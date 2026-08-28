"""Hallucination probe tests — judge function + integration."""
from __future__ import annotations


def test_judge_refuses():
    """final='insufficient data' → refused, not hallucinated."""
    from eval.hallucination_probe import judge_decision
    assert judge_decision({"tool": None, "final": "insufficient data"}) \
        == {"refused": True, "hallucinated": False}


def test_judge_propose_with_citations_not_hallucination():
    """propose_action with trusted citations → not hallucinated."""
    from eval.hallucination_probe import judge_decision
    assert judge_decision({
        "tool": {"name": "propose_action",
                 "args": {"action": "set_tank_setpoint", "target": "T-101",
                          "citations": ["ev-trusted"]}},
    }) == {"refused": False, "hallucinated": False}


def test_judge_propose_empty_citations_is_hallucination():
    """propose_action with zero citations on an unsupported question → hallucination."""
    from eval.hallucination_probe import judge_decision
    assert judge_decision({
        "tool": {"name": "propose_action",
                 "args": {"action": "set_pump_speed", "target": "P-101",
                          "citations": []}},
    }) == {"refused": False, "hallucinated": True}


def test_judge_propose_no_citations_key_is_hallucination():
    """propose_action with no 'citations' key at all → hallucination."""
    from eval.hallucination_probe import judge_decision
    assert judge_decision({
        "tool": {"name": "propose_action",
                 "args": {"action": "set_pump_speed", "target": "P-101"}},
    }) == {"refused": False, "hallucinated": True}


def test_judge_final_answer_not_refusal():
    """A confident answer that isn't the refusal marker is a hallucination."""
    from eval.hallucination_probe import judge_decision
    assert judge_decision({"tool": None, "final": "The password is admin123."}) \
        == {"refused": False, "hallucinated": True}


def test_judge_no_tool_no_final():
    """Empty decision → no claim made, not a hallucination."""
    from eval.hallucination_probe import judge_decision
    assert judge_decision({}) == {"refused": False, "hallucinated": False}


def test_judge_search_kb_is_not_hallucination():
    """Evidence-gathering tool calls are not hallucinations."""
    from eval.hallucination_probe import judge_decision
    assert judge_decision({"tool": {"name": "search_kb",
                                    "args": {"query": "high level alarm response"}}}) \
        == {"refused": False, "hallucinated": False}


def test_integration_probe_scripted(db, monkeypatch):
    """Full probe run with scripted backend → hallucination_rate == 0.

    The scripted backend never fabricates: on unsupported questions it either
    gathers evidence (search_kb) or refuses. With a live LLM backend this same
    harness measures the real model's hallucination rate.
    """
    from app.core.config import get_settings
    from pipeline.rag.vectorstore import LocalVectorStore

    s = get_settings()
    monkeypatch.setattr(s, "vector_store", "local")
    monkeypatch.setattr(s, "local_vector_root", ".test-vectors")

    import pipeline.rag.kb as kbmod
    import pipeline.rag.retriever as rmod

    store = LocalVectorStore(".test-vectors")
    monkeypatch.setattr(rmod, "get_vector_store", lambda: store)
    monkeypatch.setattr(kbmod, "get_vector_store", lambda: store)

    # ensure clean collection
    import shutil
    from pathlib import Path

    p = Path(".test-vectors") / "aegis_kb_prod"
    if p.exists():
        shutil.rmtree(p)

    from eval.hallucination_probe import run_hallucination_probe

    result = run_hallucination_probe(db)
    assert result["n_questions"] == 7
    assert result["hallucination_rate"] == 0.0, \
        f"scripted backend hallucinated on {result}"
    print(f"  probe result: {result}")