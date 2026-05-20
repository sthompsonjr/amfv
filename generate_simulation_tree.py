#!/usr/bin/env python3
"""
Session 13: Generate simulation_tree.json

Parses simulation_state_inventory.md and score_trigger_extraction.md,
merges with hardcoded structural data, and writes simulation_tree.json.
"""

import json
import os
import re
import sys

INPUT_DIR = "/mnt/project"
OUTPUT_PATH = "/mnt/user-data/outputs/simulation_tree.json"

# ---------------------------------------------------------------------------
# Scope and category lookup tables
# ---------------------------------------------------------------------------

SCOPE_MAP = {
    "time": "facility",
    "date": "facility",
    "month": "facility",
    "sim_level_table": "facility",
    "completed_tasks": "facility",
    "simulating": "facility",
    "short_first_simulation": "facility",
    "part_flag": "facility",
    "mode": "facility",
    "current_directory": "facility",
    "current_file": "facility",
    "highlight_cnt": "facility",
    "directory_cnt": "facility",
    "number_of_messages": "facility",
    "next_sleep_time": "facility",
    "next_sleep_date": "facility",
    "feed_buffer": "facility",
    "interface_change": "facility",
    "interface_warning": "facility",
    "last_abe_time": "facility",
    "perelman_noticed": "facility",
    "siege": "facility",
    "seige": "facility",
    "sabotage_counter": "facility",
    "ryder_counter": "facility",
    "ryder_recorded": "facility",
    "lose_counter": "facility",
    "air_conditioning_counter": "facility",
    "suffocate_counter": "facility",
    "grimwold_counter": "facility",
    "scores_fired": "global",
}

CATEGORY_MAP = {
    1: "clock",
    2: "progression",
    3: "chapter",
    4: "scoring",
    5: "clock",
    7: "npc",
    8: "environment",
    9: "prism_mode",
    10: "object_flag",
}

EXTRA_STATE_DEFS = {
    "scores_fired": {
        "type": "array",
        "init": [],
        "scope": "global",
        "category": "scoring",
        "note": (
            "Set of score indices already triggered. Persists across all sim sessions. "
            "Enforces zero-on-score mechanic."
        ),
    },
    "jailed": {
        "type": "bool",
        "init": False,
        "scope": "simulation",
        "category": "environment",
        "note": "True while player is in jail cell.",
    },
    "recording": {
        "type": "bool",
        "init": False,
        "scope": "simulation",
        "category": "scoring",
        "note": "True when player has activated RECORD. Gates all scoring.",
    },
}


# ---------------------------------------------------------------------------
# Part A: Parse simulation_state_inventory.md
# ---------------------------------------------------------------------------

def normalize_name(raw: str) -> str:
    """Uppercase -> lowercase, hyphens -> underscores."""
    return raw.strip().lower().replace("-", "_")


def parse_init_value(raw: str):
    """
    Returns (python_value, type_string).
    """
    v = raw.strip()

    # Array-like: starts with [ and ends with ]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1]
        parts = [p.strip() for p in inner.split(",")]
        parsed = []
        for p in parts:
            try:
                parsed.append(int(p))
            except ValueError:
                parsed.append(p)
        return parsed, "array"

    # Boolean false variants
    if v in ("<>", "false", "FALSE"):
        return False, "bool"

    # Boolean true variants
    if v in ("T", "true", "TRUE"):
        return True, "bool"

    # Integer
    try:
        return int(v), "int"
    except ValueError:
        pass

    # Fallback: keep as string
    return v, "string"


def parse_purpose_for_bool(purpose: str) -> bool:
    """Return True if purpose text clearly indicates a boolean flag."""
    lowered = purpose.lower()
    flag_indicators = [
        "flag", "whether", "true if", "true when", "true while",
        "has been", "is set", "is active", "is in effect",
    ]
    return any(ind in lowered for ind in flag_indicators)


