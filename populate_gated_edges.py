#!/usr/bin/env python3
"""Populate gated edge rules in world_graph.json and write world_graph_v2.json."""

import json
import copy

INPUT_FILE = "world_graph_json.txt"
OUTPUT_FILE = "world_graph_v2.json"

# ---------------------------------------------------------------------------
# Data tables
# ---------------------------------------------------------------------------

CAT_A = {
    "CITY-HALL-ENTER-F":      {"target": "CITY-HALL",      "open": 600,  "close": 1080, "name": "City Hall"},
    "COURTHOUSE-ENTER-F":     {"target": "COURTHOUSE",     "open": 570,  "close": 990,  "name": "The courthouse"},
    "ROCKVIL-HIGH-ENTER-F":   {"target": "ROCKVIL-HIGH",   "open": 420,  "close": 1020, "name": "The school"},
    "BANK-ENTER-F":           {"target": "BANK",           "open": 480,  "close": 960,  "name": "The bank"},
    "DRUG-STORE-ENTER-F":     {"target": "DRUG-STORE",     "open": 480,  "close": 1305, "name": "The drug store"},
    "HARDWARE-STORE-ENTER-F": {"target": "HARDWARE-STORE", "open": 600,  "close": 1080, "name": "The hardware store"},
    "LIQUOR-STORE-ENTER-F":   {"target": "LIQUOR-STORE",   "open": 660,  "close": 1320, "name": "The liquor store"},
    "GUN-SHOP-ENTER-F":       {"target": "GUN-SHOP",       "open": 630,  "close": 1230, "name": "The gun store"},
}

CAT_B = {
    "SKYBUS-TERMINAL-ENTER-F":      {"target": "SKYBUS-TERMINAL",      "blocked": [2071], "message": "The entrance is boarded over."},
    "KENNEDY-PARK-ENTER-F":         {"target": "KENNEDY-PARK",         "blocked": [2071], "message": "The entrances to the townhouses are all locked."},
    "STUDENT-UNION-ENTER-F":        {"target": "STUDENT-UNION",        "blocked": [2071], "message": "The entrance is boarded over."},
    "LECTURE-HALL-ENTER-F":         {"target": "LECTURE-HALL",         "blocked": [2071], "message": "The entrance is boarded over."},
    "ST-MICHAELS-ENTER-F":          {"target": "ST-MICHAELS",          "blocked": [2061], "message": "The entrance is boarded over."},
    "CONSTRUCTION-SITE-5-ENTER-F":  {"target": "CONSTRUCTION-SITE-5",  "blocked": [2061], "message": "The building is closed, its doorways and windows boarded over."},
    "HALLEY-PARK-WEST-ENTER-F":     {"target": "HALLEY-PARK-WEST",     "blocked": [2071], "message": "The gates of the estate are all locked; you'd be shot on sight if found within the walls."},
    "RIVERSIDE-PARK-ENTER-F":       {"target": "RIVERSIDE-PARK",       "blocked": [2071], "message": "A guard stops you and informs you that admission to the park is restricted."},
    "CLOSED-FACTORY-ENTER-F":       {"target": "CLOSED-FACTORY",       "blocked": [2061, 2071], "message": "The soup kitchen is closed down."},
    "SYMPHONY-HALL-ENTER-F":        {"target": "SYMPHONY-HALL",        "blocked": [2071], "message": "Symphony Hall has been closed for several years now."},
    "HALLEY-PARK-EAST-ENTER-F":     {"target": "HALLEY-PARK-EAST",     "blocked": [2071], "message": "The gates of the estate are all locked; you'd be shot on sight if found within the walls."},
}

