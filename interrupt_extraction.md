# AMFV Complete Interrupt Extraction

## Phase 1, Session 14 Deliverable

41 I-prefixed routines exist across all ZIL source files. This document catalogs all 29 gameplay interrupts with the detail needed to populate simulation_tree.json. The remaining 12 are categorized at the end as utility, message-delivery, or skipped.

**Scope of “handler” vs “effects”:** Interrupts with branching logic, multi-step counters, NPC location tracking, or interactive sequences require JS handler functions. Simple interrupts with linear effects can use the declarative effects array from the schema.

-----

## Category 1: NPC Schedules (Simulation)

### i_jill

Source: interrupts_zil.txt line 248. ~300 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2041, 2051, 2061]
- **initial_ticks:** -1 (per-turn)
- **repeat:** true (per-turn)
- **trigger_source:** Queued by LIVING-ROOM-F when player enters apartment from hallway. Also re-queued internally (e.g., counter 14 re-queues with 28 ticks).
- **handler:** jill_schedule

**Behavior by year:**

In 2041/2051, Jill follows a detailed daily schedule driven by JILL-COUNTER (0-14) and STIME thresholds. She moves between rooms, interacts with objects, and has context-sensitive dialogue depending on which room the player occupies.

|Counter|STIME threshold |Location   |Activity                 |
|-------|----------------|-----------|-------------------------|
|0      |> 478 (7:58am)  |BEDROOM    |Wakes up, begins dressing|
|1      |> 522 (8:42am)  |BEDROOM    |Dressing, neatening room |
|2      |> 591 (9:51am)  |KITCHEN    |Making salad             |
|3      |> 644 (10:44am) |LIVING-ROOM|Reading                  |
|4      |> 697 (11:37am) |LIVING-ROOM|Painting at easel        |
|5      |> 813 (1:33pm)  |KITCHEN    |Eating salad             |
|6      |> 859 (2:19pm)  |KITCHEN    |Washing dishes           |
|7      |> 912 (3:12pm)  |LIVING-ROOM|Painting again           |
|8      |> 1084 (6:04pm) |LIVING-ROOM|Cleaning up              |
|9      |> 1137 (6:57pm) |LIVING-ROOM|Reading on couch         |
|10     |> 1242 (8:42pm) |BATHROOM   |Wetting hair             |
|11     |> 1299 (9:39pm) |BEDROOM    |Reading in bed           |
|12     |> 1402 (11:22pm)|BEDROOM    |Falls asleep             |

Counter 13: Post-raid crying state (set by I-APARTMENT). Counter 14: Post-raid cleanup (re-queued from I-APARTMENT at 28 ticks).

On first apartment visit per simulation session (TOUCHBIT unset), Jill has a greeting interaction gated by current JILL-COUNTER value. Also has a 5% random dialogue trigger about interest rates (2041) or Clave’s call (2051).

In 2061: One-time event. When queued (9 ticks), Jill enters upset about Mitchell joining the Church of God’s Word. Long narrative speech. Scores index 119 (4 pts). Moves Jill to BEDROOM. Sets MITCHELL-NEWS-FLAG, FOLLOW-FLAG.

**handler_data needed:** Full schedule table (counter/time/room/activity), year-branched text, greeting text by counter, random dialogue text by year.

**State variables:** JILL-COUNTER, JILL-NOT-SPOKEN-YET, MITCHELL-NEWS-FLAG, FOLLOW-FLAG.

**Objects moved:** JILL, JILL-BOOK, SALAD, REFRIGERATOR (OPENBIT toggled).

-----

### i_mitchell

Source: interrupts_zil.txt line 553. ~90 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2041, 2051]
- **initial_ticks:** -1 (per-turn)
- **repeat:** true (per-turn)
- **trigger_source:** Queued by apartment enter logic when SYEAR is 2041 or 2051. Disables itself when player leaves apartment.
- **handler:** mitchell_schedule

**Daily schedule (MITCHELL-COUNTER):**

|Counter|STIME threshold |Location   |Activity                    |
|-------|----------------|-----------|----------------------------|
|0      |> 463 (7:43am)  |LIVING-ROOM|Getting ready for school    |
|1      |> 505 (8:25am)  |(leaves)   |Goes to school              |
|2      |> 1011 (4:51pm) |LIVING-ROOM|Comes home, plays logic game|
|3      |> 1120 (6:40pm) |LIVING-ROOM|Does homework               |
|4      |> 1374 (10:54pm)|(partition)|Goes to bed                 |

Context-sensitive text based on player location (LIVING-ROOM vs PARKVIEW-HALL vs elsewhere).

