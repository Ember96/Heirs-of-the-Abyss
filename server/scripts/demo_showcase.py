"""LangGraph + LangChain + LangSmith showcase — three demo scenarios.

Run:  cd server && uv run python scripts/demo_showcase.py
Each phase pauses for the presenter. LangSmith traces visible at:
https://smith.langchain.com/projects
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, llm
from app.agent import director
from app.evals.llm_judge import judge_narrative, judge_rule_adherence


def header(text: str) -> None:
    print(f"\n{'=' * 60}\n  {text}\n{'=' * 60}\n")


def trace_url() -> str:
    project = os.environ.get("LANGCHAIN_PROJECT", "heirs-of-the-abyss-demo")
    return f"  📊 LangSmith: https://smith.langchain.com/o/{project}"


def pause() -> None:
    input("\n  ⏸  Press Enter to continue…")


# ── Phase 1 ──────────────────────────────────────────────────────────────────

def phase1_composer():
    header("SCENARIO 1 — The Director Composes Your Enemy")

    from app.game.catalog import load
    from app.agent.tools import EnemyVariant
    from app.agent.verifiers import verify

    data = load()
    enemy_ids = [e["id"] for e in data["enemies"]]
    affix_ids = [a["id"] for a in data["affixes"]]
    builds = [
        ("Brawler", ["brawler", "heavy-armor", "two-handed"]),
        ("Alchemist", ["alchemist", "light-armor", "potions", "ranged"]),
    ]

    for class_name, tags in builds:
        print(f"  🎭 Build: {class_name}")
        print(f"     Build tags: {tags}")
        print(f"     Composing via {config.MODEL_CHAT}…\n")

        variant, verdict = director.compose_and_verify(tags, 2)

        status = "✅ APPROVED" if verdict.approved else "❌ REJECTED"
        print(f"  → Composed: {variant.enemy_id} ({variant.name})")
        print(f"     Affixes: {variant.affixes}")
        print(f"     Stats:   {variant.stats}")
        print(f"     Verdict: {status}")
        for j in verdict.judges:
            icon = "✅" if j.passed else "❌"
            print(f"       {icon} {j.judge}: {j.reason or 'pass'}")
        print()

        # rule-adherence judge (NFR-8)
        rq = judge_rule_adherence(variant.model_dump(), tags)
        print(f"  📊 Rule-adherence (LLM-judge): {rq:.0f}/100 (threshold 95)")
        print()

    print(trace_url())
    print("  💡 Two different builds → the LLM composed different enemies.")
    print("     Four judges gated each composition before commit.")


# ── Phase 2 ──────────────────────────────────────────────────────────────────

def phase2_narrator():
    header("SCENARIO 2 — The Narrator That Never Breaks Character")

    contexts = [
        (3, "I light the torch and peer into the darkness", ["brawler"]),
        (7, "I taste the air — something rotten this way", ["alchemist"]),
    ]

    for floor, text, tags in contexts:
        print(f"  🎭 Floor {floor} | Build: {tags}")
        print(f"     Player: \"{text}\"\n")

        prose = director.narrate(floor, text, tags)
        print(f"  📜 Narrator ({config.MODEL_CHAT}):")
        print(f"     \"{prose}\"\n")

        score = judge_narrative(prose, floor, tags)
        icon = "✅" if score >= 80 else "❌"
        print(f"  📊 Narrative quality (LLM-judge): {score:.0f}/100 (threshold 80) {icon}")
        print()

    print(trace_url())
    print("  💡 Two contexts → two unique gothic narratives, scored by an LLM judge.")


# ── Phase 3 ──────────────────────────────────────────────────────────────────

def phase3_interrupt():
    header("SCENARIO 3 — When the AI Fails, You Choose (LangGraph interrupt)")

    import asyncio
    from langgraph.types import Command
    from app.agent.graph import build_graph, OPTION_FALLBACK

    async def _run():
        graph = build_graph()
        config = {"configurable": {"thread_id": "demo-interrupt-001"}}

        print("  🎭 Forcing compose failure (invalid enemy_id)…\n")

        attempts = {"n": 0}

        def broken_compose(tags, tier):
            attempts["n"] += 1
            print(f"     Attempt {attempts['n']}: compose_and_verify → 💥 raises")
            raise ValueError("simulated: LLM produced an invalid variant")

        director.compose_and_verify = broken_compose

        init = {
            "intent": "encounter_gen", "session_id": "demo",
            "seed": 42, "floor_index": 2, "room_index": 0,
            "tier": 1, "build_tags": ["brawler"],
        }
        result = await graph.ainvoke(init, config)

        snapshot = await graph.aget_state(config)
        pending = snapshot.values.get("pending_decision", {})
        print(f"\n  ⏸  LangGraph INTERRUPT — graph parked at wait_for_decision")
        print(f"     Prompt: {pending.get('prompt', 'N/A')}")
        for opt in pending.get("options", []):
            print(f"       → {opt['option_id']}: {opt['label']}")

        print(f"\n  🎭 Player chooses: {OPTION_FALLBACK}\n")

        director.compose_and_verify = original

        result = await graph.ainvoke(Command(resume=OPTION_FALLBACK), config)
        print(f"  → Graph resumed. fallback={result.get('fallback')}, last_decision={result.get('last_decision')}")

    original = director.compose_and_verify

    asyncio.run(_run())

    print(f"\n{trace_url()}")
    print("  💡 LangGraph interrupt() parked the run; Command(resume=...) continued")
    print("     from the same checkpoint. No state lost, no silent failure.")


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🗡️  Heirs of the Abyss — LangGraph + LangChain + LangSmith Showcase\n")

    phase1_composer()
    pause()
    phase2_narrator()
    pause()
    phase3_interrupt()

    header("Demo complete")
    print(f"  All LLM calls traced in LangSmith project: "
          f"{os.environ.get('LANGCHAIN_PROJECT', 'heirs-of-the-abyss-demo')}")
    print("  🔗 https://smith.langchain.com\n")