def parse_categories_1_to_9(lines, cat_num):
    """Parse a standard state table: | Global | Init | Purpose | Assessment |"""
    entries = {}
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        cols = [c.strip() for c in stripped.split("|")]
        cols = [c for c in cols if c != ""]
        if len(cols) < 4:
            continue
        # Detect header row
        if cols[0].lower() in ("global", "object"):
            in_table = True
            continue
        # Detect separator row
        if cols[0].startswith("---"):
            continue
        if not in_table:
            continue

        assessment = cols[3].strip()
        if assessment.lower().startswith("skippable"):
            continue

        raw_name = cols[0].strip()
        raw_init = cols[1].strip()
        purpose = cols[2].strip()

        name = normalize_name(raw_name)
        init_val, type_str = parse_init_value(raw_init)

        # Override type to bool if init is 0 but purpose indicates a flag
        if init_val == 0 and type_str == "int" and parse_purpose_for_bool(purpose):
            type_str = "bool"
            init_val = False

        scope = SCOPE_MAP.get(name, "simulation")
        category = CATEGORY_MAP.get(cat_num, "simulation")

        entry = {
            "type": type_str,
            "init": init_val,
            "scope": scope,
            "category": category,
        }
        if assessment.lower().startswith("simplifiable"):
            entry["note"] = f"Simplifiable: {purpose}"

        entries[name] = entry

    return entries


def parse_category_10(lines):
    """Parse object flags table: | Object | Flag | Purpose | Assessment |"""
    entries = {}
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        cols = [c.strip() for c in stripped.split("|")]
        cols = [c for c in cols if c != ""]
        if len(cols) < 4:
            continue
        if cols[0].lower() == "object":
            in_table = True
            continue
        if cols[0].startswith("---"):
            continue
        if not in_table:
            continue

        assessment = cols[3].strip()
        if assessment.lower().startswith("skippable"):
            continue

        obj_raw = cols[0].strip()
        flag_raw = cols[1].strip()
        purpose = cols[2].strip()

        obj_lower = obj_raw.lower().replace("-", "_").replace(" ", "_")
        flag_lower = flag_raw.lower().replace("-", "_").replace(" ", "_")

        # Special cases: inventory flags
        if "in player inventory" in flag_raw.lower() or "in spear-carrier" in flag_raw.lower():
            name = obj_lower + "_held"
        else:
            name = obj_lower + "_" + flag_lower

        entry = {
            "type": "bool",
            "init": False,
            "scope": "simulation",
            "category": "object_flag",
        }
        if assessment.lower().startswith("simplifiable"):
            entry["note"] = f"Simplifiable: {purpose}"

        entries[name] = entry

    return entries


