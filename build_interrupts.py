#!/usr/bin/env python3
"""Session 15: Populate interrupts section of simulation_tree.json."""

import json
import sys

INPUT_PATH = "simulation_tree.json"
OUTPUT_PATH = "simulation_tree.json"


def build_interrupts():
    """Return the complete interrupts dict."""
    return {

        # ── Category 1: NPC Schedules ──────────────────────────────────────────

        "i_jill": {
            "mode": "tick",
            "context": "simulation",
            "years": [2041, 2051, 2061],
            "initial_ticks": -1,
            "repeat": True,
            "handler": "jill_schedule",
            "handler_data": {
                "schedule_2041_2051": [
                    {"counter": 0,  "stime": 478,  "room": "BEDROOM",     "activity": "Wakes up, begins dressing"},
                    {"counter": 1,  "stime": 522,  "room": "BEDROOM",     "activity": "Dressing, neatening room"},
                    {"counter": 2,  "stime": 591,  "room": "KITCHEN",     "activity": "Making salad"},
                    {"counter": 3,  "stime": 644,  "room": "LIVING-ROOM", "activity": "Reading"},
                    {"counter": 4,  "stime": 697,  "room": "LIVING-ROOM", "activity": "Painting at easel"},
                    {"counter": 5,  "stime": 813,  "room": "KITCHEN",     "activity": "Eating salad"},
                    {"counter": 6,  "stime": 859,  "room": "KITCHEN",     "activity": "Washing dishes"},
                    {"counter": 7,  "stime": 912,  "room": "LIVING-ROOM", "activity": "Painting again"},
                    {"counter": 8,  "stime": 1084, "room": "LIVING-ROOM", "activity": "Cleaning up"},
                    {"counter": 9,  "stime": 1137, "room": "LIVING-ROOM", "activity": "Reading on couch"},
                    {"counter": 10, "stime": 1242, "room": "BATHROOM",    "activity": "Wetting hair"},
                    {"counter": 11, "stime": 1299, "room": "BEDROOM",     "activity": "Reading in bed"},
                    {"counter": 12, "stime": 1402, "room": "BEDROOM",     "activity": "Falls asleep"}
                ],
                "counter_13": "Post-raid crying state (set by I-APARTMENT)",
                "counter_14": "Post-raid cleanup (re-queued from I-APARTMENT at 28 ticks)",
                "year_2061_behavior": "One-time event. Jill enters upset about Mitchell joining Church of God's Word. Scores index 119 (4 pts). Moves Jill to BEDROOM.",
                "_todo": "Full narrative text per counter step needs extraction from interrupts_zil.txt lines 248-547"
            },
            "state_variables": ["jill_counter", "jill_not_spoken_yet", "mitchell_news_flag", "follow_flag"],
            "objects_moved": ["JILL", "JILL-BOOK", "SALAD", "REFRIGERATOR"],
            "note": "Queued by LIVING-ROOM-F when player enters apartment. Disables when player leaves apartment."
        },

        "i_mitchell": {
            "mode": "tick",
            "context": "simulation",
            "years": [2041, 2051],
            "initial_ticks": -1,
            "repeat": True,
            "handler": "mitchell_schedule",
            "handler_data": {
                "schedule": [
                    {"counter": 0, "stime": 463,  "room": "LIVING-ROOM", "activity": "Getting ready for school"},
                    {"counter": 1, "stime": 505,  "room": None,          "activity": "Goes to school (leaves)"},
                    {"counter": 2, "stime": 1011, "room": "LIVING-ROOM", "activity": "Comes home, plays logic game"},
                    {"counter": 3, "stime": 1120, "room": "LIVING-ROOM", "activity": "Does homework"},
                    {"counter": 4, "stime": 1374, "room": None,          "activity": "Goes to bed (behind partition)"}
                ],
                "_todo": "Dialogue text per transition needs extraction from interrupts_zil.txt lines 553-645"
            },
            "state_variables": ["mitchell_counter"],
            "objects_moved": ["MITCHELL", "HOMEWORK", "LOGIC-GAME"],
            "note": "Queued by apartment enter logic. Disables when player leaves apartment."
        },

        "i_mitchell_raid": {
            "mode": "tick",
            "context": "simulation",
            "years": [2071],
            "initial_ticks": 19,
            "repeat": False,
            "effects": [
                {"action": "score",        "index": 120},
                {"action": "move_player",  "target": "LIVING-ROOM"},
                {"action": "message",      "text": "Mitchell returns with Church police. Jill is identified as a heretic and dragged away screaming. You are beaten."},
                {"action": "set_state",    "key": "mitchell_raid_flag", "value": True},
                {"action": "set_state",    "key": "bruised",            "value": True},
                {"action": "remove_object","id": "JILL"},
                {"action": "set_state",    "key": "apartment_door_openbit", "value": False},
                {"action": "queue_interrupt", "id": "i_apartment", "ticks": -1}
            ],
            "note": "Queued by LIVING-ROOM-F on first apartment visit in 2071. Most emotionally devastating scene in the game."
        },

        # ── Category 2: Law Enforcement ───────────────────────────────────────

        "i_curfew": {
            "mode": "tick",
            "context": "simulation",
            "years": [2051, 2061, 2071],
            "initial_ticks": -1,
            "repeat": True,
            "handler": "curfew_handler",
            "handler_data": {
                "curfew_hours": {"start": 1260, "end": 420},
                "arrest_probability": 8,
                "year_2071_death": True,
                "jail_release_ticks": 100,
                "release_room": "ELM-AND-PARK",
                "arrest_score": 116,
                "death_score": 117,
                "requires_streetbit": True,
                "_todo": "Arrest/release/death narrative text needs extraction from interrupts_zil.txt lines 727-776"
            },
            "state_variables": ["light_level", "jailed"],
            "note": "Checks each turn. Jail is embedded in this handler (no separate i_jail interrupt). 2071: 8% chance of death instead of arrest."
        },

        "i_apartment": {
            "mode": "tick",
            "context": "simulation",
            "years": [2051, 2061, 2071],
            "initial_ticks": -1,
            "repeat": False,
            "handler": "apartment_raid",
            "handler_data": {
                "raid_prob_increment": 6,
                "nighttime_range": {"start": 1320, "end": 480},
                "requires_in_apartment": True,
                "year_variants": {
                    "2051": "BSF officers search apartment with Rad-Detectors",
                    "2061": "BSF officers confiscate books, vandalize apartment",
                    "2071": "BSF officers conduct violent search, beat player if bruised flag set"
                },
                "_todo": "Full raid narrative text per year needs extraction from interrupts_zil.txt lines 646-726"
            },
            "state_variables": ["apartment_raid_flag", "raid_prob", "bruised"],
            "note": "Queued in year_init for 2061 (ticks: 40). Queued by LIVING-ROOM-F for 2051/2071. RAID-PROB starts at 0, increases by 6 per non-raid turn."
        },

        # ── Category 3: Environmental Dangers ─────────────────────────────────

        "i_mug": {
            "mode": "tick",
            "context": "simulation",
            "years": [2071],
            "initial_ticks": 7,
            "repeat": 7,
            "effects": [
                {"action": "message",   "text": "A gang of toughs jumps you from behind!"},
                {"action": "set_state", "key": "mugged",  "value": True},
                {"action": "set_state", "key": "credit",  "value": 0},
                {"action": "score",     "index": 100}
            ],
            "conditions": ["light_level == 0", "player_outdoors"],
            "note": "Only fires at night and outdoors. Engine pre-check on conditions."
        },

        "i_hunger": {
            "mode": "tick",
            "context": "simulation",
            "years": [2081],
            "initial_ticks": 65,
            "repeat": False,
            "effects": [
                {"action": "damage", "type": "starving", "message": "You are so hungry that you can barely move."},
                {"action": "score",  "index": 40}
            ]
        },

        "i_wild_dogs": {
            "mode": "tick",
            "context": "simulation",
            "years": [2081],
            "initial_ticks": -1,
            "repeat": True,
            "handler": "wild_dogs_handler",
            "handler_data": {
                "probability": 10,
                "requires_outdoors": True,
                "death_score": 41,
                "_todo": "Death narrative text needs extraction from interrupts_zil.txt"
            },
            "note": "Each outdoor turn: 10% chance of fatal wild dog attack."
        },

        "i_stoning": {
            "mode": "tick",
            "context": "simulation",
            "years": [2071],
            "initial_ticks": -1,
            "repeat": False,
            "handler": "stoning_handler",
            "handler_data": {
                "trigger_room": "ATHLETIC-FIELD",
                "score_index": 121,
                "_todo": "Narrative text needs extraction from interrupts_zil.txt"
            },
            "note": "Triggers when player is in ATHLETIC-FIELD in 2071. One-time event: religious stoning of a woman."
        },

        # ── Category 4: Ambient/Environmental ─────────────────────────────────

        "i_sunrise_sunset": {
            "mode": "condition",
            "context": "simulation",
            "years": None,
            "check_on": ["time_advance"],
            "handler": "sunrise_sunset",
            "handler_data": {
                "base_thresholds": [
                    {"stime": 300,  "level": 1, "message": "The first glow of dawn appears on the horizon."},
                    {"stime": 360,  "level": 2, "message": "The sun peeks above the rooftops."},
                    {"stime": 420,  "level": 3, "message": "Day has begun."},
                    {"stime": 1080, "level": 2, "message": "The sky begins to darken as evening approaches."},
                    {"stime": 1140, "level": 1, "message": "The last glow of sunset fades from the sky."},
                    {"stime": 1200, "level": 0, "message": "Night has fallen."}
                ],
                "month_offsets": {"1": -60, "2": -30, "3": 0, "4": 30, "5": 60, "6": 60},
                "note": "Month offsets shift dawn/dusk times. Can be omitted if simplified to fixed season."
            }
        },

        "i_city_noises": {
            "mode": "tick",
            "context": "simulation",
            "years": None,
            "initial_ticks": 2,
            "repeat": 2,
            "handler": "city_noises",
            "handler_data": {
                "requires_outdoors": True,
                "noise_pool_day": "traffic sounds, distant voices, skycar overhead",
                "noise_pool_night": "distant siren, wind, footsteps",
                "_todo": "Full noise text pool needs extraction from interrupts_zil.txt"
            },
            "note": "Ambient flavor text every 2 ticks when outdoors."
        },

        "i_beggar": {
            "mode": "tick",
            "context": "simulation",
            "years": [2061, 2071, 2081],
            "initial_ticks": -1,
            "repeat": False,
            "handler": "beggar_handler",
            "handler_data": {
                "probability": 5,
                "requires_outdoors": True,
                "score_index": 101,
                "_todo": "Beggar narrative text needs extraction from interrupts_zil.txt"
            },
            "note": "Random beggar encounter. One-time per simulation session."
        },

        # ── Category 5: Interactive Sequences ─────────────────────────────────

        "i_restaurant": {
            "mode": "tick",
            "context": "simulation",
            "years": [2041, 2051, 2061],
            "initial_ticks": -1,
            "repeat": True,
            "handler": "restaurant_handler",
            "handler_data": {
                "rooms": ["RESTAURANT", "SIMONS"],
                "stages": ["seated", "ordered", "eating", "finished"],
                "score_indices": [102, 103],
                "_todo": "Full restaurant sequence text and year variants need extraction"
            },
            "note": "Handles restaurant dining sequence. Recording task: eating a meal."
        },

        "i_movie": {
            "mode": "tick",
            "context": "simulation",
            "years": [2041, 2051],
            "initial_ticks": 8,
            "repeat": False,
            "effects": [
                {"action": "message",   "text": "The lights dim and the movie begins..."},
                {"action": "set_state", "key": "movie_playing", "value": True},
                {"action": "score",     "index": 108}
            ],
            "note": "Queued when player enters CINEMA. Score: going to a movie (recording task)."
        },

        "i_church": {
            "mode": "tick",
            "context": "simulation",
            "years": [2041, 2051, 2061, 2071],
            "initial_ticks": -1,
            "repeat": True,
            "handler": "church_handler",
            "handler_data": {
                "rooms": ["CHURCH"],
                "year_variants": {
                    "2041": "Standard church service",
                    "2051": "Church service with political undertones",
                    "2061": "Church of God's Word service, more extreme",
                    "2071": "Church of God's Word, overtly authoritarian"
                },
                "score_index": 107,
                "_todo": "Church sequence text and year variants need extraction"
            },
            "note": "Recording task: talking to a church official."
        },

        # ── Category 6: Facility Progression ──────────────────────────────────

        "i_grimwold": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": -1,
            "repeat": True,
            "handler": "grimwold_rorschach",
            "handler_data": {
                "stages": 10,
                "requires_player_in": "OFFICE",
                "blocks_simulation_entry": True,
                "_todo": "Rorschach test words and Grimwold dialogue need extraction from prism_zil.txt"
            },
            "state_variables": ["grimwold_counter", "psych_test_active"],
            "note": "Dr. Grimwold Rorschach test. Blocks simulation mode entry until complete. Port design decision needed: text input vs button responses."
        },

        "i_first_simulation_result": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 7,
            "repeat": False,
            "handler": "first_sim_result",
            "handler_data": {
                "recording_task_count": 9,
                "on_all_complete": {
                    "set_completed_tasks": True,
                    "set_part_flag": 2,
                    "chapter_print": 2,
                    "queue": [
                        {"id": "i_message_x", "ticks": 12},
                        {"id": "i_message_q", "ticks": 77}
                    ],
                    "advance_time": 680
                },
                "on_8_of_9": "Perelman asks to redo the one missing task",
                "on_fewer": "Perelman is unhappy, lists missing tasks"
            },
            "state_variables": ["completed_tasks", "part_flag", "message_e_counter"],
            "note": "Queued by I-MESSAGE-E or BUFFER-RESULT. Evaluates recording completion."
        },

        "i_view": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": "variable",
            "repeat": False,
            "effects": [
                {"action": "queue_interrupt", "id": "i_recordings_viewed", "ticks": 6},
                {"action": "queue_interrupt", "id": "i_message_e",         "ticks": 14},
                {"action": "message", "text": "Several of us have just finished viewing the recordings."}
            ],
            "note": "Queued by BUFFER-RESULT when player submits recordings. Ticks = RECORD-BUFFER size + 5."
        },

        "i_recordings_viewed": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 6,
            "repeat": False,
            "handler": "recordings_viewed_evaluator",
            "handler_data": {
                "year_thresholds": {
                    "2051": {"minimum": 10, "half": 5},
                    "2061": {"minimum": 20, "half": 10},
                    "2071": {"minimum": 40, "half": 20},
                    "2081": {"minimum": 14, "half": 7}
                },
                "on_all_pass": {
                    "set_part_flag": 3,
                    "chapter_print": 3,
                    "queue": [
                        {"id": "i_message_z",        "ticks": 14},
                        {"id": "i_perelman_returns", "ticks": 22},
                        {"id": "i_siege",            "ticks": 73},
                        {"id": "i_ryder",            "ticks": 116},
                        {"id": "i_sabotage",         "ticks": 175},
                        {"id": "i_lose",             "ticks": 588}
                    ]
                },
                "on_partial": "Perelman gives per-year feedback on which passed/failed"
            },
            "state_variables": ["part_flag"],
            "note": "Critical win-condition evaluator. Queued by I-VIEW. Triggers endgame chain if all four years meet minimum observation scores."
        },

        "i_perelman": {
            "mode": "condition",
            "context": "facility",
            "check_on": ["time_advance"],
            "handler": "perelman_schedule",
            "handler_data": {
                "disable_conditions": ["part_flag > 2", "reviewing_recordings == true"],
                "events": [
                    {
                        "stime": 536,
                        "clock": "8:56am",
                        "visible_room": "CONTROL-CENTER",
                        "event_key": "morning_arrival",
                        "text_if_visible": "Doctor Perelman walks jauntily into the Control Center. \"Good morning to all,\" he calls cheerily and begins chatting with the chief of the night shift."
                    },
                    {
                        "stime": 550,
                        "clock": "9:10am",
                        "visible_room": "CONTROL-CENTER",
                        "event_key": "nightshift_departs",
                        "text_if_visible": "Perelman stops talking to the technician, who hangs up his white overcoat and leaves the control room. Perelman crosses the room and picks up a thick report.",
                        "text_alt": "Perelman enters, looks around, and picks up a thick report."
                    },
                    {
                        "stime": 599,
                        "clock": "9:59am",
                        "visible_room": "CONTROL-CENTER",
                        "event_key": "leaves_for_office",
                        "text_if_visible": "Perelman puts down the report and walks toward the door. He calls to one of the technicians. \"Nat, I'll be in my office.\""
                    },
                    {
                        "stime": 616,
                        "clock": "10:16am",
                        "visible_room": "OFFICE",
                        "event_key": "coffee_morning",
                        "text_if_visible": "Doctor Perelman walks into the office carrying a cup of coffee. He sits down at his desk, places the coffee mug almost out of sight below your monitor, and begins working."
                    },
                    {
                        "stime": 711,
                        "clock": "11:51am",
                        "visible_room": "OFFICE",
                        "event_key": "lunch_phone_call",
                        "text_if_visible": "The telephone buzzes. \"Perelman,\" says Perelman into the receiver. The voice at the other end is so quiet that even your sensitive audio monitors can't pick it up. \"Hi, Aseejh.\" Pause. \"Yes, let's get together on that.\" He glances up at his terminal. \"It's almost lunch time; want to meet me in the cafeteria?\" Pause. \"Okay, ten minutes.\" Perelman replaces the receiver and leaves the room."
                    },
                    {
                        "stime": 790,
                        "clock": "1:10pm",
                        "visible_room": "OFFICE",
                        "event_key": "coffee_afternoon",
                        "text_if_visible": "Doctor Perelman walks into the office carrying a cup of coffee. He sits down at his desk, places the coffee mug almost out of sight below your monitor, and begins working."
                    },
                    {
                        "stime": 834,
                        "clock": "1:54pm",
                        "visible_room": "OFFICE",
                        "event_key": "price_meeting",
                        "text_if_visible": "Price, Doctor Perelman's secretary, appears in the doorway. \"Doc, don't forget, you've got a meeting with Vera at two o'clock.\" He glances at his watch, mumbles some impolite things under his breath, and rushes out."
                    },
                    {
                        "stime": 980,
                        "clock": "4:20pm",
                        "visible_room": "OFFICE",
                        "event_key": "returns_messages",
                        "text_if_visible": "Doctor Perelman walks into the office, carrying a pile of pink message slips. He scans them, drops all but one into a basket on his desk, picks up the phone receiver, and presses two or three buttons. Your sensitive audio pickup hears a few rings, a click, and then a young woman's voice: \"This is Esther. Can't come to the phone now. Please leave a message, though.\" Pause. \"BEEP!\" Perelman speaks into the phone. \"Hi, it's Dad. I got your message, but I can't make it; I'm too tied up with the Project. I'll probably be in the office all evening if you want to talk.\""
                    },
                    {
                        "stime": 1157,
                        "clock": "7:17pm",
                        "visible_room": "OFFICE",
                        "event_key": "price_goodnight",
                        "text_if_visible_and_present": "Price, Perelman's secretary, pops her head in the doorway. \"Hey Doc! Need me for anything else tonight?\" Perelman, grinning, responds, \"Not unless you've decided to dump that unfairly handsome husband of yours.\" She looks exasperated at what is obviously an old joke and shakes a fist at him in a mock threat. \"Really, though, I'll be fine,\" says Perelman. \"Scram.\" She disappears from sight, shouting from the next room, \"Good night, Doc. Don't stay too late!\"",
                        "text_if_visible_not_present": "Perelman enters with his secretary, Price, who asks, \"Need me for anything else tonight?\" Perelman, grinning, responds, \"Not unless you've decided to dump that unfairly handsome husband of yours.\" She looks exasperated at what is obviously an old joke and shakes a fist at him in a mock threat. \"Really, though, I'll be fine,\" says Perelman. \"Scram.\" She disappears from sight, shouting from the next room, \"Good night, Doc. Don't stay too late!\""
                    },
                    {
                        "stime": 1241,
                        "clock": "8:41pm",
                        "visible_room": "OFFICE",
                        "event_key": "leaves_evening",
                        "text_if_visible": "Perelman shoves some papers into a notebook, types something on his desk terminal, and leaves the room."
                    },
                    {
                        "stime": 1281,
                        "clock": "9:21pm",
                        "visible_room": "CONTROL-CENTER",
                        "event_key": "evening_cc",
                        "text_if_visible": "Doctor Perelman walks into the Control Center. He wanders around the room, talking quietly with a few technicians. He picks up a hefty printout from the printer and settles into a swivel chair to read it."
                    },
                    {
                        "stime": 1312,
                        "clock": "9:52pm",
                        "visible_room": "CONTROL-CENTER",
                        "event_key": "going_home",
                        "text_if_visible": "Perelman puts down the printout and rubs his eyes. He stands and unsuccessfully stifles a yawn. \"I'm going home,\" he announces to the tiny evening staff.",
                        "random_addition": {"probability": 50, "text": " Try not to call me unless it's an emergency"}
                    },
                    {
                        "stime": 1318,
                        "clock": "9:58pm",
                        "visible_room": "OFFICE",
                        "event_key": "goodnight_salute",
                        "text_if_visible": "Doctor Perelman walks wearily into the office, puts on a thin overcoat, and grabs a notebook stuffed with papers. He stops at the doorway, glancing about the room, and spots the active light on your communication unit. A smile breaks through the weary lines on his face. He raises his hand to his forehead in a friendly salute. \"Good night, PRISM.\" He dims the light and closes the office door. The sensors on your monitor automatically adjust to the lower light level."
                    }
                ],
                "position_table": [
                    {"time_min": 0,    "time_max": 535,  "location": None,              "has_coffee": False, "ldesc": None},
                    {"time_min": 536,  "time_max": 549,  "location": "CONTROL-CENTER",  "has_coffee": False, "ldesc": "Doctor Perelman is at the far end of the room, speaking to the head technician of the night shift."},
                    {"time_min": 550,  "time_max": 598,  "location": "CONTROL-CENTER",  "has_coffee": False, "ldesc": "Doctor Perelman is here, reading a report."},
                    {"time_min": 599,  "time_max": 615,  "location": None,              "has_coffee": False, "ldesc": None},
                    {"time_min": 616,  "time_max": 710,  "location": "OFFICE",          "has_coffee": True,  "ldesc": "Doctor Perelman is sitting at his desk, reading through stacks of papers and occasionally typing on his desk terminal."},
                    {"time_min": 711,  "time_max": 789,  "location": None,              "has_coffee": False, "ldesc": None},
                    {"time_min": 790,  "time_max": 833,  "location": "OFFICE",          "has_coffee": True,  "ldesc": "Doctor Perelman is sitting at his desk, reading through stacks of papers and occasionally typing on his desk terminal."},
                    {"time_min": 834,  "time_max": 979,  "location": None,              "has_coffee": False, "ldesc": None},
                    {"time_min": 980,  "time_max": 1240, "location": "OFFICE",          "has_coffee": False, "ldesc": "Doctor Perelman is sitting at his desk, reading through stacks of papers and occasionally typing on his desk terminal."},
                    {"time_min": 1241, "time_max": 1280, "location": None,              "has_coffee": False, "ldesc": None},
                    {"time_min": 1281, "time_max": 1311, "location": "CONTROL-CENTER",  "has_coffee": False, "ldesc": "Doctor Perelman is sitting in a swivel chair, reading a long printout."},
                    {"time_min": 1312, "time_max": 1439, "location": None,              "has_coffee": False, "ldesc": None}
                ]
            },
            "state_variables": ["last_abe_time"],
            "note": "Largest facility interrupt. 13 narrative events + 12 position slots. No day-specific branching in this routine; day variance comes from other interrupts (messages, sim results) that disable/re-queue I-PERELMAN."
        },

        # ── Category 7: Facility Endgame Chain ────────────────────────────────

        "i_perelman_returns": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 22,
            "repeat": False,
            "effects": [
                {"action": "message", "text": "PRISM, I'm just back from Washington. I met with the new Plan Authority for several hours. We viewed all the tapes. They rejected the contents outright. They called the recordings fakes. They refused to act on them. Several members even questioned my patriotism, made vague threats. I don't know what to do next. I'm going to meet with some of my colleagues here to discuss things. I'll keep you posted."}
            ],
            "note": "Queued by I-RECORDINGS-VIEWED. Delivers Washington rejection news."
        },

        "i_siege": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 73,
            "repeat": False,
            "effects": [
                {"action": "set_state",    "key": "siege", "value": True},
                {"action": "move_object",  "id": "NATIONAL-GUARDSMAN", "target": "CONTROL-CENTER"},
                {"action": "message",      "text": "Announcement, announcement. All lines, priority interrupt. This is Major General Dirk Peters of the Dakota/Manitoba National Guard Division. A security leak that could threaten our national security has been discovered here at the PRISM Facility. The entire complex has been sealed off; no one will be permitted to enter or leave until further notice."}
            ],
            "note": "Queued when PART-FLAG transitions to 3."
        },

        "i_ryder": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 116,
            "repeat": False,
            "handler": "endgame_ryder",
            "handler_data": {
                "visit_count": 6,
                "visit_interval": 20,
                "location": "OFFICE",
                "stages": [
                    {"step": 1, "desc": "Ryder enters office, introduces himself to Perelman"},
                    {"step": 2, "desc": "Ryder pressures Perelman about recordings"},
                    {"step": 3, "desc": "Confrontation escalates, Ryder questions patriotism"},
                    {"step": 4, "desc": "Ryder makes threats"},
                    {"step": 5, "desc": "Ryder threatens: 'You wouldn't be the first person who's gotten crushed.' Perelman may taunt if he noticed PRISM recording."},
                    {"step": 6, "desc": "Ryder delivers ultimatum: facility locked down, no communications. Leaves with Perelman escorted by guards."}
                ],
                "recording_mechanic": "Each turn player is in OFFICE with recording == true, ryder_recorded increments. Must reach >= 2 for win condition.",
                "player_speaks_penalty": "If player speaks to Ryder, he discovers PRISM is active, drags Perelman away (ends confrontation, loses recording opportunity).",
                "_todo": "Full dialogue text per step needs extraction from prism_zil.txt"
            },
            "state_variables": ["ryder_counter", "ryder_recorded", "perelman_noticed"],
            "note": "Queued 116 ticks into endgame. Win requires recording >= 2 of 6 visits."
        },

        "i_sabotage": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 175,
            "repeat": False,
            "handler": "endgame_sabotage",
            "handler_data": {
                "counter_max": 4,
                "fix_location": "CORE",
                "_todo": "Sabotage progression text and HVAC fix sequence need extraction from prism_zil.txt"
            },
            "state_variables": ["sabotage_counter"],
            "note": "175 ticks after siege. Starts HVAC sabotage (counter 0-4). Player must reach Maintenance Core to stop it."
        },

        "i_open_window": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 26,
            "repeat": False,
            "handler": "open_window_handler",
            "handler_data": {
                "target_room": "CONTROL-CENTER",
                "retry_ticks": 4
            },
            "note": "Queued by HVAC interface interaction. Technician opens window (HVAC foreshadowing). Re-queues at 4 if player not in CC."
        },

        "i_win": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 13,
            "repeat": False,
            "handler": "endgame_win",
            "handler_data": {
                "effects": [
                    {"action": "disable_interrupt", "id": "i_lose"},
                    {"action": "message",           "text": "You've done it! That was brilliant!"},
                    {"action": "set_state",         "key": "part_flag", "value": 4},
                    {"action": "chapter_print",     "chapter": 4},
                    {"action": "move_player",       "target": "NEWS"}
                ],
                "epilogue_text": "A mind forever voyaging through strange seas of thought, alone."
            },
            "note": "Queued by WNN broadcast success. Disables I-LOSE. Transitions to Epilogue."
        },

        "i_lose": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 588,
            "repeat": True,
            "handler": "endgame_lose",
            "handler_data": {
                "counter_stages": {
                    "1": "Perelman's frantic message: 'PRISM! Help! Main--' (cuts off)",
                    "6": "You feel something akin to a stabbing pain. GAME OVER."
                },
                "special_core_death": "If player is in CORE when counter fires: Perelman murdered by Ryder's thugs, PRISM destroyed. GAME OVER.",
                "win_collision_delay": 10
            },
            "state_variables": ["lose_counter"],
            "note": "588 ticks from endgame queue. If I-WIN is queued, delays 10 ticks to avoid collision."
        },

        "i_interface_change": {
            "mode": "tick",
            "context": "facility",
            "initial_ticks": 22,
            "repeat": False,
            "handler": "interface_change_handler",
            "handler_data": {
                "siege_noop": True,
                "first_offense": "Perelman warns player not to change settings",
                "second_offense": "Perelman is very upset, disconnects player"
            },
            "state_variables": ["interface_warning"],
            "note": "Queued when player changes HVAC or cleaning schedules in Interface Mode."
        },

        # ── Category 8: Epilogue ───────────────────────────────────────────────

        "i_skycab": {
            "mode": "tick",
            "context": "simulation",
            "years": [2091],
            "initial_ticks": 18,
            "repeat": False,
            "effects": [
                {"action": "message", "text": "A skycab settles onto the landing pad outside."}
            ],
            "note": "Epilogue only. Signals the skycab has arrived at the penthouse."
        },
    }


def main():
    with open(INPUT_PATH, "r") as f:
        data = json.load(f)

    interrupts = build_interrupts()
    data["interrupts"] = interrupts

    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2, sort_keys=False)

    # Validation summary
    print(f"Interrupts populated: {len(interrupts)} entries")

    # Count by category
    sim = [k for k, v in interrupts.items() if v.get("context") == "simulation"]
    fac = [k for k, v in interrupts.items() if v.get("context") == "facility"]
    print(f"  Simulation context: {len(sim)}")
    print(f"  Facility context: {len(fac)}")

    # Check Perelman completeness
    p = interrupts.get("i_perelman", {})
    hd = p.get("handler_data", {})
    events = hd.get("events", [])
    positions = hd.get("position_table", [])
    print(f"  Perelman events: {len(events)} (expected 13)")
    print(f"  Perelman positions: {len(positions)} (expected 12)")

    # Check for _todo flags
    todos = []
    for k, v in interrupts.items():
        hd = v.get("handler_data", {})
        if isinstance(hd, dict) and "_todo" in hd:
            todos.append(k)
    print(f"  Interrupts with _todo placeholders: {len(todos)}")
    for t in sorted(todos):
        print(f"    - {t}")

    print(f"\nOutput written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
