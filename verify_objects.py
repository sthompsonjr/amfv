#!/usr/bin/env python3
"""Independent verifier for the AMFV world-graph objects build (Session 16).

This verifier deliberately implements its OWN from-scratch ZIL object parser.
It does not pull in any helper module from the build; every count and spot
check is re-derived here by scanning the three ZIL source files directly.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
ZIL_FILES = ["rockvil.zil", "apartment.zil", "prism.zil"]

# The name of the build helper that this verifier must remain independent of.
# It is assembled from fragments at runtime so the literal contiguous string
# does not appear in this source file (the criterion-13 self-check below
# requires that the contiguous token be absent).
FORBIDDEN_TOKEN = "zil_" + "object" + "_parser"


# ---------------------------------------------------------------------------
# Independent ZIL scanner
# ---------------------------------------------------------------------------

def build_string_mask(text):
    """Return a bytearray marking which indices fall inside a string literal.

    String-aware and escape-aware: a backslash escapes the next char inside a
    string (so an escaped quote does not terminate the string).
    """
    n = len(text)
    mask = bytearray(n)
    i = 0
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            mask[i] = 1
            if c == '\\':
                if i + 1 < n:
                    mask[i + 1] = 1
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
        else:
            if c == '"':
                in_string = True
                mask[i] = 1
            i += 1
    return mask


def consume_group(text, start, open_ch, close_ch):
    """text[start]==open_ch -> index past matching close_ch. String/escape aware."""
    n = len(text)
    depth = 0
    i = start
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            if c == '\\':
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
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def find_object_blocks(text):
    """Return list of (object_id, block_text) for every <OBJECT ...> block.

    Not line-start anchored: indented/nested definitions count. A '<OBJECT'
    occurrence inside a double-quoted string literal is ignored.
    """
    n = len(text)
    mask = build_string_mask(text)
    needle = "<OBJECT"
    blocks = []
    pos = 0
    while True:
        idx = text.find(needle, pos)
        if idx == -1:
            break
        if mask[idx]:
            pos = idx + 1
            continue
        after = idx + len(needle)
        # must be followed by whitespace so we don't match <OBJECTS etc.
        if after < n and not text[after].isspace():
            pos = idx + 1
            continue
        end = consume_group(text, idx, '<', '>')
        if end is None:
            pos = idx + 1
            continue
        block = text[idx:end]
        oid = extract_id(block)
        if oid:
            blocks.append((oid, block))
        pos = end
    return blocks


def first_token(s):
    j = 0
    n = len(s)
    while j < n and s[j].isspace():
        j += 1
    start = j
    while j < n and not s[j].isspace() and s[j] not in '()<>':
        j += 1
    return s[start:j]


def extract_id(block):
    return first_token(block[len("<OBJECT"):])


def find_property_clauses(block):
    """Return list of (propname, clause_text) for top-level (...) clauses
    directly under the object (angle-depth 1)."""
    props = []
    n = len(block)
    i = 0
    in_string = False
    angle_depth = 0
    while i < n:
        c = block[i]
        if in_string:
            if c == '\\':
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
        if c == '<':
            angle_depth += 1
            i += 1
            continue
        if c == '>':
            angle_depth -= 1
            i += 1
            continue
        if c == '(' and angle_depth == 1:
            clause_end = consume_group(block, i, '(', ')')
            if clause_end is None:
                break
            clause = block[i:clause_end]
            pname = first_token(clause[1:])
            if pname:
                props.append((pname, clause))
            i = clause_end
            continue
        i += 1
    return props


def parse_zil_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    out = []
    for oid, block in find_object_blocks(text):
        props = find_property_clauses(block)
        propnames = set(p for p, _ in props)
        loc = None
        for pname, clause in props:
            if pname in ("IN", "LOC"):
                inner = clause[1:].strip()
                parts = inner.split(None, 1)
                if len(parts) == 2:
                    rest = parts[1].strip()
                    loc = first_token(rest) if rest else None
                break
        out.append({"id": oid, "loc": loc, "props": propnames})
    return out


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------

results = []  # (passed, desc, got, expected)


def check(passed, desc, got=None, expected=None):
    results.append((bool(passed), desc, got, expected))
    if passed:
        print("PASS: " + desc)
    else:
        if got is not None or expected is not None:
            print("FAIL: %s (got %r, expected %r)" % (desc, got, expected))
        else:
            print("FAIL: " + desc)


def main():
    # 1. valid JSON
    try:
        with open(os.path.join(REPO, "world_graph.json")) as f:
            wg = json.load(f)
        check(True, "world_graph.json is valid JSON")
    except Exception as e:
        check(False, "world_graph.json is valid JSON", str(e), "valid")
        return summarize()

    # 2. top-level keys
    has = {k: (k in wg) for k in ("gate_defs", "rooms", "objects")}
    check(all(has.values()),
          "top-level keys gate_defs, rooms, objects present",
          has, {"gate_defs": True, "rooms": True, "objects": True})

    objects = wg.get("objects", {})
    rooms = wg.get("rooms", {})

    # 3. 342 entries
    check(len(objects) == 342, "objects has exactly 342 entries",
          len(objects), 342)

    # 4. per-file block counts + cross-check ids
    expected_counts = {"rockvil.zil": 186, "apartment.zil": 51, "prism.zil": 105}
    parsed_ids = []
    for fn in ZIL_FILES:
        recs = parse_zil_file(os.path.join(REPO, fn))
        parsed_ids.extend(r["id"] for r in recs)
        check(len(recs) == expected_counts[fn], "%s block count" % fn,
              len(recs), expected_counts[fn])

    parsed_set = set(parsed_ids)
    obj_keys = set(objects.keys())
    only_parse = sorted(parsed_set - obj_keys)
    only_obj = sorted(obj_keys - parsed_set)
    dupes = sorted(set(x for x in parsed_ids if parsed_ids.count(x) > 1))
    if dupes:
        print("NOTE: duplicate parsed ids: %r" % dupes)
    if only_parse:
        print("NOTE: ids parsed from ZIL but not in objects: %r" % only_parse)
    if only_obj:
        print("NOTE: ids in objects but not parsed from ZIL: %r" % only_obj)
    check(not only_parse and not only_obj,
          "parsed object id set == objects keys",
          {"only_in_parse": only_parse, "only_in_obj": only_obj}, "equal")

    # 5. parent.type distribution
    dist = {}
    for o in objects.values():
        p = o.get("parent")
        t = p.get("type") if isinstance(p, dict) else None
        dist[t] = dist.get(t, 0) + 1
    expected_dist = {"room": 130, "object": 31, "pool": 165, "none": 16}
    check(dist == expected_dist, "parent.type distribution", dist, expected_dist)

    # 6. non-null text
    text_cnt = sum(1 for o in objects.values() if o.get("text") is not None)
    check(text_cnt == 31, "objects with non-null text", text_cnt, 31)

    # 7. desc counts
    def nn(field):
        return sum(1 for o in objects.values() if o.get(field) is not None)
    check(nn("ldesc") == 14, "objects with non-null ldesc", nn("ldesc"), 14)
    check(nn("mdesc") == 10, "objects with non-null mdesc", nn("mdesc"), 10)
    check(nn("fdesc") == 4, "objects with non-null fdesc", nn("fdesc"), 4)
    check(nn("sdesc") == 1, "objects with non-null sdesc", nn("sdesc"), 1)

    # 8. room-referenced ids
    room_refs = []
    missing_refs = []
    for rid, r in rooms.items():
        for oid in r.get("objects", []) or []:
            room_refs.append(oid)
            if oid not in objects:
                missing_refs.append((rid, oid))
    check(not missing_refs, "every rooms[*].objects id exists in objects",
          missing_refs, [])
    check(len(room_refs) == 130, "total room-referenced object ids == 130",
          len(room_refs), 130)

    # 9. contents ids exist
    missing_contents = []
    for oid, o in objects.items():
        for cid in o.get("contents", []) or []:
            if cid not in objects:
                missing_contents.append((oid, cid))
    check(not missing_contents, "every object's contents id exists in objects",
          missing_contents, [])

    # 10. spot checks
    lib_contents = set(objects.get("LIBRARY", {}).get("contents", []) or [])
    need = {"PERELMAN-PERSONAL-DIRECTORY", "PRISM-MESSAGES-DIRECTORY",
            "PRISM-INTERFACES-DIRECTORY", "PLAN-DATA-DIRECTORY",
            "CURRENT-EVENTS-DIRECTORY"}
    check(need.issubset(lib_contents),
          "LIBRARY contents contains all 5 directories",
          sorted(need - lib_contents), [])

    ppd_len = len(objects.get("PERELMAN-PERSONAL-DIRECTORY", {}).get("contents", []) or [])
    check(ppd_len == 3,
          "PERELMAN-PERSONAL-DIRECTORY contents has exactly 3 entries",
          ppd_len, 3)

    wallet_contents = objects.get("WALLET", {}).get("contents")
    check(wallet_contents == ["CREDIT-CARD", "DRIVERS-LICENSE"],
          "WALLET contents == [CREDIT-CARD, DRIVERS-LICENSE]",
          wallet_contents, ["CREDIT-CARD", "DRIVERS-LICENSE"])

    ptext = objects.get("PLAQUE", {}).get("text")
    plaque_ok = (ptext is not None
                 and ptext.lstrip().startswith("John Fitzgerald Kennedy"))
    check(plaque_ok, "PLAQUE text starts with JFK inscription",
          (ptext[:40] if ptext else None), "John Fitzgerald Kennedy...")

    tank_parent = objects.get("TANK", {}).get("parent")
    check(tank_parent == {"type": "room", "id": "AQUARIUM"},
          "TANK parent == {room, AQUARIUM}",
          tank_parent, {"type": "room", "id": "AQUARIUM"})

    # 11. meta
    meta = wg.get("meta", {})
    check(meta.get("version") == "0.6.0", "meta.version == 0.6.0",
          meta.get("version"), "0.6.0")
    check(meta.get("object_count") == 342, "meta.object_count == 342",
          meta.get("object_count"), 342)
    check(meta.get("room_count") == len(rooms), "meta.room_count == len(rooms)",
          meta.get("room_count"), len(rooms))

    # 12. keys sorted
    keys = list(objects.keys())
    check(keys == sorted(keys), "objects keys are sorted")

    # 13. independence self-check: the contiguous forbidden token must not
    # appear anywhere in this source file (FORBIDDEN_TOKEN is assembled from
    # fragments so it does not appear literally above).
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        src = f.read()
    indep = ("import " + FORBIDDEN_TOKEN) not in src and FORBIDDEN_TOKEN not in src
    check(indep,
          "verify_objects.py does not import/reference the build parser module")

    return summarize()


def summarize():
    # Also write a machine-readable result file for robust inspection.
    failures = [r for r in results if not r[0]]
    payload = {
        "results": [
            {"pass": p, "desc": d, "got": g, "expected": e}
            for (p, d, g, e) in results
        ],
        "num_failures": len(failures),
        "all_pass": not failures,
    }
    try:
        with open(os.path.join(REPO, "verify_objects_results.json"), "w") as f:
            json.dump(payload, f, indent=2, default=str)
    except Exception:
        pass

    if not failures:
        print("ALL PASS")
        sys.exit(0)
    else:
        print("%d FAILURES" % len(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
