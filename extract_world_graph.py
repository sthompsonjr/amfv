#!/usr/bin/env python3
"""Extract world graph skeleton from AMFV ZIL source files."""

import json
import os
import re
import sys
from datetime import datetime, timezone

VERSION = "0.5.0"
EXTRACTION_SESSION = 5
EXPECTED_ROOM_COUNT = 154

DIRECTION_MAP = {
    "NORTH": "N", "NE": "NE", "EAST": "E", "SE": "SE",
    "SOUTH": "S", "SW": "SW", "WEST": "W", "NW": "NW",
    "UP": "UP", "DOWN": "DOWN", "IN": "IN", "OUT": "OUT",
}

DIRECTIONS = set(DIRECTION_MAP.keys())

# Hardcoded zone sets. Note: actual room IDs in these files use EPILOGUE-BATHROOM
# and DINING-ROOM rather than EPILOGUE-BATH / EPILOGUE-DINING-ROOM from the spec.
EPILOGUE_ROOMS = frozenset([
    "SOLARIUM", "PATIO", "EPILOGUE-LIVING-ROOM", "FOYER", "DEN",
    "GUEST-ROOM", "EPILOGUE-BATH", "EPILOGUE-BATHROOM",
    "MASTER-BEDROOM", "EPILOGUE-DINING-ROOM", "DINING-ROOM",
    "EPILOGUE-KITCHEN", "SKYCAB",
])

# The spec lists RED-LINE-* / BROWN-LINE-* names that don't appear in the source;
# actual tube station rooms use TUBEBIT flag. TUBECAR rooms lack TUBEBIT.
TUBECAR_ROOMS = frozenset(["RED-TUBECAR", "BROWN-TUBECAR"])

SPECIAL_ROOMS = {
    "BURNED-OUT-AREA": "disorientation",
    "LIBRARY-ROOM": "virtual_mode",
    "SLEEP-ROOM": "virtual_mode",
    "COMM-ROOM": "virtual_mode",
    "INTERFACE-ROOM": "virtual_mode",
    "SIMULATION-ROOM": "virtual_mode",
}

OUTPUT_FILE = "world_graph.json"


# ---------------------------------------------------------------------------
# Low-level ZIL text utilities
# ---------------------------------------------------------------------------

def find_matching_angle(text, start):
    """Return index of the > that closes the < at text[start]."""
    depth = 0
    in_string = False
    i = start
    while i < len(text):
        c = text[i]
        if in_string:
            if c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == '<':
                depth += 1
            elif c == '>':
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def find_matching_paren(text, start):
    """Return index of the ) that closes the ( at text[start]."""
    depth = 0
    in_string = False
    i = start
    while i < len(text):
        c = text[i]
        if in_string:
            if c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def extract_string(text, start):
    """Return the string content (without delimiters) beginning at text[start]='\"'."""
    i = start + 1
    result = []
    while i < len(text):
        c = text[i]
        if c == '"':
            return ''.join(result), i
        result.append(c)
        i += 1
    return ''.join(result), i


def normalize_ldesc(raw):
    """Strip quotes, collapse newlines/spaces, and trim LDESC string."""
    s = raw.replace('\n', ' ')
    s = re.sub(r' +', ' ', s)
    return s.strip()


# ---------------------------------------------------------------------------
# Room block extraction
# ---------------------------------------------------------------------------

def find_room_blocks(content):
    """Return list of (room_id, block_text) for all non-commented <ROOM> defs."""
    blocks = []
    for m in re.finditer(r'^<ROOM\s+(\S+)', content, re.MULTILINE):
        room_id = m.group(1)
        start = m.start()
        end = find_matching_angle(content, start)
        if end == -1:
            print(f"WARNING: could not find closing > for ROOM {room_id}", file=sys.stderr)
            continue
        blocks.append((room_id, content[start:end + 1]))
    return blocks


# ---------------------------------------------------------------------------
# Property clause extraction
# ---------------------------------------------------------------------------