CAT_C = {
    "DUNBARS-ENTER-F": {
        "target": "DUNBARS",
        "name": "Dunbar's",
        "year_block": [2071],
        "year_block_msg": "A security guard stops you at the doorway and turns you away.",
        "hours": {
            "default": (600, 1260)
        }
    },
    "MAIN-LIBRARY-ENTER-F": {
        "target": "MAIN-LIBRARY",
        "name": "The library",
        "year_block": [],
        "year_block_msg": None,
        "hours": {
            2041: (510, 1320),
            2051: (510, 1320),
            2061: (600, 1260),
            2071: (750, 990)
        }
    },
    "ROCKVIL-MALL-ENTER-F": {
        "target": "ROCKVIL-MALL",
        "name": "The Mall",
        "year_block": [],
        "year_block_msg": None,
        "hours": {
            2041: (480, 1320),
            2051: (480, 1320),
            2061: (480, 1320),
            2071: (720, 1080)
        }
    },
    "STOCK-EXCHANGE-ENTER-F": {
        "target": "STOCK-EXCHANGE",
        "name": "The stock exchange building",
        "year_block": [],
        "year_block_msg": None,
        "hours": {
            2041: (360, 1320),
            2051: (420, 1320),
            2061: (420, 1320),
            2071: (420, 1320)
        }
    },
    "AQUARIUM-ENTER-F": {
        "target": "AQUARIUM",
        "name": "The Aquarium",
        "year_block": [],
        "year_block_msg": None,
        "hours": {
            2041: (600, 1320),
            2051: (600, 1200),
            2061: (660, 1080),
            2071: (720, 1020)
        }
    },
    "TRAIN-STATION-ENTER-F": {
        "target": "TRAIN-STATION",
        "name": "The station",
        "year_block": [],
        "year_block_msg": None,
        "hours": {
            2041: (660, 1260),
            2051: None,
            2061: None,
            2071: None
        }
    },
    "HALLEY-MUSEUM-ENTER-F": {
        "target": "HALLEY-MUSEUM",
        "name": "The museum",
        "year_block": [2061, 2071],
        "year_block_msg": "The entrance is boarded over.",
        "hours": {
            2041: (615, 1185),  # note: spec says 600-1290 for HALLEY, 615-1185 for RAILROAD
            2051: (600, 1290)
        }
    },
    "RAILROAD-MUSEUM-ENTER-F": {
        "target": "RAILROAD-MUSEUM",
        "name": "The museum",
        "year_block": [2061, 2071],
        "year_block_msg": "The entrance is boarded over.",
        "hours": {
            2041: (615, 1185),
            2051: (615, 1185)
        }
    },
    "BOOKSTORE-ENTER-F": {
        "target": "BOOKSTORE",
        "name": "The bookstore",
        "year_block": [2071],
        "year_block_msg": "The bookstore is locked. Through the grimy window, the bookstore looks empty and barren.",
        "hours": {
            "default": (501, 1083)
        }
    },
}

# Fix HALLEY-MUSEUM hours per spec (600-1290 for 2041)
CAT_C["HALLEY-MUSEUM-ENTER-F"]["hours"][2041] = (600, 1290)

FOODVILLE = {
    "gate_fn": "FOODVILLE-ENTER-F",
    "name": "The Foodville",
    "year_block": [],
    "hours": {
        2041: (480, 1320),
        2051: (480, 1320),
        2061: (600, 1140),
        2071: (700, 960)
    },
    "target_by_source": {
        "MAIN-AND-WICKER": "FOODVILLE-2",
        "__default__": "FOODVILLE-1"
    },
    "year_block_2071_msg": "According to a note on the door, the Foodville is only open from 11:30am until 4:00 in the afternoon."
}

CAT_D = {
    "ROYS-PAGODA-ENTER-F":     {"target": "ROYS-PAGODA",     "object": "restaurant"},
    "EZZIS-BAR-ENTER-F":       {"target": "EZZIS-BAR",       "object": "bar"},
    "THE-COACHMAN-ENTER-F":    {"target": "THE-COACHMAN",    "object": "restaurant"},
    "BURGER-MEISTER-ENTER-F":  {"target": "BURGER-MEISTER",  "object": "restaurant"},
    "CINEMA-ENTER-F":          {"target": "CINEMA",           "object": "movie theatre"},
    "SIMONS-ENTER-F":          {"target": "SIMONS",           "object": "restaurant"},
    "POOL-HALL-ENTER-F":       {"target": "POOL-HALL",        "object": "pool hall"},
}

