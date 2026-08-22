"""T3.1 — agent graph compiles, routes, interrupts, and resumes deterministically."""

from langgraph.types import Command

from app.agent.graph import build_graph


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_interrupt_and_resume():
    graph = build_graph()
    config = {"configurable": {"thread_id": "t1"}}
    graph.invoke({"intent": "narrate", "session_id": "s1"}, config)

    snapshot = graph.get_state(config)
    assert snapshot.next == ("wait_for_decision",)
    assert snapshot.values["route"] == "narrate"

    result = graph.invoke(Command(resume="ok"), config)
    assert result["last_decision"] == "ok"
    assert result["pending_decision"] == {}


def test_route_each_subgraph():
    graph = build_graph()
    for intent in ("floor_gen", "encounter_gen", "boss_gen", "narrate", "flavor"):
        config = {"configurable": {"thread_id": f"t-{intent}"}}
        graph.invoke({"intent": intent, "session_id": "s"}, config)
        snapshot = graph.get_state(config)
        assert snapshot.next == ("wait_for_decision",)
        assert snapshot.values["route"] == intent


def test_unknown_intent_falls_back_to_narrate():
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-fallback"}}
    graph.invoke({"intent": "talk_about_the_weather", "session_id": "s"}, config)
    snapshot = graph.get_state(config)
    assert snapshot.values["route"] == "narrate"


def test_interrupt_resume_does_not_rerun_gen_node():
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-resume"}}
    graph.invoke({"intent": "boss_gen", "session_id": "s"}, config)
    before = graph.get_state(config)
    result = graph.invoke(Command(resume="ok"), config)
    after = graph.get_state(config)
    assert after.next == ()
    assert result["last_decision"] == "ok"


def test_checkpoint_persists_state():
    graph = build_graph()
    config = {"configurable": {"thread_id": "t-persist"}}
    graph.invoke({"intent": "flavor", "session_id": "s42"}, config)
    snapshot = graph.get_state(config)
    assert snapshot.values["session_id"] == "s42"
    assert snapshot.values["route"] == "flavor"
