#!/usr/bin/env python3
"""Session 11: PRISM Edges + Tubecar Instant Travel.

Reads world_graph.json (canonical: 178 rooms, 470 edges, 1 gate_def tube_access),
applies all session 11 transformations, and writes the result back in place.
"""

import json
import os
import sys

INPUT_FILE = "world_graph.json"
OUTPUT_FILE = "world_graph.json"

# ---------------------------------------------------------------------------
# Part A: New gate_defs
# ---------------------------------------------------------------------------

NEW_GATE_DEFS = {
    "mode_standard": [
        {"when": {"flag": {"name": "part_flag", "eq": 4}}, "then": "block", "message": "That mode is not currently active."},
        {"when": {"flag": {"name": "psych_test_active", "eq": True}}, "then": "block", "message": "It would be impolite to leave during the psych test."},
        {"when": {"flag": {"name": "simulating", "eq": True}}, "then": "block", "message": "To resume normal computer functions, abort Simulation Mode."},
        {"when": {}, "then": "allow"},
    ],
    "mode_comm": [
        {"when": {"flag": {"name": "simulating", "eq": True}}, "then": "block", "message": "To resume normal computer functions, abort Simulation Mode."},
        {"when": {}, "then": "allow"},
    ],
    "mode_simulation": [
        {"when": {"flag": {"name": "rorschach_queued", "eq": True}}, "then": "block", "message": "Access currently denied...see Perelman."},
        {"when": {"flag": {"name": "psych_test_active", "eq": True}}, "then": "block", "message": "It would be impolite to leave during the psych test."},
        {"when": {"flag": {"name": "sim_cleared", "eq": False}}, "then": "block", "message": "You are not yet cleared for Simulation Mode. Please await approval."},
        {"when": {}, "then": "allow"},
    ],
    "outlet_access": [
        {"when": {"flag": {"name": "part_flag", "eq": 4}}, "then": "block", "message": "There are currently no active outlets."},
        {"when": {}, "then": "allow"},
    ],
    "sim_2051": [
        {"when": {"flag": {"name": "completed_tasks", "eq": False}}, "then": "block", "message": "That simulation year is not yet available."},
        {"when": {}, "then": "allow"},
    ],
    "sim_2061": [
        {"when": {"flag": {"name": "sim_2061_unlocked", "eq": False}}, "then": "block", "message": "That simulation year is not yet available."},
        {"when": {}, "then": "allow"},
    ],
    "sim_2071": [
        {"when": {"flag": {"name": "sim_2071_unlocked", "eq": False}}, "then": "block", "message": "That simulation year is not yet available."},
        {"when": {}, "then": "allow"},
    ],
    "sim_2081": [
        {"when": {"flag": {"name": "sim_2081_unlocked", "eq": False}}, "then": "block", "message": "That simulation year is not yet available."},
        {"when": {}, "then": "allow"},
    ],
    "sim_2091": [
        {"when": {"flag": {"name": "part_flag", "neq": 4}}, "then": "block", "message": "That simulation year is not yet available."},
        {"when": {}, "then": "allow"},
    ],
}

# ---------------------------------------------------------------------------
# Part B: Mode edges
# ---------------------------------------------------------------------------

# (direction, target_room, gate_ref)
MODE_TARGETS = [
    ("mode_library",    "LIBRARY-ROOM",    "mode_standard"),
    ("mode_sleep",      "SLEEP-ROOM",      "mode_standard"),
    ("mode_comm",       "COMM-ROOM",       "mode_comm"),
    ("mode_interface",  "INTERFACE-ROOM",  "mode_standard"),
    ("mode_simulation", "SIMULATION-ROOM", "mode_simulation"),
]

MODE_ROOMS = {"LIBRARY-ROOM", "SLEEP-ROOM", "COMM-ROOM", "INTERFACE-ROOM", "SIMULATION-ROOM"}

OUTLET_ROOMS = [
    "CONTROL-CENTER", "ROOFTOP", "OFFICE", "CAFETERIA", "CORE", "NEWS",
]

# ---------------------------------------------------------------------------
# Part C: Outlet edges
# ---------------------------------------------------------------------------

# COMM-ROOM gets these outlet edges
COMM_OUTLET_EDGES = [
    ("outlet_ppcc", "CONTROL-CENTER"),
    ("outlet_rcro", "ROOFTOP"),
    ("outlet_peof", "OFFICE"),
    ("outlet_pcaf", "CAFETERIA"),
    ("outlet_maco", "CORE"),
    ("outlet_wnnf", "NEWS"),
]

# ---------------------------------------------------------------------------
# Part D: Simulation year edges (on SIMULATION-ROOM)
# ---------------------------------------------------------------------------

