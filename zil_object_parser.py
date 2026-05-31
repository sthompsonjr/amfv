#!/usr/bin/env python3
"""
Session 16: Shared ZIL object parser + world-graph objects-layer build.

This module is the single source of truth for object block-boundary scanning
and property reading. The per-file parser sub-agents import it (via the
``shard`` sub-command) so they cannot diverge; the orchestrator uses the
``build`` sub-command to merge the shards, classify parents, compute the
container tree, populate room.objects, update meta, and write world_graph.json
atomically.

Stdlib only, deterministic output, atomic write. The independent verifier
(verify_objects.py) deliberately does NOT import this module.

Sub-commands::

    python3 zil_object_parser.py shard <shortname> <zil_path> <out_shard_json>
    python3 zil_object_parser.py build
    python3 zil_object_parser.py all      # parse every file + build, no shards
"""

import json
import os
import re
import sys
import tempfile

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORLD_GRAPH_IN = "world_graph.json"
WORLD_GRAPH_OUT = "world_graph.json"

ZIL_SOURCES = {
    "rockvil.zil": "rockvil.zil",
    "apartment.zil": "apartment.zil",
    "prism.zil": "prism.zil",
}

BUILD_DIR = "build/session16"

# Hard gates ----------------------------------------------------------------
EXPECTED_BLOCK_COUNTS = {"rockvil.zil": 186, "apartment.zil": 51, "prism.zil": 105}
EXPECTED_TOTAL_OBJECTS = 342
EXPECTED_PARENT_TYPES = {"room": 130, "object": 31, "pool": 165, "none": 16}

POOLS = {"LOCAL-GLOBALS", "GLOBAL-OBJECTS", "GENERIC-OBJECTS"}

# Property keyword tables ----------------------------------------------------
# KEYWORD -> field name
STRING_KEYWORDS = {
    "DESC": "desc",
    "TEXT": "text",
    "LDESC": "ldesc",
    "FDESC": "fdesc",
    "MDESC": "mdesc",
    "SDESC": "sdesc",
}
LIST_KEYWORDS = {
    "SYNONYM": "synonyms",
    "ADJECTIVE": "adjectives",
    "FLAGS": "flags",
}
TOKEN_KEYWORDS = {
    "ACTION": "action",
    "GENERIC": "generic",
    "DESCFCN": "descfcn",
}
INT_KEYWORDS = {
    "SIZE": "size",
    "CAPACITY": "capacity",
}

NOTE_APPEND = (
    " Objects layer added in Session 16: flat objects table, room.objects "
    "populated, container tree via parent/contents. Object desc_variants "
    "reserved for later session."
)


# ---------------------------------------------------------------------------
# Balanced-delimiter scanners (string-aware, escape-aware)
# ---------------------------------------------------------------------------

def _find_matching(text, start, open_c, close_c):
    """Index of the close delimiter matching the open one at text[start].

    String-aware (ignores delimiters inside double-quoted strings) and
    escape-aware (a backslash escapes the next character, so ``\\"`` does not
    end a string). Returns -1 if unbalanced.
    """
    depth = 0
    in_string = False
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == open_c:
                depth += 1
            elif c == close_c:
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def find_matching_angle(text, start):
    """Return index of the > that closes the < at text[start]."""
    return _find_matching(text, start, "<", ">")


def find_matching_paren(text, start):
    """Return index of the ) that closes the ( at text[start]."""
    return _find_matching(text, start, "(", ")")


# ---------------------------------------------------------------------------
# Object block scanning
# ---------------------------------------------------------------------------

_OBJECT_TAG = "<OBJECT"