def find_clause(block, prop_name):
    """Return the full '(PROP_NAME ...)' clause text, or None if absent."""
    pat = re.compile(r'\(' + re.escape(prop_name) + r'\b')
    m = pat.search(block)
    if not m:
        return None
    start = m.start()
    end = find_matching_paren(block, start)
    if end == -1:
        return None
    return block[start:end + 1]


def parse_simple_string(clause_text):
    """Extract the first double-quoted string from a clause."""
    i = clause_text.find('"')
    if i == -1:
        return None
    content, _ = extract_string(clause_text, i)
    return content


def parse_tokens(clause_text, prop_name):
    """Return list of whitespace-delimited tokens after PROP_NAME in a clause."""
    inner = clause_text.strip()
    # Strip outer parens
    inner = inner[1:-1].strip()
    # Remove prop name
    inner = inner[len(prop_name):].strip()
    # Split on whitespace, filtering empties
    return [t for t in re.split(r'\s+', inner) if t]


def extract_desc(block):
    """Extract DESC string or None."""
    clause = find_clause(block, "DESC")
    if clause is None:
        return None
    return parse_simple_string(clause)


def extract_ldesc(block):
    """Extract and normalize LDESC multi-line string or None."""
    clause = find_clause(block, "LDESC")
    if clause is None:
        return None
    i = clause.find('"')
    if i == -1:
        return None
    raw, _ = extract_string(clause, i)
    return normalize_ldesc(raw)


def extract_flags(block):
    """Extract FLAGS token list or empty list."""
    clause = find_clause(block, "FLAGS")
    if clause is None:
        return []
    return parse_tokens(clause, "FLAGS")


def extract_scene(block):
    """Extract SCENE integer or None."""
    clause = find_clause(block, "SCENE")
    if clause is None:
        return None
    tokens = parse_tokens(clause, "SCENE")
    if not tokens:
        return None
    try:
        return int(tokens[0])
    except ValueError:
        return None


def extract_action(block):
    """Extract ACTION routine name string or None."""
    clause = find_clause(block, "ACTION")
    if clause is None:
        return None
    tokens = parse_tokens(clause, "ACTION")
    return tokens[0] if tokens else None


def extract_globals(block):
    """Extract GLOBAL token list or empty list."""
    clause = find_clause(block, "GLOBAL")
    if clause is None:
        return []
    return parse_tokens(clause, "GLOBAL")


# ---------------------------------------------------------------------------
# Edge extraction
# ---------------------------------------------------------------------------

def parse_edge_clause(clause_text, dir_key):
    """
    Parse a direction clause and return an edge dict or None (for SORRY).

    Handles:
      (DIR TO TARGET)
      (DIR TO TARGET IF OBJECT IS OPEN)
      (DIR PER FUNCTION)
      (DIR SORRY "msg")
    """
    dir_short = DIRECTION_MAP[dir_key]
    # Strip outer parens and leading whitespace
    inner = clause_text.strip()[1:-1].strip()
    # Remove the direction keyword
    inner = re.sub(r'^' + re.escape(dir_key) + r'\s*', '', inner, count=1).strip()

    if inner.startswith("SORRY"):
        return None

    if inner.startswith("PER ") or inner == "PER":
        tokens = inner.split()
        gate_fn = tokens[1] if len(tokens) > 1 else None
        return {
            "direction": dir_short,
            "type": "gated",
            "target": None,
            "gate_fn": gate_fn,
            "rules": [],
        }

    if inner.startswith("TO "):
        tokens = inner.split()
        target = tokens[1]
        # Check for conditional: TO TARGET IF OBJECT IS OPEN
        if len(tokens) >= 5 and tokens[2] == "IF" and tokens[4] == "IS":
            door_id = tokens[3]
            return {
                "direction": dir_short,
                "type": "door",
                "target": target,
                "door_id": door_id,
            }
        return {"direction": dir_short, "type": "open", "target": target}

    # Fallback: IF OBJECT IS OPEN TO TARGET (spec's alternate IF syntax)
    if inner.startswith("IF "):
        tokens = inner.split()
        # IF OBJECT IS OPEN TO TARGET [ELSE "msg"]
        if len(tokens) >= 6 and tokens[2] == "IS" and tokens[3] == "OPEN" and tokens[4] == "TO":
            return {
                "direction": dir_short,
                "type": "door",
                "target": tokens[5],
                "door_id": tokens[1],
            }

    return None