**handler_data needed:** Schedule table, dialogue text per transition, the ALGEBRA constant (homework comment).

**State variables:** MITCHELL-COUNTER.

**Objects moved:** MITCHELL, HOMEWORK, LOGIC-GAME.

-----

### i_mitchell_raid

Source: apartment_zil.txt line 1678. ~50 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2071]
- **initial_ticks:** 19
- **repeat:** false
- **trigger_source:** Queued by LIVING-ROOM-F when player enters apartment from PARKVIEW-HALL in 2071 and MITCHELL-RAID-FLAG is false.
- **effects:** (declarative, one-time narrative)

**Effects:**

1. Score index 120 (9 pts)
1. Move player to LIVING-ROOM
1. Narrative: Mitchell returns with Church police, identifies Jill as heretic, Jill is dragged away screaming, player is beaten
1. Set MITCHELL-RAID-FLAG = true, BRUISED = true
1. Move JILL to LOCAL-GLOBALS (removed from game)
1. Close APARTMENT-DOOR
1. Queue I-APARTMENT at -1 (per-turn, for subsequent BSF raid)

**Port note:** This is the single most emotionally devastating scene in the game. The visual port should handle this with care. It could be a full-screen text overlay with atmospheric treatment.

-----

## Category 2: Law Enforcement (Simulation)

### i_curfew

Source: interrupts_zil.txt line 727. ~50 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2051, 2061, 2071]
- **initial_ticks:** -1 (per-turn)
- **repeat:** true (per-turn, re-queues itself)
- **trigger_source:** Queued in year_init for 2051, 2061, 2071.
- **handler:** curfew_handler

**Conditions checked each turn:**

1. If player is in JAIL-CELL: check ELAPSED-TIME. If > 100, re-queue at 5 and wait. Otherwise, release player to ELM-AND-PARK with cop’s warning speech. Set LIGHT-LEVEL to 3.
1. If STIME between 420-1260 (daytime): disable self, no curfew during day.
1. If player is NOT on a street (no STREETBIT): re-queue per-turn, do nothing.
1. If random 8% check passes:
- In 2071: DEATH. Score 117 (8 pts). Player shot by drunk cop.
- In 2051/2061: Score 116 (2 pts). Player arrested, moved to JAIL-CELL. Re-queues for release timing.
1. Otherwise: re-queue per-turn.

**handler_data needed:** Year-variant arrest text, release text, death text. Curfew hours (420-1260 = 7:00am-9:00pm). Probability (8%).

**State variables:** LIGHT-LEVEL. BLANKET moved to JAIL-CELL during jailing.

-----

### i_jail

Source: rockvil_zil.txt line 887. ~30 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2051, 2061, 2071]
- **initial_ticks:** (variable, set by i_curfew’s re-queue logic)
- **repeat:** false
- **trigger_source:** Handled by i_curfew’s jail release logic (embedded in same routine).

**Port note:** I-JAIL in the ZIL is actually handled entirely within I-CURFEW. The separate routine at line 887 is never queued; the jail release logic is inside the JAIL-CELL branch of I-CURFEW. For the port, model this as part of the curfew handler, not a separate interrupt.

-----

### i_apartment

Source: interrupts_zil.txt line 646. ~80 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2051, 2061, 2071]
- **initial_ticks:** -1 (per-turn) or 30 or 10 (context-dependent)
- **repeat:** false (but re-queues itself conditionally)
- **trigger_source:** Queued in year_init for 2061 (initial_ticks: 40). Queued by LIVING-ROOM-F for 2051 and 2071. Also re-queued internally after raids.
- **handler:** apartment_raid

**Logic:**

1. If JILL-COUNTER = 13 (post-Mitchell-news crying): transition to counter 14, queue I-JILL at 28 ticks. Not a raid.
1. If player not in apartment: disable self.
1. If nighttime (STIME > 1320 or < 480): re-queue at 30. No raids at night.
1. If NOT 2041 and APARTMENT-RAID-FLAG is false:
- PROB(RAID-PROB) check. RAID-PROB starts at 0 and increases by 6 per non-raid turn (so 0%, 6%, 12%, 18%…).
- If raid triggers:
  - Door slam/commotion text
  - Move player to LIVING-ROOM
  - BSF officers search apartment with Rad-Detectors
  - Year-variant aftermath:
    - 2051: Apologetic leader, “Sorry for the inconvenience.” Jill cries. Score 8 (3 pts). I-JILL disabled, JILL-COUNTER set to 13, I-APARTMENT re-queued at 10.
    - 2061: Gruff dismissal, “Keep it that way.” Score 9 (4 pts). Disable self.
    - 2071: Destructive search, overturn furniture. If BOOK-PURCHASED, book destroyed. Score 10 (5 pts). Door left open. Disable self.