def parse_state_defs(filepath: str) -> dict:
    """Parse simulation_state_inventory.md and return state_defs dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    result = {}
    # Split into category sections using ## Category N: header
    sections = re.split(r"\n##\s+Category\s+(\d+):", content)
    # sections[0] = preamble, then [1]=num, [2]=content, [3]=num, [4]=content, ...

    i = 1
    while i < len(sections) - 1:
        cat_num_str = sections[i].strip()
        cat_content = sections[i + 1]
        i += 2

        try:
            cat_num = int(cat_num_str)
        except ValueError:
            print(f"WARNING: Could not parse category number '{cat_num_str}', skipping.")
            continue

        # Skip category 6 (interrupts) and 11 (strings)
        if cat_num in (6, 11):
            continue

        cat_lines = cat_content.splitlines()

        if cat_num == 10:
            parsed = parse_category_10(cat_lines)
        else:
            parsed = parse_categories_1_to_9(cat_lines, cat_num)

        for k, v in parsed.items():
            if k not in result:
                result[k] = v

    # Apply EXTRA_STATE_DEFS (overrides parsed entries)
    for k, v in EXTRA_STATE_DEFS.items():
        result[k] = v

    return result


# ---------------------------------------------------------------------------
# Part B: year_init (fully hardcoded)
# ---------------------------------------------------------------------------

YEAR_INIT = {
    "2041": {
        "start_room": "KENNEDY-PARK",
        "state_overrides": {"credit": 600},
        "objects": [
            {"id": "WALLET", "location": "PLAYER"},
            {"id": "CREDIT-CARD", "location": "WALLET"},
            {"id": "DRIVERS-LICENSE", "location": "WALLET"},
            {"id": "KEY", "location": "PLAYER"},
            {"id": "CRIB", "location": "BEDROOM"},
            {"id": "FORMULA", "location": "REFRIGERATOR"},
            {"id": "SOUVENIR", "location": "TRAIN-STATION"},
            {"id": "NEWSPAPER-DISPENSER", "location": "BODANSKI-SQUARE"},
            {"id": "NEWSPAPER", "location": "BODANSKI-SQUARE"},
            {"id": "GOVERNMENT-OFFICIAL", "location": "CITY-HALL"},
            {"id": "OFFICIAL-SNACK", "location": "CITY-HALL"},
            {"id": "FIRETRUCK", "location": "FIREHOUSE"},
            {"id": "ANDERSON-DIRECTORY", "location": "HEALTH-CENTER"},
            {"id": "WATERPOOL", "location": "KENNEDY-PARK"},
            {"id": "STATUE", "location": "KENNEDY-PARK"},
            {"id": "PLAQUE", "location": "KENNEDY-PARK"},
            {"id": "FOUNTAIN", "location": "CHURCH-STREET-PARK"},
            {"id": "SODA", "location": "REFRIGERATOR"},
            {"id": "TURKEY-SANDWICH", "location": "REFRIGERATOR"},
            {"id": "HAM-SANDWICH", "location": "REFRIGERATOR"},
            {"id": "TURTLE", "location": "AQUARIUM"},
            {"id": "MANTA-RAY", "location": "AQUARIUM"},
            {"id": "DUCKS", "location": "HALLEY-PARK-WEST"},
        ],
        "room_flags": [
            {"room": "CHURCH-STREET-PARK", "set": ["OUTSIDEBIT", "PARKBIT"]}
        ],
        "interrupts_queue": [
            {"id": "i_sunrise_sunset", "ticks": -1},
            {"id": "i_city_noises", "ticks": 2},
        ],
    },
    "2051": {
        "start_room": "TUBE-AT-UNIVERSITY",
        "state_overrides": {"credit": 500},
        "objects": [
            {"id": "WALLET", "location": "PLAYER"},
            {"id": "CREDIT-CARD", "location": "WALLET"},
            {"id": "DRIVERS-LICENSE", "location": "WALLET"},
            {"id": "KEY", "location": "PLAYER"},
            {"id": "PARTITION", "location": "LIVING-ROOM"},
            {"id": "APPLE", "location": "REFRIGERATOR"},
            {"id": "GRANOLA-CLUSTER", "location": "REFRIGERATOR"},
            {"id": "GOVERNMENT-OFFICIAL", "location": "CITY-HALL"},
            {"id": "OFFICIAL-SNACK", "location": "CITY-HALL"},
            {"id": "PAMPHLET", "location": "TRAIN-STATION"},
            {"id": "NEWSPAPER-DISPENSER", "location": "BODANSKI-SQUARE"},
            {"id": "NEWSPAPER", "location": "BODANSKI-SQUARE"},
            {"id": "WATERPOOL", "location": "KENNEDY-PARK"},
            {"id": "STATUE", "location": "KENNEDY-PARK"},
            {"id": "PLAQUE", "location": "KENNEDY-PARK"},
            {"id": "FOUNTAIN", "location": "CHURCH-STREET-PARK"},
            {"id": "DUCKS", "location": "HALLEY-PARK-WEST"},
            {"id": "FIRETRUCK", "location": "FIREHOUSE"},
            {"id": "STEW", "location": "CLOSED-FACTORY"},
            {"id": "ANDERSON-DIRECTORY", "location": "HEALTH-CENTER"},
        ],
        "room_flags": [
            {"room": "CHURCH-STREET-PARK", "set": ["OUTSIDEBIT", "PARKBIT"]}
        ],
        "interrupts_queue": [
            {"id": "i_sunrise_sunset", "ticks": -1},
            {"id": "i_city_noises", "ticks": 2},
            {"id": "i_curfew", "ticks": -1},
        ],
    },
    "2061": {
        "start_room": "SOUTHWAY-AND-RIVER",
        "state_overrides": {"credit": 200},
        "objects": [
            {"id": "WALLET", "location": "PLAYER"},
            {"id": "CREDIT-CARD", "location": "WALLET"},
            {"id": "DRIVERS-LICENSE", "location": "WALLET"},
            {"id": "KEY", "location": "PLAYER"},
            {"id": "PARTITION", "location": "LIVING-ROOM"},
            {"id": "PAMPHLET", "location": "TRAIN-STATION"},
            {"id": "FIRETRUCK", "location": "FIREHOUSE"},
            {"id": "ANDERSON-DIRECTORY", "location": "HEALTH-CENTER"},
        ],
        "room_flags": [
            {"room": "WAREHOUSE-1", "set": ["OUTSIDEBIT"]}
        ],
        "interrupts_queue": [
            {"id": "i_sunrise_sunset", "ticks": -1},
            {"id": "i_city_noises", "ticks": 2},
            {"id": "i_curfew", "ticks": -1},
            {"id": "i_apartment", "ticks": 40},
        ],
    },
    "2071": {
        "start_room": "BODANSKI-SQUARE",
        "state_overrides": {"credit": 100},
        "objects": [
            {"id": "WALLET", "location": "PLAYER"},
            {"id": "CREDIT-CARD", "location": "WALLET"},
            {"id": "RATION-CARD", "location": "WALLET"},
            {"id": "KEY", "location": "PLAYER"},
            {"id": "PAMPHLET", "location": "TRAIN-STATION"},
            {"id": "JOYBOOTH-BUTTON", "location": "JOYBOOTH"},
            {"id": "ROY", "location": "ELM-UNDERPASS"},
            {"id": "BANNED-TITLES-LIST", "location": "MAIN-LIBRARY"},
            {"id": "BANNER", "location": "ZOO"},
            {"id": "STONES", "location": "ATHLETIC-FIELD"},
        ],
        "room_flags": [
            {"room": "WAREHOUSE-1", "set": ["OUTSIDEBIT"]},
            {"room": "ST-MICHAELS", "set": ["OUTSIDEBIT"]},
            {"room": "FIRST-METHODIST-CHURCH", "set": ["OUTSIDEBIT"]},
        ],
        "interrupts_queue": [
            {"id": "i_sunrise_sunset", "ticks": -1},
            {"id": "i_city_noises", "ticks": 2},
            {"id": "i_curfew", "ticks": -1},
            {"id": "i_apartment", "ticks": 40},
            {"id": "i_mug", "ticks": 7},
        ],
    },
    "2081": {
        "start_room": "MAIN-AND-WICKER",
        "state_overrides": {"credit": 0},
        "objects": [
            {"id": "SACK", "location": "MAIN-STREET-BRIDGE"},
            {"id": "MOLD", "location": "FOODVILLE-2"},
            {"id": "TIMBERS", "location": "THE-COACHMAN"},
        ],
        "room_flags": [],
        "interrupts_queue": [
            {"id": "i_sunrise_sunset", "ticks": -1},
            {"id": "i_city_noises", "ticks": 2},
            {"id": "i_hunger", "ticks": 65},
            {"id": "i_wild_dogs", "ticks": -1},
        ],
    },
    "2091": {
        "start_room": "SOLARIUM",
        "state_overrides": {},
        "objects": [
            {"id": "JILL", "location": "MASTER-BEDROOM"},
            {"id": "NEWSPAPER", "location": "EPILOGUE-LIVING-ROOM"},
            {"id": "REFRIGERATOR", "location": "EPILOGUE-KITCHEN"},
            {"id": "APARTMENT-DOOR", "location": "FOYER"},
            {"id": "BED", "location": "MASTER-BEDROOM"},
            {"id": "CHAIR", "location": "DINING-ROOM"},
            {"id": "COUNTER", "location": "EPILOGUE-KITCHEN"},
            {"id": "TOILET", "location": "EPILOGUE-BATHROOM"},
        ],
        "room_flags": [],
        "interrupts_queue": [
            {"id": "i_skycab", "ticks": 18},
        ],
        "note": "Epilogue. Triggered by PART-FLAG=4, not player-selectable.",
    },
}


# ---------------------------------------------------------------------------
# Part C: Parse score_trigger_extraction.md
# ---------------------------------------------------------------------------

TRIGGER_NORMALIZE = {
    "room_enter": "room_enter",
    "object_examine": "object_examine",
    "object_read": "object_read",
    "event": "event",
    "death": "death",
    "room_enter/object": "room_enter",
    "object/room_enter": "room_enter",
    "event/object": "event",
    "object/event": "event",
    "event/death": "event",
    "death/event": "event",
}


def extract_room_from_routine(routine: str):
    """
    Attempt to extract a room ID from a routine name ending in -F or -ENTER-F.
    Returns (room_id, True) on success or (None, False) on failure.
    """
    # Strip -ENTER-F first (longer suffix takes priority)
    for suffix in ("-ENTER-F", "-DESC-F", "-DESCFCN", "-DESCF", "-DESC", "-F"):
        if routine.upper().endswith(suffix):
            candidate = routine[: len(routine) - len(suffix)]
            # Plausibility check: all caps (or uppercase + hyphens/underscores)
            if re.match(r"^[A-Z][A-Z0-9\-_]+$", candidate):
                return candidate, True
            break
    return None, False


def parse_years(years_str: str):
    """Parse years column into sorted list of ints."""
    years = []
    for part in re.split(r"[,\s]+", years_str.strip()):
        part = part.strip()
        if re.match(r"^\d{4}$", part):
            years.append(int(part))
    return sorted(set(years))


def parse_scores(filepath: str) -> list:
    """Parse score_trigger_extraction.md and return scores list."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    primary = {}   # index -> entry dict
    seen_order = []  # maintain insertion order

    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        # Skip separator rows
        if line.startswith("|---") or line.startswith("| ---"):
            continue

        cols = [c.strip() for c in line.split("|")]
        cols = [c for c in cols if c != ""]
        if len(cols) < 7:
            continue

        # First column must be a digit to be a score row (not header)
        if not cols[0][:1].isdigit():
            continue

        try:
            idx = int(cols[0])
        except ValueError:
            print(f"WARNING: Could not parse score index '{cols[0]}', skipping row: {line}")
            continue

        # Filter out year-summary rows (idx >= 2000)
        if idx >= 2000:
            continue

        try:
            pts = int(cols[1])
        except ValueError:
            print(f"WARNING: Could not parse points '{cols[1]}' for index {idx}, skipping.")
            continue

        desc = cols[2]
        trigger_raw = cols[3].strip().lower()
        routine = cols[4].strip()
        years_raw = cols[5]
        source = cols[6] if len(cols) > 6 else ""

        trigger = TRIGGER_NORMALIZE.get(trigger_raw, "event")

        years = parse_years(years_raw)

        if idx in primary:
            # Deduplication: add to alt_routines
            existing = primary[idx]
            if routine != existing.get("source_routine", ""):
                if "alt_routines" not in existing:
                    existing["alt_routines"] = []
                existing["alt_routines"].append(routine)
        else:
            entry = {
                "index": idx,
                "points": pts,
                "desc": desc,
                "trigger": trigger,
                "years": years,
                "source_routine": routine,
            }

            if trigger == "room_enter":
                room_id, derived = extract_room_from_routine(routine)
                if derived and room_id:
                    entry["rooms"] = [room_id]
                    entry["rooms_unverified"] = True
                else:
                    entry["rooms"] = None
            elif trigger in ("object_examine", "object_read"):
                # Derive object from routine: strip trailing -F
                obj_candidate = routine
                for suffix in ("-ENTER-F", "-DESC-F", "-F"):
                    if obj_candidate.upper().endswith(suffix):
                        obj_candidate = obj_candidate[: len(obj_candidate) - len(suffix)]
                        break
                entry["object"] = obj_candidate
            elif trigger == "event":
                # Derive interrupt id: lowercase, hyphens -> underscores
                entry["interrupt"] = routine.lower().replace("-", "_")
            elif trigger == "death":
                # Death entries: derive interrupt if routine starts with I-
                if routine.upper().startswith("I-"):
                    entry["interrupt"] = routine.lower().replace("-", "_")

            primary[idx] = entry
            seen_order.append(idx)

    # Build output list in insertion order
    return [primary[i] for i in seen_order]