TUBES_TARGETS = {
    "HALLEY-PARK-WEST":   "TUBE-AT-PARK",
    "ROCKVIL-STADIUM":    "TUBE-AT-STADIUM",
    "SKYBUS-TERMINAL":    "TUBE-JUNCTION",
    "ELM-AND-UNIVERSITY": "TUBE-AT-UNIVERSITY",
    "ELM-AND-RIVER":      "TUBE-AT-HEIMAN",
    "BODANSKI-SQUARE":    "TUBE-AT-BODANSKI",
    "TERMINAL":           "TUBE-AT-AIRPORT",
    "WICKER-AND-RIVER":   "TUBE-AT-FACTORY",
}

REMOVE_GATE_FNS = {
    "OFFICE-BUILDING-ENTER-F",
    "APARTMENT-ENTER-F",
    "RIVER-ENTER-F",
    "BASE-GATE-ENTER-F",
    "SPACEPORT-ENTER-F",
    "NO-ENTRY-TO-HEIMAN-WORLD-F",
    "NO-ENTRANCE-TO-PARK-F",
    "CHURCH-STREET-PARK-EXIT-F",
    "WAREHOUSE-1-EXIT-F",
    "TRAIN-STATION-EXIT-F",
    "RAMP-MOVEMENT-F",
}

TUBE_ACCESS_DEF = [
    {"when": {"syear": {"eq": [2071]}}, "then": "block", "message": "The Tube system closed five years ago!"},
    {"when": {"syear": {"eq": [2051, 2061]}, "stime": {"outside": [420, 1250]}}, "then": "block", "message": "As usual, the Tubes have closed for curfew."},
    {"when": {}, "then": "allow"}
]

SUBURBS_RULES = [
    {"when": {"syear": {"eq": [2071]}}, "then": "block", "message": "The collapsed highway blocks the road."},
    {"when": {}, "then": "block", "message": "WARNING: You have reached the boundary of this simulation."}
]

# ---------------------------------------------------------------------------
# Rule generators
# ---------------------------------------------------------------------------

def rules_cat_a(cfg):
    name, open_t, close_t = cfg["name"], cfg["open"], cfg["close"]
    return [
        {"when": {"stime": {"lt": open_t}}, "then": "block", "message": f"{name} isn't open yet."},
        {"when": {"stime": {"gt": close_t}}, "then": "block", "message": f"{name} seems to be closed for the night."},
        {"when": {}, "then": "allow"}
    ]


def rules_cat_b(cfg):
    return [
        {"when": {"syear": {"eq": cfg["blocked"]}}, "then": "block", "message": cfg["message"]},
        {"when": {}, "then": "allow"}
    ]


def rules_cat_c(cfg):
    """Generate rules for category C (time + year variable hours)."""
    rules = []
    name = cfg["name"]
    year_block = cfg.get("year_block", [])
    hours = cfg["hours"]

    # 1. Year-only block rule
    if year_block:
        rules.append({
            "when": {"syear": {"eq": year_block}},
            "then": "block",
            "message": cfg["year_block_msg"]
        })

    # 2. Handle hours
    has_default = "default" in hours

    if has_default:
        # default applies to all non-blocked years; emit without syear condition
        open_t, close_t = hours["default"]
        rules.append({
            "when": {"stime": {"outside": [open_t, close_t]}},
            "then": "block",
            "message": f"{name} isn't open yet."
        })
    else:
        # Group years by (open, close) tuple, skipping None (always open) and blocked years
        blocked_set = set(year_block)
        tuple_to_years = {}
        for yr, h in hours.items():
            if isinstance(yr, str):
                continue
            if yr in blocked_set:
                continue
            if h is None:
                continue
            tuple_to_years.setdefault(h, []).append(yr)

        # Sort groups by open time descending (most restrictive first)
        for h_tuple, years in sorted(tuple_to_years.items(), key=lambda x: (-x[0][0], -x[0][1])):
            open_t, close_t = h_tuple
            rules.append({
                "when": {
                    "syear": {"eq": sorted(years)},
                    "stime": {"outside": [open_t, close_t]}
                },
                "then": "block",
                "message": f"{name} isn't open yet."
            })

    # 3. Catch-all
    rules.append({"when": {}, "then": "allow"})
    return rules