- If raid doesn’t trigger: RAID-PROB += 6.

**handler_data needed:** RAID-PROB mechanics, year-variant text, post-raid state changes.

**State variables:** APARTMENT-RAID-FLAG, RAID-PROB (init 0), BOOK-PURCHASED, JILL-COUNTER. Objects: APARTMENT-DOOR (OPENBIT), BOOK.

-----

## Category 3: Environmental Dangers (Simulation)

### i_mug

Source: rockvil_zil.txt line 10554. ~40 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2071]
- **initial_ticks:** 7
- **repeat:** 7
- **trigger_source:** Queued in year_init for 2071.
- **handler:** mug_handler

**Pre-check conditions (checked each fire, not at queue time):**

1. Must be nighttime (LIGHT-LEVEL = 0)
1. Must be outdoors (room has OUTSIDEBIT)
1. Random check (PROB with some value, need to verify)

If conditions met: gang attack text, MUGGED = true, CREDIT = 0, score 100.

**Port note:** The schema example already covers this. Needs the OUTSIDEBIT + night pre-check either in the condition field or as a handler pre-check.

-----

### i_hunger

Source: rockvil_zil.txt line 3155. ~15 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2081]
- **initial_ticks:** 65
- **repeat:** false (but re-queues at 47 on first fire)
- **trigger_source:** Queued in year_init for 2081.
- **effects:** (declarative, two-step)

**Step 1 (tick 65):** Warning text (“Hunger overwhelms you…”). Set HUNGER-WARNING = true. Score 40 (3 pts). Re-queue at 47 ticks.

**Step 2 (tick 47 after step 1):** Death. “You finally succumb to the ravages of hunger.” Score 40 again (idempotent; already fired).

**Port note:** Eating at a restaurant, buying groceries, or finding food in 2081 is not possible (restaurant closed, stores looted). This timer is essentially a death clock. The engine should track whether any food-related action resets it (none do in the ZIL).

-----

### i_wild_dogs

Source: interrupts_zil.txt line 1248. ~25 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2081]
- **initial_ticks:** -1 (per-turn)
- **repeat:** true (per-turn)
- **trigger_source:** Queued in year_init for 2081 AND by MAIN-STREET-BRIDGE-F on room entry. Disables when player leaves MAIN-STREET-BRIDGE.
- **handler:** wild_dogs_handler

**Escalating 4-step sequence (WILD-DOG-COUNTER):**

|Counter|Event                                                    |
|-------|---------------------------------------------------------|
|1      |Distant barking heard to the east. BARKING object placed.|
|2-3    |Barking continues, getting closer.                       |
|4      |Pack attacks. Score 45 (3 pts). DEATH.                   |

Player must leave the bridge before counter 4 to survive. Exiting east (MAIN-STREET-BRIDGE-EXIT-F) in 2081 is also instant death (separate from this interrupt).

**State variables:** WILD-DOG-COUNTER (init 0). BARKING object.

-----

### i_athletic_field

Source: rockvil_zil.txt line 6130. ~30 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2061, 2071]
- **initial_ticks:** -1 (per-turn)
- **repeat:** false (but re-queues at 1 for 2071 second step)
- **trigger_source:** Queued by ATHLETIC-FIELD-F on room entry. Disables when player leaves.
- **effects/handler:** Simple enough for effects with year branching.

**In 2061:** Children mock player, pluck at clothing. Score 80 (2 pts). Non-lethal.

**In 2071:** Two-step:

1. First turn: Children gather menacingly, pick up stones. STONING-FLAG = true. Re-queue at 1.
1. Second turn: Children stone player to death. Score 81 (7 pts). DEATH.

**State variables:** STONING-FLAG (init false).

-----

## Category 4: Ambient / Environmental (Simulation)

### i_sunrise_sunset

Source: interrupts_zil.txt line 775. ~80 lines.

- **mode:** condition (per-turn check on time_advance)
- **context:** simulation
- **years:** null (all years)
- **trigger_source:** Queued in year_init for all years (ticks: -1).
- **handler:** sunrise_sunset

Already documented in schema. Updates LIGHT-LEVEL (0-3) based on STIME thresholds with month-dependent offsets. Base thresholds: dawn glow 300, sun peek 360, full day 420, evening 1080, sunset 1140, night 1200.

**handler_data:** Already in schema (base_thresholds + month_offsets).

-----

### i_city_noises