def find_direction_clauses_in_order(block):
    """Yield (dir_key, clause_text) in ZIL source order using position scan."""
    dir_pat = re.compile(
        r'\((' + '|'.join(re.escape(d) for d in DIRECTIONS) + r')\b'
    )
    for m in dir_pat.finditer(block):
        dir_key = m.group(1)
        start = m.start()
        end = find_matching_paren(block, start)
        if end != -1:
            yield dir_key, block[start:end + 1]


def extract_edges(block):
    """Extract all edge dicts from direction clauses in ZIL source order."""
    edges = []
    for dir_key, clause in find_direction_clauses_in_order(block):
        edge = parse_edge_clause(clause, dir_key)
        if edge is not None:
            edges.append(edge)
    return edges


# ---------------------------------------------------------------------------
# Alias collapsing
# ---------------------------------------------------------------------------

def _edge_key(edge):
    """Return a hashable key for alias-collapsing equivalence."""
    if edge["type"] == "gated":
        return (edge["type"], edge.get("gate_fn"))
    if edge["type"] == "door":
        return (edge["type"], edge["target"], edge.get("door_id"))
    return (edge["type"], edge["target"])


def collapse_aliases(edges):
    """
    Collapse edges with the same type+target+gate_fn into one, adding aliases.

    First direction encountered becomes primary; duplicates go into 'aliases'.
    """
    seen = {}  # key -> index in result list
    result = []
    for edge in edges:
        key = _edge_key(edge)
        if key in seen:
            primary = result[seen[key]]
            aliases = primary.setdefault("aliases", [])
            aliases.append(edge["direction"])
        else:
            seen[key] = len(result)
            result.append(dict(edge))  # copy so we don't mutate original
    return result


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------

def get_zone(room_id, flags, source_basename):
    """Return zone string for a room based on source file, hardcoded sets, and flags."""
    if "prism" in source_basename:
        return "prism"
    if "apartment" in source_basename:
        if room_id in EPILOGUE_ROOMS:
            return "epilogue"
        return "apartment"
    # rockvil
    if room_id in EPILOGUE_ROOMS:
        return "epilogue"
    if "TUBEBIT" in flags or room_id in TUBECAR_ROOMS:
        return "tube"
    if room_id.startswith("SKYCAR-LOT"):
        return "skycar"
    if "STREETBIT" in flags:
        return "street"
    return "interior"


# ---------------------------------------------------------------------------
# Full room parser
# ---------------------------------------------------------------------------

