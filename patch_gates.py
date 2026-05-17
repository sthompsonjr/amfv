#!/usr/bin/env python3
"""
patch_gates.py — Apply 20 gated-edge modifications to world_graph_v2.json
and write the result to world_graph.json.
"""

import json
import sys
import os


def find_edge(rooms, room_id, gate_fn):
    """Return the single edge matching gate_fn in room_id, or abort."""
    if room_id not in rooms:
        sys.exit(f"ERROR: room {room_id!r} not found")
    matches = [e for e in rooms[room_id]["edges"] if e.get("gate_fn") == gate_fn]
    if len(matches) != 1:
        sys.exit(f"ERROR: expected 1 edge with gate_fn={gate_fn!r} in {room_id!r}, found {len(matches)}")
    return matches[0]


def patch(edge, target, rules):
    edge["target"] = target
    edge["rules"] = rules


def main():
    in_path = sys.argv[1] if len(sys.argv) > 1 else "world_graph_v2.json"
    out_dir = os.path.dirname(in_path) or "."
    out_path = os.path.join(out_dir, "world_graph.json")

    with open(in_path) as f:
        graph = json.load(f)
    rooms = graph["rooms"]

    changes = 0

    # ── Group 1: Construction Sites ──────────────────────────────────────────

    # CONSTRUCTION-SITE-1-ENTER-F in SOUTHWAY-AND-KENNEDY
    e = find_edge(rooms, "SOUTHWAY-AND-KENNEDY", "CONSTRUCTION-SITE-1-ENTER-F")
    patch(e, "CONSTRUCTION-SITE-1", [
        {"when": {"syear": {"neq": [2041]}}, "then": "block",
         "message": "A security guard escorts you away from the building."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched SOUTHWAY-AND-KENNEDY / CONSTRUCTION-SITE-1-ENTER-F")
    changes += 1

    # CONSTRUCTION-SITE-3-ENTER-F in MAIN-AND-CHURCH
    e = find_edge(rooms, "MAIN-AND-CHURCH", "CONSTRUCTION-SITE-3-ENTER-F")
    patch(e, "CONSTRUCTION-SITE-3", [
        {"when": {"syear": {"neq": [2041]}}, "then": "block",
         "message": "A security guard escorts you away from the building."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched MAIN-AND-CHURCH / CONSTRUCTION-SITE-3-ENTER-F")
    changes += 1

    # CONSTRUCTION-SITE-4-ENTER-F in CHURCH-ENTRANCE
    e = find_edge(rooms, "CHURCH-ENTRANCE", "CONSTRUCTION-SITE-4-ENTER-F")
    patch(e, "CONSTRUCTION-SITE-4", [
        {"when": {"syear": {"neq": [2041]}}, "then": "block",
         "message": "A doorman turns you away from the building."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched CHURCH-ENTRANCE / CONSTRUCTION-SITE-4-ENTER-F")
    changes += 1

    # CONSTRUCTION-SITE-4-ENTER-F in MAIN-AND-CHURCH
    e = find_edge(rooms, "MAIN-AND-CHURCH", "CONSTRUCTION-SITE-4-ENTER-F")
    patch(e, "CONSTRUCTION-SITE-4", [
        {"when": {"syear": {"neq": [2041]}}, "then": "block",
         "message": "A doorman turns you away from the building."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched MAIN-AND-CHURCH / CONSTRUCTION-SITE-4-ENTER-F")
    changes += 1

    # ── Group 2: Beer-Block Exits ─────────────────────────────────────────────

    beer_rules = [
        {"when": {"flag": {"name": "holding_beer", "value": True}}, "then": "block",
         "message": "The bartender yells out, \"Hey buster, you can't leave with that mug!\""},
        {"when": {}, "then": "allow"},
    ]

    e = find_edge(rooms, "EZZIS-BAR", "EZZIS-BAR-EXIT-F")
    patch(e, "ELM-UNDERPASS", beer_rules)
    print("Patched EZZIS-BAR / EZZIS-BAR-EXIT-F")
    changes += 1

    e = find_edge(rooms, "BAR", "BAR-TO-ALLEY-F")
    patch(e, "ALLEY", beer_rules)
    print("Patched BAR / BAR-TO-ALLEY-F")
    changes += 1

    e = find_edge(rooms, "BAR", "BAR-TO-PIER-F")
    patch(e, "PIER", beer_rules)
    print("Patched BAR / BAR-TO-PIER-F")
    changes += 1

    e = find_edge(rooms, "BURGER-MEISTER", "BURGER-MEISTER-EXIT-F")
    patch(e, "AQUARIUM-AND-PARK", beer_rules)
    print("Patched BURGER-MEISTER / BURGER-MEISTER-EXIT-F")
    changes += 1

    # ── Group 3: Apartment Exit ───────────────────────────────────────────────

    e = find_edge(rooms, "LIVING-ROOM", "APARTMENT-EXIT-F")
    patch(e, "PARKVIEW-HALL", [
        {"when": {"flag": {"name": "apartment_door_open", "value": False}}, "then": "block",
         "message": "The door is closed."},
        {"when": {"flag": {"name": "holding_baby", "value": True}}, "then": "block",
         "message": "Jill won't let you take the baby outside."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched LIVING-ROOM / APARTMENT-EXIT-F")
    changes += 1

    # ── Group 4: Inner Lobby ──────────────────────────────────────────────────

    # PARKVIEW-APARTMENTS — unlockable
    e = find_edge(rooms, "PARKVIEW-APARTMENTS", "INNER-LOBBY-ENTER-F")
    patch(e, "PARKVIEW-HALL", [
        {"when": {"flag": {"name": "parkview_door_open", "value": False}}, "then": "block",
         "message": "The door to the inner lobby is locked."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched PARKVIEW-APARTMENTS / INNER-LOBBY-ENTER-F")
    changes += 1

    # Always-blocked inner lobbies
    for room_id in ("CHURCH-STREET-APARTMENTS", "ROW-HOUSES", "UNIVERSITY-HEIGHTS"):
        e = find_edge(rooms, room_id, "INNER-LOBBY-ENTER-F")
        patch(e, None, [
            {"when": {}, "then": "block", "message": "The door to the inner lobby is locked."},
        ])
        print(f"Patched {room_id} / INNER-LOBBY-ENTER-F")
        changes += 1

    # ── Group 5: Hall Exit Reclassification ───────────────────────────────────

    e = find_edge(rooms, "PARKVIEW-HALL", "HALL-NEAR-YOUR-APARTMENT-EXIT-F")
    e["type"] = "open"
    e["target"] = "PARKVIEW-APARTMENTS"
    del e["rules"]
    del e["gate_fn"]
    print("Reclassified PARKVIEW-HALL / HALL-NEAR-YOUR-APARTMENT-EXIT-F -> open")
    changes += 1

    # ── Group 6: Dorm Death Trap ──────────────────────────────────────────────

    e = find_edge(rooms, "ROCKVIL-UNIVERSITY", "DORM-ENTER-F")
    patch(e, "DORM", [
        {
            "when": {"syear": {"eq": [2071]}},
            "then": "block",
            "message": "Some of the boards over the entrance have been pried away. You hesitate, because it's so dangerous to enter deserted buildings these days.",
            "special": "death_confirmation",
            "death_message": "As you stand in the lobby, squatters jump you and slit your throat.",
        },
        {"when": {}, "then": "allow"},
    ])
    print("Patched ROCKVIL-UNIVERSITY / DORM-ENTER-F")
    changes += 1

    # ── Group 7: Main and Church Death ───────────────────────────────────────

    e = find_edge(rooms, "MAIN-AND-WICKER", "MAIN-AND-CHURCH-ENTER-F")
    patch(e, "MAIN-AND-CHURCH", [
        {
            "when": {"syear": {"eq": [2081]}},
            "then": "block",
            "message": "Three men armed with knives leap out of a doorway and slit your throat.",
            "special": "death",
        },
        {"when": {}, "then": "allow"},
    ])
    print("Patched MAIN-AND-WICKER / MAIN-AND-CHURCH-ENTER-F")
    changes += 1

    # ── Group 8: Main Street Bridge Exit ─────────────────────────────────────

    e = find_edge(rooms, "MAIN-STREET-BRIDGE", "MAIN-STREET-BRIDGE-EXIT-F")
    patch(e, None, [
        {
            "when": {"syear": {"eq": [2081]}},
            "then": "block",
            "message": "A pack of wild dogs surrounds you and tears you to shreds!",
            "special": "death",
        },
        {
            "when": {},
            "then": "block",
            "message": "WARNING: You have reached the boundary of this simulation.",
        },
    ])
    print("Patched MAIN-STREET-BRIDGE / MAIN-STREET-BRIDGE-EXIT-F")
    changes += 1

    # ── Group 9: Joybooth Enter ───────────────────────────────────────────────

    e = find_edge(rooms, "ROCKVIL-MALL", "JOYBOOTH-ENTER-F")
    patch(e, "JOYBOOTH", [
        {"when": {"syear": {"eq": [2051, 2061]}}, "then": "block",
         "message": "There's nothing in that direction -- just a featureless wall."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched ROCKVIL-MALL / JOYBOOTH-ENTER-F")
    changes += 1

    # ── Group 10: Joybooth Exit ───────────────────────────────────────────────

    e = find_edge(rooms, "JOYBOOTH", "JOYBOOTH-EXIT-F")
    patch(e, "ROCKVIL-MALL", [
        {"when": {"flag": {"name": "wearing_headset", "value": True}}, "then": "block",
         "message": "You'll have to remove the headset first."},
        {"when": {}, "then": "allow"},
    ])
    print("Patched JOYBOOTH / JOYBOOTH-EXIT-F")
    changes += 1

    # ── Group 11: Theatre Edge Removal ────────────────────────────────────────

    before = len(rooms["CINEMA"]["edges"])
    rooms["CINEMA"]["edges"] = [
        e for e in rooms["CINEMA"]["edges"] if e.get("gate_fn") != "THEATRE-ENTER-F"
    ]
    after = len(rooms["CINEMA"]["edges"])
    if before - after != 1:
        sys.exit(f"ERROR: expected to remove 1 THEATRE-ENTER-F edge from CINEMA, removed {before - after}")
    print("Removed CINEMA / THEATRE-ENTER-F")
    changes += 1

    # ── Validation ────────────────────────────────────────────────────────────

    assert changes == 20, f"Expected 20 changes, applied {changes}"

    room_count = len(rooms)
    open_count = sum(1 for r in rooms.values() for e in r["edges"] if e.get("type") == "open")
    door_count = sum(1 for r in rooms.values() for e in r["edges"] if e.get("type") == "door")
    gated_count = sum(1 for r in rooms.values() for e in r["edges"] if e.get("type") == "gated")
    populated_count = sum(
        1 for r in rooms.values() for e in r["edges"]
        if e.get("type") == "gated" and (e.get("rules") or e.get("gate_ref"))
    )
    stub_count = sum(
        1 for r in rooms.values() for e in r["edges"]
        if e.get("type") == "gated" and not e.get("rules") and not e.get("gate_ref")
    )

    allowed_stub_fns = {
        "BROWN-TUBECAR-ENTER-F", "BROWN-TUBECAR-EXIT-F",
        "RED-TUBECAR-ENTER-F", "RED-TUBECAR-EXIT-F",
        "TUBECAR-AT-JUNCTION-ENTER-F",
    }
    bad_stubs = [
        (rid, e.get("gate_fn"))
        for rid, rdata in rooms.items()
        for e in rdata["edges"]
        if e.get("type") == "gated" and not e.get("rules") and not e.get("gate_ref")
        and e.get("gate_fn") not in allowed_stub_fns
    ]

    cinema_edges = len(rooms["CINEMA"]["edges"])
    ph_edge = next(
        (e for e in rooms["PARKVIEW-HALL"]["edges"]
         if e.get("direction") == "E" or "OUT" in (e.get("aliases") or [])),
        None,
    )

    errors = []
    if room_count != 178:
        errors.append(f"Room count: expected 178, got {room_count}")
    if open_count != 359:
        errors.append(f"Open edges: expected 359, got {open_count}")
    if door_count != 1:
        errors.append(f"Door edges: expected 1, got {door_count}")
    if gated_count != 110:
        errors.append(f"Gated edges: expected 110, got {gated_count}")
    if populated_count != 98:
        errors.append(f"Populated gated: expected 98, got {populated_count}")
    if stub_count != 12:
        errors.append(f"Stub gated: expected 12, got {stub_count}")
    if bad_stubs:
        errors.append(f"Bad stub gate_fns: {bad_stubs}")
    if cinema_edges != 3:
        errors.append(f"CINEMA edges: expected 3, got {cinema_edges}")
    if ph_edge is None:
        errors.append("PARKVIEW-HALL E edge not found")
    elif ph_edge.get("type") != "open":
        errors.append(f"PARKVIEW-HALL E edge type: expected 'open', got {ph_edge.get('type')!r}")
    elif "rules" in ph_edge:
        errors.append("PARKVIEW-HALL E edge still has 'rules' key")
    elif "gate_fn" in ph_edge:
        errors.append("PARKVIEW-HALL E edge still has 'gate_fn' key")

    print()
    print("── Summary ──────────────────────────────────────")
    print(f"  Changes applied    : {changes}")
    print(f"  Room count         : {room_count}  (expected 178)")
    print(f"  Open edges         : {open_count}  (expected 359)")
    print(f"  Door edges         : {door_count}  (expected 1)")
    print(f"  Gated edges        : {gated_count}  (expected 110)")
    print(f"  Populated gated    : {populated_count}  (expected 98)")
    print(f"  Stub gated         : {stub_count}  (expected 12)")
    print(f"  CINEMA edge count  : {cinema_edges}  (expected 3)")
    if ph_edge:
        print(f"  PARKVIEW-HALL E    : type={ph_edge.get('type')!r}, "
              f"has_rules={'rules' in ph_edge}, has_gate_fn={'gate_fn' in ph_edge}")

    if errors:
        print()
        for err in errors:
            print(f"VALIDATION ERROR: {err}")
        sys.exit(1)

    print()
    print("All validation checks passed.")

    with open(out_path, "w") as f:
        json.dump(graph, f, indent=2, sort_keys=False)
        f.write("\n")

    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