# (direction, target, type, gate_ref_or_None)
SIM_YEAR_EDGES = [
    ("sim_2041", "KENNEDY-PARK",       "open",  None),
    ("sim_2051", "TUBE-AT-UNIVERSITY", "gated", "sim_2051"),
    ("sim_2061", "SOUTHWAY-AND-RIVER", "gated", "sim_2061"),
    ("sim_2071", "BODANSKI-SQUARE",    "gated", "sim_2071"),
    ("sim_2081", "MAIN-AND-WICKER",    "gated", "sim_2081"),
    ("sim_2091", "SOLARIUM",           "gated", "sim_2091"),
]

# ---------------------------------------------------------------------------
# Part E: Tube network
# ---------------------------------------------------------------------------

# Maps room ID → tube_* direction identifier
TUBE_DIR = {
    "TUBE-AT-STADIUM":   "tube_stadium",
    "TUBE-AT-PARK":      "tube_park",
    "TUBE-JUNCTION":     "tube_junction",
    "TUBE-AT-HEIMAN":    "tube_heiman",
    "TUBE-AT-FACTORY":   "tube_factory",
    "TUBE-AT-AIRPORT":   "tube_airport",
    "TUBE-AT-BODANSKI":  "tube_bodanski",
    "TUBE-AT-UNIVERSITY":"tube_university",
}

RED_LINE   = ["TUBE-AT-STADIUM", "TUBE-AT-PARK", "TUBE-JUNCTION", "TUBE-AT-HEIMAN", "TUBE-AT-FACTORY"]
BROWN_LINE = ["TUBE-AT-AIRPORT", "TUBE-AT-BODANSKI", "TUBE-JUNCTION", "TUBE-AT-UNIVERSITY"]

REMOVE_ROOMS = ["RED-TUBECAR", "BROWN-TUBECAR"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    src = INPUT_FILE
    if not os.path.exists(src):
        print(f"ERROR: {src} not found", file=sys.stderr)
        sys.exit(1)

    with open(src) as f:
        wg = json.load(f)

    rooms = wg["rooms"]

    # --- Part A: gate_defs ---
    wg["gate_defs"].update(NEW_GATE_DEFS)

    # --- Part B: mode edges ---
    all_mode_sources = list(MODE_ROOMS) + OUTLET_ROOMS
    for rid in all_mode_sources:
        for direction, target, gate_ref in MODE_TARGETS:
            if rid == target:
                continue  # self-exclusion
            rooms[rid]["edges"].append({
                "direction": direction,
                "gate_ref": gate_ref,
                "target": target,
                "type": "gated",
            })

    # --- Part C: outlet edges ---
    for direction, target in COMM_OUTLET_EDGES:
        rooms["COMM-ROOM"]["edges"].append({
            "direction": direction,
            "gate_ref": "outlet_access",
            "target": target,
            "type": "gated",
        })
    for rid in OUTLET_ROOMS:
        rooms[rid]["edges"].append({
            "direction": "OUT",
            "target": "COMM-ROOM",
            "type": "open",
        })

    # --- Part D: simulation year edges ---
    for direction, target, etype, gate_ref in SIM_YEAR_EDGES:
        edge = {"direction": direction, "target": target, "type": etype}
        if gate_ref is not None:
            edge["gate_ref"] = gate_ref
        rooms["SIMULATION-ROOM"]["edges"].append(edge)

    # --- Pre-E: resolve always-blocked null-target edges to self-loops ---
    # The canonical input may contain gated edges whose catch-all rule is
    # "then: block", making the target unreachable.  These edges predate
    # session 11 and are not tubecar stubs.  We give them a self-loop target
    # (source room) so the graph has no null targets while leaving edge count
    # and block semantics unchanged.
    for rid, room in rooms.items():
        for e in room.get("edges", []):
            if e.get("target") is not None:
                continue
            rules = e.get("rules") or []
            if rules and rules[-1].get("when") == {} and rules[-1].get("then") == "block":
                e["target"] = rid

    # --- Part E1: remove tubecar rooms ---
    for rid in REMOVE_ROOMS:
        del rooms[rid]

    # --- Part E2: remove null-target stub edges on tube stations ---
    for rid in TUBE_DIR:
        rooms[rid]["edges"] = [
            e for e in rooms[rid].get("edges", [])
            if e.get("target") is not None
        ]

    # --- Part E3: add station-to-station edges ---
    def add_tube_edges(line):
        for station in line:
            for dest in line:
                if station == dest:
                    continue
                rooms[station]["edges"].append({
                    "direction": TUBE_DIR[dest],
                    "gate_ref": "tube_access",
                    "target": dest,
                    "type": "gated",
                })

    add_tube_edges(RED_LINE)
    add_tube_edges(BROWN_LINE)

    # --- Write output ---
    out = json.dumps(wg, sort_keys=True, indent=2)
    with open(OUTPUT_FILE, "w") as f:
        f.write(out)
        f.write("\n")

    # Quick summary
    total_edges = sum(len(r.get("edges", [])) for r in rooms.values())
    print(f"Wrote {OUTPUT_FILE}")
    print(f"  Rooms: {len(rooms)}")
    print(f"  Edges: {total_edges}")
    print(f"  gate_defs: {len(wg['gate_defs'])}")


if __name__ == "__main__":
    main()