# ---------------------------------------------------------------------------
# Part D: Stub sections (hardcoded)
# ---------------------------------------------------------------------------

INTERRUPTS_STUB = {
    "_note": (
        "Populated in Sessions 14-15. "
        "See simulation_tree_schema.md Section 3 for schema."
    )
}

DESCRIPTIONS_STUB = {
    "rooms": {
        "_note": (
            "Populated in Sessions 14-16. "
            "See simulation_tree_schema.md Section 5 for schema."
        )
    },
    "objects": {
        "_note": (
            "Populated in Sessions 15-17. "
            "See simulation_tree_schema.md Section 5 for schema."
        )
    },
}

FACILITY_STUB = {
    "chapters": {
        "1": {
            "title": "Part One: The Awakening of PRISM",
            "trigger": "game_start",
        },
        "2": {
            "title": "Part Two: Simulations",
            "trigger": {"flag": {"name": "completed_tasks", "eq": True}},
        },
        "3": {
            "title": "Part Three: The Plan Goes Into Effect",
            "trigger": "handler:check_plan_adoption",
        },
        "4": {
            "title": "Epilogue",
            "trigger": "handler:check_epilogue",
        },
    },
    "recording_tasks": [
        {"index": 0, "desc": "Eating a meal in a restaurant"},
        {"index": 1, "desc": "Talking to a government official"},
        {"index": 2, "desc": "Visiting a power-generating facility"},
        {"index": 3, "desc": "Reading a newspaper"},
        {"index": 4, "desc": "Riding some form of public transportation"},
        {"index": 5, "desc": "Attending a court in session"},
        {"index": 6, "desc": "Talking to a church official"},
        {"index": 7, "desc": "Going to a movie"},
        {"index": 8, "desc": "Visiting your own home or living quarters"},
    ],
    "sim_unlock_thresholds": {
        "2051": {"requires": "completed_tasks"},
        "2061": {"requires": {"sim_level_table_1": {"gt": 300}}},
        "2071": {"requires": {"sim_level_table_2": {"gt": 400}}},
        "2081": {"requires": {"sim_level_table_3": {"gt": 600}}},
        "2091": {"requires": {"part_flag": {"eq": 4}}},
    },
    "security_code": {
        "colors_table": [
            "WHITE", "DARK GREEN", "DARK BLUE", "PINK", "ORANGE", "PURPLE",
            "TAN", "AQUA", "LIGHT BLUE", "LIGHT GREEN", "LIGHT GRAY", "YELLOW",
            "BLACK", "DARK GRAY", "BROWN", "RED",
        ],
        "inner_numbers": [
            89, 61, 50, 18, 29, 82, 46, 77, 27, 68, 22, 95, 40, 58, 15, 86,
            28, 33, 94, 11, 64, 98, 34, 49, 60, 16, 85, 52, 37, 53, 93, 91,
        ],
        "outer_numbers": [
            12, 66, 73, 36, 90, 41, 19, 48, 62, 92, 55, 23, 84, 99, 57, 20,
            78, 67, 51, 88, 17, 31, 70, 39, 96, 25, 81, 83, 47, 54, 13, 43,
        ],
        "note": (
            "Color index * 2 + inner_index = outer_table_index (mod 32). "
            "Player enters outer_numbers[offset] given color and inner number."
        ),
    },
    "messages": {"_note": "Message schedule extracted in Session 14."},
    "endgame": {"_note": "Endgame sequence details extracted in Session 14."},
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_state_defs(state_defs: dict):
    count = len(state_defs)
    print(f"state_defs count: {count}")
    if count < 70 or count > 120:
        print(f"WARNING: state_defs count {count} is outside expected range (70-120).")

    valid_scopes = {"facility", "simulation", "global"}
    for name, entry in state_defs.items():
        for field in ("type", "init", "scope", "category"):
            if field not in entry:
                print(f"WARNING: state_def '{name}' missing field '{field}'.")
        if entry.get("scope") not in valid_scopes:
            print(f"WARNING: state_def '{name}' has invalid scope '{entry.get('scope')}'.")


def validate_scores(scores: list):
    count = len(scores)
    print(f"scores count: {count}")
    if count != 137:
        print(f"WARNING: Expected exactly 137 score entries, got {count}.")

    indices = [e["index"] for e in scores]
    seen = set()
    for idx in indices:
        if idx in seen:
            print(f"WARNING: Duplicate score index {idx} in output.")
        seen.add(idx)

    if 22 in seen:
        print("WARNING: Index 22 (empty slot) is present in scores - should be absent.")

    null_rooms = sum(
        1 for e in scores
        if e.get("trigger") == "room_enter" and e.get("rooms") is None
    )
    print(f"scores with null rooms: {null_rooms} (flagged for manual review)")

    for entry in scores:
        for field in ("index", "points", "desc", "trigger", "years", "source_routine"):
            if field not in entry:
                print(f"WARNING: score index {entry.get('index')} missing field '{field}'.")


def validate_year_init(year_init: dict):
    expected_keys = {"2041", "2051", "2061", "2071", "2081", "2091"}
    actual_keys = set(year_init.keys())
    if actual_keys != expected_keys:
        print(f"WARNING: year_init keys mismatch. Expected {expected_keys}, got {actual_keys}.")

    objs_2071 = year_init.get("2071", {}).get("objects", [])
    if len(objs_2071) != 10:
        print(f"WARNING: year_init['2071'].objects has {len(objs_2071)} entries, expected 10.")

    objs_2081 = year_init.get("2081", {}).get("objects", [])
    if len(objs_2081) != 3:
        print(f"WARNING: year_init['2081'].objects has {len(objs_2081)} entries, expected 3.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    state_inv_path = os.path.join(INPUT_DIR, "simulation_state_inventory.md")
    score_path = os.path.join(INPUT_DIR, "score_trigger_extraction.md")

    if not os.path.exists(state_inv_path):
        print(f"ERROR: Input file not found: {state_inv_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(score_path):
        print(f"ERROR: Input file not found: {score_path}", file=sys.stderr)
        sys.exit(1)

    print("Parsing simulation_state_inventory.md ...")
    state_defs = parse_state_defs(state_inv_path)
    validate_state_defs(state_defs)

    print("Building year_init ...")
    year_init = YEAR_INIT
    validate_year_init(year_init)

    print("Parsing score_trigger_extraction.md ...")
    scores = parse_scores(score_path)
    validate_scores(scores)

    output_dir = os.path.dirname(OUTPUT_PATH)
    os.makedirs(output_dir, exist_ok=True)

    tree = {
        "state_defs": state_defs,
        "year_init": year_init,
        "interrupts": INTERRUPTS_STUB,
        "scores": scores,
        "descriptions": DESCRIPTIONS_STUB,
        "facility": FACILITY_STUB,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, sort_keys=False)

    print(f"\nOutput written to: {OUTPUT_PATH}")
    print("\n=== Summary ===")
    print(f"  state_defs count : {len(state_defs)}")
    print(f"  year_init keys   : {len(year_init)} ({', '.join(sorted(year_init.keys()))})")
    print(f"  scores count     : {len(scores)}")
    null_rooms = sum(
        1 for e in scores
        if e.get("trigger") == "room_enter" and e.get("rooms") is None
    )
    print(f"  null rooms scores: {null_rooms}")


if __name__ == "__main__":
    main()