def rules_cat_c_train_station():
    """Special case: TRAIN-STATION-ENTER-F."""
    return [
        {"when": {"syear": {"eq": [2041]}, "stime": {"outside": [660, 1260]}}, "then": "block", "message": "The station isn't open yet."},
        {"when": {}, "then": "allow"}
    ]


def rules_foodville(room_id, cfg):
    """Generate rules for FOODVILLE-ENTER-F."""
    rules = []
    hours = cfg["hours"]
    name = cfg["name"]

    # Group years by hours tuple (no year_block for foodville)
    # 2071 has a custom message
    yr_2071_hours = hours.get(2071)

    # Non-2071 hours grouped
    tuple_to_years = {}
    for yr, h in hours.items():
        if yr == 2071:
            continue
        if h is None:
            continue
        tuple_to_years.setdefault(h, []).append(yr)

    # Emit 2071 rule first with custom message
    if yr_2071_hours is not None:
        open_t, close_t = yr_2071_hours
        rules.append({
            "when": {"syear": {"eq": [2071]}, "stime": {"outside": [open_t, close_t]}},
            "then": "block",
            "message": cfg["year_block_2071_msg"]
        })

    # Remaining year groups
    for h_tuple, years in sorted(tuple_to_years.items(), key=lambda x: (-x[0][0], -x[0][1])):
        open_t, close_t = h_tuple
        rules.append({
            "when": {
                "syear": {"eq": sorted(years)},
                "stime": {"outside": [open_t, close_t]}
            },
            "then": "block",
            "message": f"{name} isn't open yet."
        })

    rules.append({"when": {}, "then": "allow"})
    return rules