Source: rockvil_zil.txt line 10460. ~100 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2041, 2051, 2061, 2071] (not 2081)
- **initial_ticks:** 2 (from year_init)
- **repeat:** random (re-queues at 6 + RANDOM(7) = 7-13 ticks)
- **trigger_source:** Queued in year_init for 2041-2071.
- **handler:** city_noises

**Pre-check conditions (all must fail for text to fire):**

1. Player NOT on street (no STREETBIT): suppress
1. NOT daytime (LIGHT-LEVEL != 3): suppress
1. Room has BADAREABIT: suppress
1. Room is AIRPORT-ENTRANCE, BASE-GATE, or INTERCHANGE: suppress
1. Year is 2081: suppress
1. Room is ROCKVIL-UNIVERSITY and year is 2061/2071: suppress
1. PROB(75) passes: suppress (75% chance of no noise even when conditions met)

If all checks pass: print random text from year-specific table.

**handler_data needed:** Four text tables (8 entries each):

- 2041: newspapers, trucks, taxis, skycopters, police frisking youth, car alarms, stranger bumps, religious man
- 2051: newspapers, panhandler, dog, near-collision, porta-stereos, policeman, siren, stranger bumps
- 2061: siren, police van, pregnant woman, BSF patrol, rotting odor, wailing siren, pistol shot, skycar crash
- 2071: wind/dust, teenager kicking can, BSF patrol, Church Police Paddywagon, lynch mob, panhandler dragged into alley, prostitute with Church official, scream from building

-----

### i_church_skycopter

Source: rockvil_zil.txt line 4972. ~5 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2051]
- **initial_ticks:** ELAPSED-TIME + 1 (effectively 1 tick after scene)
- **repeat:** false
- **trigger_source:** Queued by HALLEY-AND-UNIVERSITY-F scene event (one-time, 2051 only).
- **effects:** (declarative)

**Effects:**

1. Message: “The skycopter, heading away, disappears from view.”
1. Remove CHURCH-SKYCOPTER object from room.

**Port note:** This is a cleanup timer for a one-shot scene event. The skycopter scene at Halley & University triggers independently via the room’s SCENE property (first visit in 2051). Could be folded into the room description system rather than modeled as an interrupt.

-----

## Category 5: Interactive Sequences (Simulation)

### i_meal

Source: rockvil_zil.txt line 3758. ~70 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2041, 2051, 2061, 2071] (restaurants closed in 2081)
- **initial_ticks:** 12 (initial wait) then 1 (waiter prompts)
- **repeat:** variable (re-queues at 1 during waiter interaction)
- **trigger_source:** Queued by V-YES when player accepts maitre d’s seating (MEAL-STATUS transitions).
- **handler:** meal_sequence

**Multi-step sequence (driven by MEAL-STATUS and credit card state):**

1. Player enters restaurant, maitre d’ asks “Party of one?” (MEAL-STATUS = 1). If player lingers > 8 turns without saying yes, kicked out.
1. Player says yes, seated at table (MEAL-STATUS = 3).
1. Waiter presents menu. Year-variant food (2041: soybean salad; others: kelp fillet). MEAL-STATUS = 4. Asks for credit card.
1. If CREDIT-CARD given to SPEAR-CARRIER (waiter):
- If CREDIT < 65: insufficient funds, escorted out.
- If CREDIT >= 65: meal served, CREDIT debited 65, recording task 0 completed. MEAL-STATUS = 6.
1. If no card after 4 turns: waiter warns. After 6 turns: bounced by maitre d’.

**handler_data needed:** Menu text by year, credit threshold (65), waiter dialogue, timing.

**State variables:** MEAL-STATUS (init 0), WAITER-COUNTER (init 0), MAITRE-COUNTER (init 0), CREDIT. CREDIT-CARD object location. RECORDING-TABLE[0] set on completion.

-----

### i_foodville

Source: rockvil_zil.txt line 1392. ~20 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2061, 2071] (ration card required in these years)
- **initial_ticks:** 2
- **repeat:** false (one-shot per visit)
- **trigger_source:** Queued by Foodville room enter functions.
- **effects:** (declarative, two-step)

**Step 1 (first fire):** Clerk asks for ration card. CLERK-WAITING = true. Re-queue at 2.

**Step 2 (second fire):** If player hasn’t given ration card: bounced. “The clerk says, ‘Listen, joker…’” Player moved to adjacent street (SOUTHWAY-AND-PARK from FOODVILLE-1, MAIN-AND-WICKER from FOODVILLE-2).

**State variables:** CLERK-WAITING (init false).

-----

### i_joybooth_recharge

