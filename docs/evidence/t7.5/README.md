# T7.5 evidence — live director via LangGraph

> [!TIP]
> D4 is no longer a diagram: `talk` routes through the compiled graph's `narrate` node (`test_talk_routes_through_graph` proves the node receives floor/text/build_tags and streams real prose); `attack` runs `encounter_gen`, whose compose→clamp→four-judges pipeline must approve before `commit_encounter` writes the room — a composed variant's stats feed `fight_begin` verbatim (`test_committed_variant_feeds_the_fight`, max_hp 123 passes through).

> [!NOTE]
> Judge rejection twice parks the run at a real LangGraph `interrupt`: the player receives `decision_request` and resumes with fallback (derived engine-standard foe) or flee — `test_judges_reject_parks_decision_then_fallback`, `test_flee_option_ends_without_a_fight`. Repair budget respected across resume (`calls == 2`). Two builds probe different compositions (`[["brawler"], ["alchemist"]]`). Graph contract tests: 7/7 in `tests/test_graph.py`; live WS loop: 5/5 in `tests/test_director_live.py`.