def rules_cat_d(cfg):
    obj = cfg["object"]
    return [
        {"when": {"syear": {"eq": [2041]}}, "then": "allow"},
        {"when": {"stime": {"outside": [420, 1200]}}, "then": "block", "message": f"The {obj} is closed at this hour, of course."},
        {"when": {}, "then": "allow"}
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Try both possible filenames
    import os
    for candidate in ("world_graph_json.txt", "world_graph.json"):
        if os.path.exists(candidate):
            input_file = candidate
            break
    else:
        raise FileNotFoundError("Neither world_graph_json.txt nor world_graph.json found")

    print(f"Reading {input_file} ...")
    with open(input_file) as f:
        data = json.load(f)

    data = copy.deepcopy(data)

    # Add tube_access gate_def
    data.setdefault("gate_defs", {})["tube_access"] = TUBE_ACCESS_DEF

    # Counters
    cat_counts = {"A": 0, "B": 0, "C": 0, "C_foodville": 0, "D": 0, "tubes": 0, "suburbs": 0}
    removed_count = 0
    unpopulated = {}  # gate_fn -> count

    all_known_fns = (
        set(CAT_A) | set(CAT_B) | set(CAT_C) |
        {FOODVILLE["gate_fn"]} | set(CAT_D) |
        {"TUBES-ENTER-F", "SUBURBS-ENTER-F"} |
        REMOVE_GATE_FNS
    )

    for room_id, room in data["rooms"].items():
        edges_to_keep = []
        for edge in room.get("edges", []):
            if edge.get("type") != "gated":
                edges_to_keep.append(edge)
                continue

            fn = edge.get("gate_fn", "")

            # --- Remove ---
            if fn in REMOVE_GATE_FNS:
                print(f"  REMOVE {room_id}:{edge.get('direction', '?')} ({fn})")
                removed_count += 1
                continue

            # --- Category A ---
            if fn in CAT_A:
                cfg = CAT_A[fn]
                edge["rules"] = rules_cat_a(cfg)
                edge["target"] = cfg["target"]
                cat_counts["A"] += 1

            # --- Category B ---
            elif fn in CAT_B:
                cfg = CAT_B[fn]
                edge["rules"] = rules_cat_b(cfg)
                edge["target"] = cfg["target"]
                cat_counts["B"] += 1

            # --- Category C special: TRAIN-STATION-ENTER-F ---
            elif fn == "TRAIN-STATION-ENTER-F":
                cfg = CAT_C[fn]
                edge["rules"] = rules_cat_c_train_station()
                edge["target"] = cfg["target"]
                cat_counts["C"] += 1

            # --- Category C ---
            elif fn in CAT_C:
                cfg = CAT_C[fn]
                edge["rules"] = rules_cat_c(cfg)
                edge["target"] = cfg["target"]
                cat_counts["C"] += 1

            # --- FOODVILLE special case ---
            elif fn == FOODVILLE["gate_fn"]:
                tb = FOODVILLE["target_by_source"]
                edge["target"] = tb.get(room_id, tb["__default__"])
                edge["rules"] = rules_foodville(room_id, FOODVILLE)
                cat_counts["C_foodville"] += 1

            # --- Category D ---
            elif fn in CAT_D:
                cfg = CAT_D[fn]
                edge["rules"] = rules_cat_d(cfg)
                edge["target"] = cfg["target"]
                cat_counts["D"] += 1

            # --- TUBES-ENTER-F ---
            elif fn == "TUBES-ENTER-F":
                if room_id not in TUBES_TARGETS:
                    print(f"  WARNING: TUBES-ENTER-F in unexpected room {room_id}")
                else:
                    edge["target"] = TUBES_TARGETS[room_id]
                edge["gate_ref"] = "tube_access"
                edge.pop("rules", None)
                cat_counts["tubes"] += 1

            # --- SUBURBS-ENTER-F ---
            elif fn == "SUBURBS-ENTER-F":
                edge["rules"] = copy.deepcopy(SUBURBS_RULES)
                # target stays null
                cat_counts["suburbs"] += 1

            # --- Unknown / unpopulated ---
            else:
                unpopulated[fn] = unpopulated.get(fn, 0) + 1

            edges_to_keep.append(edge)

        room["edges"] = edges_to_keep

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nWrote {OUTPUT_FILE}")

    # Summary
    print("\n=== Summary ===")
    print(f"  Category A populated:         {cat_counts['A']}")
    print(f"  Category B populated:         {cat_counts['B']}")
    print(f"  Category C populated:         {cat_counts['C']}")
    print(f"  Category C (Foodville):       {cat_counts['C_foodville']}")
    print(f"  Category D populated:         {cat_counts['D']}")
    print(f"  TUBES-ENTER-F populated:      {cat_counts['tubes']}")
    print(f"  SUBURBS-ENTER-F populated:    {cat_counts['suburbs']}")
    total_populated = sum(cat_counts.values())
    print(f"  Total populated:              {total_populated}")
    print(f"  Edges removed:                {removed_count}")

    print(f"\n  Unpopulated gated edges ({sum(unpopulated.values())} total):")
    for fn, cnt in sorted(unpopulated.items()):
        print(f"    {fn}: {cnt}")

    # Edge type counts in output
    type_counts = {}
    for room in data["rooms"].values():
        for edge in room.get("edges", []):
            t = edge.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
    print(f"\n  Output edge counts by type:")
    for t, cnt in sorted(type_counts.items()):
        print(f"    {t}: {cnt}")


if __name__ == "__main__":
    main()