Source: rockvil_zil.txt line 2659. ~3 lines.

- **mode:** tick
- **context:** simulation
- **years:** [2071] (joybooth only exists in 2071)
- **initial_ticks:** 60
- **repeat:** false
- **trigger_source:** Queued by JOYBOOTH-BUTTON-F when player uses joybooth.
- **effects:** none (routine returns RFALSE)

**Port note:** This is a pure cooldown timer. The joybooth checks QUEUED?(I-JOYBOOTH-RECHARGE) to determine if recharging. When the 60-tick timer expires and the routine fires (doing nothing), the interrupt is dequeued, and the joybooth becomes usable again. For the port, model as a boolean state flag (joybooth_recharging) with a tick countdown, or just track the cooldown end time.

-----

## Category 6: Facility Progression

### i_perelman

Source: interrupts_zil.txt line 8. ~240 lines.

- **mode:** condition (per-turn)
- **context:** facility
- **initial_ticks:** -1 (per-turn)
- **trigger_source:** Queued at game start and re-queued after various facility events.
- **handler:** perelman_schedule

Already partially documented in schema. Perelman has day-specific schedules for days 16-20+ of March 2031. He moves between OFFICE, CAFETERIA, and CONTROL-CENTER, delivers messages, and responds to player interaction.

**handler_data needed:** Full per-day schedule extracted from the I-PERELMAN routine. This is the most complex facility handler (240 lines of ZIL) and requires its own dedicated extraction pass.

-----

### i_rorschach

Source: interrupts_zil.txt line 993. ~60 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 9 (queued by I-MESSAGE-X)
- **repeat:** true (per-turn after activation, via QUEUE -1)
- **trigger_source:** Queued by I-MESSAGE-X.
- **handler:** rorschach_test

**Sequence:**

1. Grimwold and Perelman arrive in OFFICE.
1. Grimwold asks player to begin (“Ready to begin?”).
1. If player is not in OFFICE, waits (re-queues at 1).
1. If player doesn’t respond for 8 turns: Grimwold leaves (“This rudeness will certainly figure in my report!”). Perelman re-queued at 30 ticks.
1. If player responds (handled by BLOT-ACTION in verbs_zil.txt): Rorschach inkblot test begins (player types words in response to patterns).

**handler_data needed:** Grimwold arrival text, patience counter (8 turns max), exit text.

**State variables:** GRIMWOLD-COUNTER (init 0), PSYCH-TEST-ACTIVE (blocks simulation mode entry). GRIMWOLD and PERELMAN object positions.

**Port note:** The interactive Rorschach test requires the player to type words. In a point-and-click port, this could be a text input overlay (typing is thematically appropriate since PRISM is a computer), or it could be simplified to a button-response interaction. Design decision needed.

-----

### i_first_simulation_result

Source: prism_zil.txt line 1764. ~110 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 7 (queued by I-MESSAGE-E) or 2 (queued by BUFFER-RESULT)
- **repeat:** false
- **trigger_source:** Queued after player’s first simulation session when recordings are submitted for review.
- **handler:** first_sim_result

**Logic:**

Counts how many of the 9 recording tasks (RECORDING-TABLE) have been completed.

- All 9 complete: Success. COMPLETED-TASKS = true. Part Two begins (CHAPTER-PRINT 2). Queues I-MESSAGE-X (12 ticks) and I-MESSAGE-Q (77 ticks). Advances time 680 minutes.
- 8 of 9 complete: Perelman asks to redo the one missing task. Player re-enters simulation.
- < 8 complete: Perelman is unhappy, lists missing tasks, tells player to redo.

**State variables:** COMPLETED-TASKS, RECORDING-TABLE, PART-FLAG (set to 2 on success). MESSAGE-E-COUNTER.

-----

### i_view

Source: prism_zil.txt line 4600. ~15 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** variable (RECORD-BUFFER size + 5)
- **repeat:** false
- **trigger_source:** Queued by BUFFER-RESULT when player submits recordings for review.
- **effects:** (declarative-ish)

**Effects:**

1. Queue I-RECORDINGS-VIEWED at 6 ticks.
1. Queue I-MESSAGE-E at 14 ticks (nag to come to office).
1. Perelman message: “Several of us have just finished viewing the [recordings].”

-----

### i_recordings_viewed

Source: prism_zil.txt line 4616. ~100 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 6 (queued by I-VIEW)
- **repeat:** false
- **trigger_source:** Queued by I-VIEW.
- **handler:** recordings_viewed_evaluator

**Critical win-condition logic:**

Evaluates per-year observation scores against minimum thresholds:

|Year|Minimum score|Half-minimum|
|----|-------------|------------|
|2051|> 10         |> 5         |
|2061|> 20         |> 10        |
|2071|> 40         |> 20        |
|2081|> 14         |> 7         |

If TOTAL = 4 (all four years meet minimum): **TRIGGERS ENDGAME.** Queues the full endgame chain:

- I-MESSAGE-Z at 14 ticks
- I-PERELMAN-RETURNS at 22 ticks
- I-SEIGE at 73 ticks
- I-RYDER at 116 ticks
- I-SABOTAGE at 175 ticks
- I-LOSE at 588 ticks

Also: sets PART-FLAG to 3, transitions to Part Three, advances time.

If TOTAL < 4: Perelman gives partial feedback based on which years passed/failed. If recordings were empty or didn’t include simulation data, he’s confused/disappointed.

**handler_data needed:** Score thresholds per year, endgame queue timings, feedback text variants.

**State variables:** 2051_SCORE, 2061_SCORE, 2071_SCORE, 2081_SCORE. RECORDINGS-INCLUDE-SIMULATION.

-----

## Category 7: Facility Endgame Chain

These five interrupts form the endgame timing chain, all queued by I-RECORDINGS-VIEWED.

### i_perelman_returns

Source: prism_zil.txt line 4891. ~12 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 22 (from endgame queue)
- **repeat:** false
- **effects:** (declarative)

**Effects:**

1. Perelman message: “PRISM, I’m just back from Washington. I met with the new Plan Authority… They rejected the contents outright. They called the recordings fakes.”

-----

### i_seige

Source: prism_zil.txt line 4904. ~20 lines. (Note: ZIL has typo “SEIGE” for “SIEGE”.)

- **mode:** tick
- **context:** facility
- **initial_ticks:** 73 (from endgame queue)
- **repeat:** false
- **effects:** (declarative)

**Effects:**

1. Set SEIGE = true.
1. Move NATIONAL-GUARDSMAN to CONTROL-CENTER.
1. Announcement: Major General Dirk Peters, facility sealed off.
1. If player in CONTROL-CENTER: see guardsmen take positions.

Already documented in schema.

-----

### i_sabotage

Source: prism_zil.txt line 4921. ~100 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 175 (from endgame queue)
- **repeat:** false (but re-queues itself between stages)
- **handler:** endgame_sabotage

**4-stage sequence (SABOTAGE-COUNTER 0-3):**

|Counter|Delay after|Event                                                                                      |
|-------|-----------|-------------------------------------------------------------------------------------------|
|0      |16 ticks   |Saboteurs arrive by skyvan on rooftop (visible if player there)                            |
|1      |33 ticks   |Saboteurs enter CORE, begin tampering with HVAC. Queue I-SUFFOCATE if HVAC unit 11 is at 0.|
|2      |16 ticks   |Saboteurs finish, leave CORE.                                                              |
|3      |(end)      |Saboteurs board skyvan on rooftop, leave.                                                  |

If SABOTAGE-COUNTER = 2 and I-SUFFOCATE is still running: wait (re-queue at 2) until suffocation resolves.

**State variables:** SABOTAGE-COUNTER (init 0). Objects: SABOTEURS, TOTE-BAGS. HVAC-STATUS-TABLE.

Already partially documented in schema.

-----

### i_suffocate

Source: interrupts_zil.txt line 930. ~35 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** -1 (per-turn, queued by I-SABOTAGE stage 1)
- **repeat:** true (per-turn)
- **handler:** suffocate_handler

**Counter-based sequence (SUFFOCATE-COUNTER):**

|Counter|Event (if player in CORE)                                                     |
|-------|------------------------------------------------------------------------------|
|8      |Saboteur: “Stuffy in here, isn’t it?” (YES-NO prompt)                         |
|13     |“Hurry, will ya! I need some fresh air!”                                      |
|16     |One gasps and falls. Others pass out. Disable I-SABOTAGE. Re-queue self at 24.|
|17     |National Guard patrol rescues unconscious saboteurs.                          |

If player talks to saboteurs (TELL action) while they’re conscious: they shoot the comm outlet, PRISM dies. If player waits for them to pass out, the crisis resolves itself.

**State variables:** SUFFOCATE-COUNTER (init 0). SABOTEURS LDESC changes.

-----

### i_air_conditioning

Source: interrupts_zil.txt line 970. ~25 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** -1 (per-turn, queued by I-SABOTAGE stage 2)
- **repeat:** true (per-turn)
- **handler:** air_conditioning_death

**Counter-based death clock (AIR-CONDITIONING-COUNTER):**