def find_object_blocks(content):
    """Return a list of (object_id, block_text) for every <OBJECT ...> def.

    Not anchored to line-start: indented/nested object definitions (e.g. the
    four indented ones in prism.zil) are caught. String-aware and escape-aware
    so a literal '<OBJECT' inside a quoted string is ignored. The id is the
    first whitespace-delimited token after <OBJECT.
    """
    blocks = []
    i = 0
    n = len(content)
    in_string = False
    while i < n:
        c = content[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            i += 1
            continue
        if c == "<" and content.startswith(_OBJECT_TAG, i):
            j = i + len(_OBJECT_TAG)
            # Require whitespace after <OBJECT so <OBJECTS / <OBJECT? etc. do
            # not false-match.
            if j < n and content[j].isspace():
                end = find_matching_angle(content, i)
                if end == -1:
                    print(
                        "WARNING: unbalanced <OBJECT at offset %d" % i,
                        file=sys.stderr,
                    )
                    i = j
                    continue
                block = content[i:end + 1]
                m = re.match(r"<OBJECT\s+(\S+)", block)
                if not m:
                    print(
                        "WARNING: <OBJECT with no id at offset %d" % i,
                        file=sys.stderr,
                    )
                    i = end + 1
                    continue
                blocks.append((m.group(1), block))
                i = end + 1
                continue
        i += 1
    return blocks


# ---------------------------------------------------------------------------
# Property extraction
# ---------------------------------------------------------------------------

_COMMENT_STRING_RE = re.compile(r';"(?:[^"\\]|\\.)*"')
_INNER_STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _string_inner(clause):
    """First double-quoted literal in clause, outer quotes stripped, inner
    content preserved verbatim (keeps the '|' line-break convention and any
    escaped quotes). Returns None if there is no string literal."""
    m = _INNER_STRING_RE.search(clause)
    return m.group(1) if m else None


def _bare_tokens(clause, keyword):
    """Bare tokens of a (KEYWORD tok tok ...) clause, with the keyword and any
    ;"..." comments removed."""
    inner = clause[1:-1]  # drop the outer parens
    inner = _COMMENT_STRING_RE.sub(" ", inner)
    toks = inner.split()
    if toks and toks[0] == keyword:
        toks = toks[1:]
    return [t for t in toks if not t.startswith(";")]


def parse_object_block(object_id, block, source_file):
    """Parse one <OBJECT ...> block into a raw record.

    Returns {"id", "source_file", "loc", "props", "raw_props"} where:
      - loc       : the LOC token (str) or None
      - props     : typed known properties keyed by FIELD name
      - raw_props : unknown keywords keyed by KEYWORD -> raw inner text
    Only top-level (KEYWORD ...) clauses are read, so keywords appearing inside
    strings or nested expressions are not mistaken for properties.
    """
    m = re.match(r"<OBJECT\s+\S+", block)
    i = m.end()
    n = len(block)
    in_string = False
    loc = None
    props = {}
    raw_props = {}
    while i < n:
        c = block[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            i += 1
            continue
        if c == "(":
            end = find_matching_paren(block, i)
            if end == -1:
                break
            clause = block[i:end + 1]
            km = re.match(r"\(\s*([^\s()]+)", clause)
            if km:
                keyword = km.group(1)
                _handle_clause(keyword, clause, props, raw_props, lambda v: None)
                if keyword == "LOC":
                    toks = _bare_tokens(clause, "LOC")
                    loc = toks[0] if toks else None
            i = end + 1
            continue
        i += 1
    return {
        "id": object_id,
        "source_file": source_file,
        "loc": loc,
        "props": props,
        "raw_props": raw_props,
    }


def _handle_clause(keyword, clause, props, raw_props, _unused):
    if keyword == "LOC":
        return  # consumed separately into record["loc"]
    if keyword in STRING_KEYWORDS:
        val = _string_inner(clause)
        if val is None:
            # Known string keyword whose value is not a quoted literal
            # (e.g. MDESC <TABLE 3 14 2031 557>). Preserve the raw inner
            # expression verbatim so the property is captured, not dropped.
            inner = clause[1:-1].strip()
            if inner.startswith(keyword):
                inner = inner[len(keyword):].strip()
            val = inner or None
        props[STRING_KEYWORDS[keyword]] = val
    elif keyword in LIST_KEYWORDS:
        props[LIST_KEYWORDS[keyword]] = _bare_tokens(clause, keyword)
    elif keyword in TOKEN_KEYWORDS:
        toks = _bare_tokens(clause, keyword)
        props[TOKEN_KEYWORDS[keyword]] = toks[0] if toks else None
    elif keyword in INT_KEYWORDS:
        toks = _bare_tokens(clause, keyword)
        val = None
        if toks:
            try:
                val = int(toks[0])
            except ValueError:
                val = None
        props[INT_KEYWORDS[keyword]] = val
    else:
        # Unknown keyword: keep raw inner text so nothing is silently lost.
        inner = clause[1:-1].strip()
        inner = inner[len(keyword):].strip() if inner.startswith(keyword) else inner
        raw_props[keyword] = inner


def parse_file(short_name, zil_path):
    """Parse one ZIL file into a list of raw object records; assert count."""
    with open(zil_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    blocks = find_object_blocks(content)
    records = [parse_object_block(oid, blk, short_name) for oid, blk in blocks]
    expected = EXPECTED_BLOCK_COUNTS.get(short_name)
    if expected is not None and len(records) != expected:
        raise AssertionError(
            "block count for %s: got %d, expected %d"
            % (short_name, len(records), expected)
        )
    return records


# ---------------------------------------------------------------------------
# Assembly (orchestrator)
# ---------------------------------------------------------------------------

ALL_FIELDS = [
    "desc", "desc_variants", "synonyms", "adjectives", "flags", "action",
    "generic", "descfcn", "text", "ldesc", "fdesc", "mdesc", "sdesc", "size",
    "capacity", "parent", "contents", "source_file", "raw_props",
]


def classify_parent(loc, room_ids, object_ids):
    if loc is None:
        return {"type": "none", "id": None}
    if loc in room_ids:
        return {"type": "room", "id": loc}
    if loc in object_ids:
        return {"type": "object", "id": loc}
    if loc in POOLS:
        return {"type": "pool", "id": loc}
    return {"type": "none", "id": loc}


def build_objects(records, room_ids):
    """Turn raw records into the final objects dict and parent/room maps."""
    object_ids = {r["id"] for r in records}

    nodes = {}
    parent_of = {}
    for r in records:
        parent = classify_parent(r["loc"], room_ids, object_ids)
        p = r["props"]
        node = {
            "desc": p.get("desc"),
            "desc_variants": None,
            "synonyms": p.get("synonyms", []),
            "adjectives": p.get("adjectives", []),
            "flags": p.get("flags", []),
            "action": p.get("action"),
            "generic": p.get("generic"),
            "descfcn": p.get("descfcn"),
            "text": p.get("text"),
            "ldesc": p.get("ldesc"),
            "fdesc": p.get("fdesc"),
            "mdesc": p.get("mdesc"),
            "sdesc": p.get("sdesc"),
            "size": p.get("size"),
            "capacity": p.get("capacity"),
            "parent": parent,
            "contents": [],  # filled below
            "source_file": r["source_file"],
            "raw_props": dict(r["raw_props"]),
        }
        nodes[r["id"]] = node
        parent_of[r["id"]] = parent

    # contents: every object whose parent.id == this id (any parent.type)
    children = {}
    for oid, parent in parent_of.items():
        pid = parent["id"]
        if pid is not None:
            children.setdefault(pid, []).append(oid)
    for oid, node in nodes.items():
        node["contents"] = sorted(children.get(oid, []))

    # room.objects: objects whose parent.type == "room"
    room_objects = {}
    for oid, parent in parent_of.items():
        if parent["type"] == "room":
            room_objects.setdefault(parent["id"], []).append(oid)
    for rid in room_objects:
        room_objects[rid] = sorted(room_objects[rid])

    return nodes, parent_of, room_objects


def parent_type_counts(parent_of):
    counts = {"room": 0, "object": 0, "pool": 0, "none": 0}
    for parent in parent_of.values():
        counts[parent["type"]] += 1
    return counts


def assemble_graph(records):
    with open(WORLD_GRAPH_IN, "r", encoding="utf-8") as fh:
        graph = json.load(fh)

    room_ids = set(graph["rooms"].keys())
    nodes, parent_of, room_objects = build_objects(records, room_ids)

    # Hard gates ------------------------------------------------------------
    if len(nodes) != EXPECTED_TOTAL_OBJECTS:
        raise AssertionError(
            "total objects: got %d, expected %d"
            % (len(nodes), EXPECTED_TOTAL_OBJECTS)
        )
    counts = parent_type_counts(parent_of)
    if counts != EXPECTED_PARENT_TYPES:
        raise AssertionError(
            "parent.type distribution: got %s, expected %s"
            % (counts, EXPECTED_PARENT_TYPES)
        )

    # Populate room.objects (only field touched on rooms) -------------------
    for rid, room in graph["rooms"].items():
        room["objects"] = sorted(room_objects.get(rid, []))

    # Top-level objects table (keys sorted for determinism) -----------------
    graph["objects"] = {oid: nodes[oid] for oid in sorted(nodes)}

    # Meta ------------------------------------------------------------------
    meta = graph["meta"]
    meta["version"] = "0.6.0"
    meta["extraction_session"] = 16
    meta["object_count"] = len(nodes)
    meta["room_count"] = len(graph["rooms"])
    if NOTE_APPEND not in meta.get("notes", ""):
        meta["notes"] = meta.get("notes", "") + NOTE_APPEND

    return graph, counts


def write_atomic(graph, path):
    """Write graph to path atomically: temp file in same dir + os.replace."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".wg_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(graph, fh, indent=2, sort_keys=True, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_shard(short_name, zil_path, out_path):
    records = parse_file(short_name, zil_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print(
        "shard %s: %d objects -> %s" % (short_name, len(records), out_path)
    )


def _load_shards():
    records = []
    for short_name in ZIL_SOURCES:
        shard = os.path.join(BUILD_DIR, "objects_%s.json" % short_name)
        with open(shard, "r", encoding="utf-8") as fh:
            chunk = json.load(fh)
        if len(chunk) != EXPECTED_BLOCK_COUNTS[short_name]:
            raise AssertionError(
                "shard %s: got %d, expected %d"
                % (short_name, len(chunk), EXPECTED_BLOCK_COUNTS[short_name])
            )
        records.extend(chunk)
    return records


def cmd_build():
    records = _load_shards()
    _finish(records)


def cmd_all():
    records = []
    for short_name, path in ZIL_SOURCES.items():
        records.extend(parse_file(short_name, path))
    _finish(records)


def _finish(records):
    graph, counts = assemble_graph(records)
    write_atomic(graph, WORLD_GRAPH_OUT)
    print("wrote %s" % WORLD_GRAPH_OUT)
    print("  objects: %d" % len(graph["objects"]))
    print("  parent.type: %s" % counts)
    room_refs = sum(len(r["objects"]) for r in graph["rooms"].values())
    print("  room-referenced object ids: %d" % room_refs)
    print("  meta.version: %s" % graph["meta"]["version"])


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "shard":
        if len(argv) != 5:
            print("usage: shard <shortname> <zil_path> <out_shard_json>",
                  file=sys.stderr)
            return 2
        cmd_shard(argv[2], argv[3], argv[4])
        return 0
    if cmd == "build":
        cmd_build()
        return 0
    if cmd == "all":
        cmd_all()
        return 0
    print("unknown sub-command: %s" % cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