def parse_room(room_id, block, source_path):
    """Parse a single ROOM block and return the room node dict."""
    source_basename = os.path.basename(source_path)
    flags = extract_flags(block)
    edges_raw = extract_edges(block)
    edges = collapse_aliases(edges_raw)
    zone = get_zone(room_id, flags, source_basename)

    return {
        "desc": extract_desc(block),
        "desc_variants": None,
        "zone": zone,
        "source_file": source_basename,
        "flags": flags,
        "scene": extract_scene(block),
        "special": SPECIAL_ROOMS.get(room_id),
        "action": extract_action(block),
        "description": extract_ldesc(block),
        "globals": extract_globals(block),
        "objects": [],
        "asset_ref": None,
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def check_orphan_targets(rooms):
    """Warn about open-edge targets that don't exist in the rooms dict."""
    orphans = []
    for room_id, room in rooms.items():
        for edge in room["edges"]:
            if edge["type"] == "open" and edge.get("target") not in rooms:
                orphans.append((room_id, edge["direction"], edge["target"]))
    return orphans


def check_reciprocal_edges(rooms):
    """Return count of open edges without a reciprocal open edge in the target room."""
    non_recip = 0
    for room_id, room in rooms.items():
        for edge in room["edges"]:
            if edge["type"] != "open":
                continue
            target_id = edge["target"]
            if target_id not in rooms:
                continue
            target_room = rooms[target_id]
            has_back = any(
                e["type"] == "open" and e["target"] == room_id
                for e in target_room["edges"]
            )
            if not has_back:
                non_recip += 1
    return non_recip


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    """Parse ZIL files, build world graph, write JSON, print summary."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file1.zil> [file2.zil ...]", file=sys.stderr)
        sys.exit(1)

    source_files = sys.argv[1:]
    rooms = {}
    alias_total = 0

    for path in source_files:
        try:
            content = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
            sys.exit(1)

        for room_id, block in find_room_blocks(content):
            if room_id in rooms:
                print(f"WARNING: duplicate room ID {room_id} in {path}", file=sys.stderr)
                continue
            room = parse_room(room_id, block, path)
            # Count aliases added in this room
            for edge in room["edges"]:
                alias_total += len(edge.get("aliases", []))
            rooms[room_id] = room

    # Sort rooms alphabetically for deterministic output
    rooms = dict(sorted(rooms.items()))

    # --- Counts ---
    total_rooms = len(rooms)
    open_edges = sum(
        1 for r in rooms.values() for e in r["edges"] if e["type"] == "open"
    )
    gated_edges = sum(
        1 for r in rooms.values() for e in r["edges"] if e["type"] == "gated"
    )
    door_edges = sum(
        1 for r in rooms.values() for e in r["edges"] if e["type"] == "door"
    )
    total_edges = open_edges + gated_edges + door_edges

    zone_counts = {}
    for room in rooms.values():
        z = room["zone"]
        zone_counts[z] = zone_counts.get(z, 0) + 1

    # --- Orphan targets ---
    orphans = check_orphan_targets(rooms)
    for room_id, direction, target in orphans:
        print(f"WARNING: orphan target {target!r} in {room_id} ({direction})")

    # --- Non-reciprocal edges ---
    non_recip = check_reciprocal_edges(rooms)

    # --- Build output ---
    zone_summary = ", ".join(
        f"{v} {k}" for k, v in sorted(zone_counts.items(), key=lambda x: -x[1])
    )
    print(
        f"Extracted {total_rooms} rooms "
        f"({zone_summary}, "
        f"{zone_counts.get('unknown', 0)} unknown)"
    )
    print(
        f"Total edges: {total_edges} "
        f"({open_edges} open, {gated_edges} gated stubs, {door_edges} door)"
    )
    print(f"Aliases collapsed: {alias_total}")
    print(f"Non-reciprocal open edges: {non_recip} (informational)")

    source_basenames = [os.path.basename(p) for p in source_files]

    graph = {
        "meta": {
            "version": VERSION,
            "generated": datetime.now(timezone.utc).isoformat(),
            "source_files": source_basenames,
            "room_count": total_rooms,
            "open_edge_count": open_edges,
            "stub_edge_count": gated_edges,
            "extraction_session": EXTRACTION_SESSION,
            "notes": (
                "Skeleton: room nodes with flags, static LDESC, globals, open edges. "
                "Gated/door/mode edge rules added in Sessions 6-7."
            ),
        },
        "gate_defs": {},
        "rooms": rooms,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Output: {OUTPUT_FILE}")

    # --- Room count check ---
    exit_code = 0
    if total_rooms != EXPECTED_ROOM_COUNT:
        diff = total_rooms - EXPECTED_ROOM_COUNT
        direction = f"{abs(diff)} extra" if diff > 0 else f"{abs(diff)} missing"
        print(
            f"FAIL: expected {EXPECTED_ROOM_COUNT} rooms, found {total_rooms} "
            f"({direction}). Adjust EXPECTED_ROOM_COUNT or audit source files."
        )
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