|Counter|Event                                                     |
|-------|----------------------------------------------------------|
|20     |V-DIAGNOSE: show symptoms (heat-related)                  |
|35     |V-DIAGNOSE again: symptoms worsening                      |
|46     |PRISM dies. If in simulation: forced out first. GAME OVER.|

Player can stop this by reaching the Maintenance Core and fixing the HVAC (via the Interface Mode HVAC controls). If HVAC is repaired, this interrupt should be disabled.

**State variables:** AIR-CONDITIONING-COUNTER (init 0).

-----

### i_ryder

Source: prism_zil.txt line 5084. ~100 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 116 (from endgame queue), then -1 (per-turn)
- **repeat:** true (per-turn after activation)
- **handler:** endgame_ryder

**6-step confrontation (RYDER-COUNTER):**

|Counter|Event (only visible if player in OFFICE)                                                                                                                     |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
|1      |Ryder and Perelman enter office. Guardsmen outside door.                                                                                                     |
|2      |Ryder: “Shut up, Perelman!” Perelman begins to notice player.                                                                                                |
|3      |Ryder threatens: “A helluva lot of people have a helluva lot at stake.”                                                                                      |
|4      |Ryder: “Don’t think you’re gonna get special consideration.”                                                                                                 |
|5      |Ryder threatens Perelman: “You wouldn’t be the first person who’s gotten crushed.” If Perelman has noticed PRISM recording, he taunts Ryder (“Vintage thug”).|
|6      |Ryder delivers ultimatum: facility locked down, no communications. Leaves with Perelman escorted by guards.                                                  |

If player speaks to Ryder at any point: Ryder discovers PRISM is active, drags Perelman away (ends the confrontation early, player loses recording opportunity).

**RECORDING tracking:** Each turn player is in OFFICE with RECORDING = true, RYDER-RECORDED increments. Must reach >= 2 for win condition.

**Win trigger:** After Ryder leaves, if player broadcasts recordings via WNN transmitter in Interface Mode, I-WIN is queued (13 ticks).

**handler_data:** Dialogue per step, PERELMAN-NOTICED flag behavior.

**State variables:** RYDER-COUNTER (init 0), RYDER-RECORDED (init 0), PERELMAN-NOTICED.

Already partially documented in schema.

-----

### i_open_window

Source: prism_zil.txt line 5024. ~10 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 26 (queued by HVAC interface interaction)
- **repeat:** false (re-queues at 4 if player not in CONTROL-CENTER)
- **effects:** (declarative)

**Effects:**

1. If player in CONTROL-CENTER: technician opens window (foreshadowing HVAC problems).
1. If player not in CONTROL-CENTER: re-queue at 4 (waits for player).

-----

### i_win

Source: prism_zil.txt line 5187. ~30 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 13 (queued by WNN broadcast success)
- **repeat:** false
- **handler:** endgame_win

**Effects:**

1. Disable I-LOSE.
1. Perelman message: “You’ve done it! That was brilliant!” Plan is dead. PRISM is a hero.
1. Advance time (month + 1, randomize time of day).
1. Transition to EPILOGUE (CHAPTER-PRINT 4).
1. Move player to NEWS (World News Network Feed comm outlet).
1. Display Wordsworth quote: “A mind forever voyaging through strange seas of thought, alone.”

-----

### i_lose

Source: prism_zil.txt line 5220. ~30 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 588 (from endgame queue), then -1 (per-turn)
- **repeat:** true (per-turn after activation)
- **handler:** endgame_lose

**Sequence (LOSE-COUNTER):**

1. If I-WIN is queued: delay 10 ticks (avoid collision).
1. Counter 1: Perelman’s frantic message: “PRISM! Help! Main–” (message cuts off).
1. Counter 6: “You feel something akin to a stabbing pain.” GAME OVER.

Special case: if player is in CORE when LOSE-COUNTER fires: Perelman is murdered by Ryder’s thugs in front of PRISM. PRISM’s machinery destroyed. GAME OVER.

**State variables:** LOSE-COUNTER (init 0).

-----

## Category 8: Facility Miscellaneous

### i_interface_change

Source: prism_zil.txt line 3880. ~50 lines.

- **mode:** tick
- **context:** facility
- **initial_ticks:** 22 (queued by Interface Mode interactions)
- **repeat:** false
- **trigger_source:** Queued when player changes HVAC or cleaning schedules in Interface Mode.
- **handler:** interface_change_handler

**Effects:**

1. If SEIGE is true: no-op (Perelman can’t respond during siege).
1. Reset all HVAC-STATUS-TABLE entries to defaults.
1. Reset all cleaning schedule times to defaults.
1. Enable transmitter (FSET TRANSMITTER ONBIT).
1. If INTERFACE-WARNING already true: Perelman is very upset, disconnects player.
1. If first offense: Perelman warns player not to change settings.
1. INTERFACE-WARNING = true.

**Port note:** Interface Mode is where the player interacts with facility systems (HVAC, cleaning schedules, auditing). Most of this is optional exploration, but during the endgame the player must use Interface Mode to broadcast recordings via the WNN transmitter. The HVAC controls also let the player fix the sabotage.

-----

## Category 9: Facility Messages (NOT interrupts section)

These 8 routines deliver messages from Perelman to PRISM’s library. They should be modeled in the **facility.messages** section of simulation_tree.json, not in interrupts. Each adds a message object to the PRISM-MESSAGES-DIRECTORY and triggers follow-on events.

|Routine    |Queued by                |Ticks |Purpose                                    |
|-----------|-------------------------|------|-------------------------------------------|
|I-MESSAGE-C|Game start (day 16)      |~55   |Delivers initial briefing, enables sim mode|
|I-MESSAGE-D|Return from simulation   |var   |Announces recording review                 |
|I-MESSAGE-E|Various (nag timer)      |14    |“Please come to my office” (repeating)     |
|I-MESSAGE-M|I-MESSAGE-C              |875   |“Enter simulation mode” (escalating nag)   |
|I-MESSAGE-Q|I-FIRST-SIMULATION-RESULT|77    |Post-Part-Two message                      |
|I-MESSAGE-X|I-FIRST-SIMULATION-RESULT|12    |Sets up Rorschach test                     |
|I-MESSAGE-Y|(after Part Two tasks)   |var   |Unlocks auditing system                    |
|I-MESSAGE-Z|I-RECORDINGS-VIEWED      |14/274|Endgame message, enables WNN transmitter   |

**Population note:** These need their own extraction pass to capture the exact message text from each MESSAGE object’s TEXT property, and the queueing/re-queueing logic. Estimate: 1 session.

-----

## Category 10: Utility Interrupts (Engine-Internal)

### i_unfollow

Source: verbs_zil.txt line 887. Resets FOLLOW-FLAG to 0 after 2 ticks. Used by NPC movement to prevent overlapping descriptions. For the port, model as an engine-internal timer, not a game interrupt.

### i_yes_no

Source: verbs_zil.txt line 2359. Resets YES-NO-FLAG to 0 after 2 ticks. Used for timed yes/no prompts. For the port, model as a UI timeout on interactive prompts.

-----

## Category 11: Skipped

### i_red_tube, i_brown_tube

Source: rockvil_zil.txt lines 10203 and 10325. Tubecar movement timers. Skipped per instant-travel design decision (Session 11).

-----

## Summary Statistics

|Category                     |Count  |Handler|Declarative|
|-----------------------------|-------|-------|-----------|
|NPC Schedules                |3      |2      |1          |
|Law Enforcement              |2*     |1      |1          |
|Environmental Dangers        |4      |2      |2          |
|Ambient/Environmental        |3      |2      |1          |
|Interactive Sequences        |3      |1      |2          |
|Facility Progression         |5      |4      |1          |
|Facility Endgame Chain       |9      |5      |4          |
|Facility Miscellaneous       |1      |1      |0          |
|**Total gameplay interrupts**|**30***|**18** |**12**     |

*I-JAIL is embedded in I-CURFEW; they are documented together as one interrupt. 30 documented entries, 29 distinct engine interrupts.

**Handler functions needed: 18.** These are the JS functions that the engine must implement. Each receives its handler_data from the JSON.

**Declarative interrupts: 12.** These can use the effects array from the schema without custom code.

-----

## Design Decision: i_perelman Full Extraction

I-PERELMAN is the largest single routine (240 lines) and the most complex handler. It has per-day branching for days 16-20+, time-of-day movement between rooms, interaction with other interrupts (Rorschach, messages, simulation results), and multiple state variables (LAST-ABE-TIME, PERELMAN object position, COFFEE object). Full extraction of this handler’s data tables warrants its own focused analysis pass, possibly as a sub-task of the next session.

-----

## Next Steps

1. Convert this document to JSON entries in simulation_tree.json (Claude Code session).
1. Extract I-PERELMAN full schedule (separate analysis pass).
1. Extract facility.messages content (MESSAGE-A through MESSAGE-Z text).
1. Populate handler_data for the 17 handler interrupts.

-----

## Revision History

- v1.0 (Session 14): Complete extraction from ZIL source. 29 gameplay interrupts cataloged.