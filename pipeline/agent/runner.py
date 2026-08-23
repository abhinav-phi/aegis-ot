"""Single-agent ReAct runner (DEC-005/006). Terminates at draft materialization;
approval/execution operate purely on DB artifacts afterwards.

Max-step behavior (AGENT-002): forced finalize with evidence-so-far draft,
STEP_LIMIT_REACHED marker, run completed — never a silent hang.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.canonical import steps_hash
from app.core.config import get_settings
from app.db.models import AgentMessage, AgentRun, Incident, MitigationPlan
from app.services.state import agent_run_transition
from pipeline.agent.llm import get_llm
from pipeline.agent.prompts import SYSTEM_GROUNDED, SYSTEM_NAIVE, build_transcript
from pipeline.agent.tools import ToolContext, dispatch


def run_agent(db: Session, *, run_id, incident_id, dataset_run_id, variant: str,
              mode: str = "production", created_by=None) -> dict:
    """Execute one agent run synchronously (worker/API background task).

    Caller is responsible for the DB transaction and lease bookkeeping.
    """
    llm = get_llm()
    max_steps = get_settings().agent_max_steps
    ctx = ToolContext(db=db, incident_id=str(incident_id),
                      dataset_run_id=str(dataset_run_id), mode=mode)
    system = SYSTEM_NAIVE if variant == "naive" else SYSTEM_GROUNDED

    def record(role: str, payload: dict, tool_name: str | None = None) -> None:
        # AGENT-001 stale-writer guard: after reaper/interrupt, no further
        # writes from this worker may land.
        from app.services.agent_service import assert_run_active

        assert_run_active(db, run_id)
        db.add(AgentMessage(agent_run_id=run_id, role=role, tool_name=tool_name,
                            payload=payload))
        db.flush()

    step_limit_reached = False
    final_text = None
    step_no = 0
    while step_no < max_steps:
        step_no += 1
        from app.services.agent_service import HEARTBEAT_S, renew_lease

        renew_lease(db, run_id, seconds=HEARTBEAT_S)
        db.query(AgentRun).filter(AgentRun.id == run_id).update(
            {"steps": step_no}, synchronize_session=False)
        transcript = build_transcript(ctx, step_no)
        try:
            decision = llm.decide(system, transcript)
        except Exception as exc:  # LLM failure: bounded recovery (AppFlow §5)
            record("assistant", {"error": f"llm_error:{exc}", "step": step_no})
            decision = {"thought": "", "tool": None, "final": "insufficient data"}

        record("assistant", {"thought": decision.get("thought", ""),
                             "step": step_no})
        tool = decision.get("tool")
        if tool:
            try:
                result = dispatch(ctx, tool["name"], tool.get("args") or {})
            except Exception as exc:  # tool failure: record + retry once
                record("tool", {"error": str(exc), "tool": tool["name"]},
                       tool_name=tool["name"])
                try:
                    result = dispatch(ctx, tool["name"], tool.get("args") or {})
                except Exception as exc2:
                    record("tool", {"error": f"retry_failed:{exc2}",
                                    "tool": tool["name"]}, tool_name=tool["name"])
                    continue
            record("tool", {"result": _compact(result), "tool": tool["name"]},
                   tool_name=tool["name"])
        if decision.get("final"):
            final_text = decision["final"]
            break
    else:
        step_limit_reached = True
        final_text = final_text or "insufficient data"

    status = "completed"
    plan_id = None
    if ctx.proposed:
        plan_id = _materialize_draft(
            db, run_id=run_id, incident_id=incident_id, variant=variant,
            proposed=ctx.proposed, index=ctx.index,
            step_limit_reached=step_limit_reached,
        )
    elif step_limit_reached:
        record("assistant", {"marker": "STEP_LIMIT_REACHED", "final": final_text})

    ended = dt.datetime.now(dt.UTC)
    # Final transcript entry MUST land while the run is still `running` —
    # AGENT-001 rejects writes after the completion transition below.
    record("assistant", {"final": final_text, "step_limit_reached": step_limit_reached,
                         "variant": variant})
    agent_run_transition(db, run_id, "running", status,
                         extra={"ended_at": ended, "lease_until": None})
    return {"run_id": str(run_id), "status": status, "plan_id": plan_id,
            "steps": step_no, "step_limit_reached": step_limit_reached}


def _compact(result: dict) -> dict:
    out = {}
    for k, v in result.items():
        out[k] = v if not isinstance(v, (dict, list)) else str(v)[:300]
    return out


def _materialize_draft(db: Session, *, run_id, incident_id, variant, proposed,
                       index, step_limit_reached: bool) -> str:
    """Immutable plan revision insert (DEC-001). naive ⇒ draft_only (INV-010)."""
    from app.core.canonical import canonical_bytes

    steps = [dict(s) for s in proposed]
    h = steps_hash(steps)
    run = db.get(AgentRun, run_id)
    # Revisions are per agent run: never collide with an existing revision
    # (UNIQUE(agent_run_id, revision_no)); amendments continue the chain.
    latest = db.execute(
        select(MitigationPlan.revision_no)
        .where(MitigationPlan.agent_run_id == run_id)
        .order_by(MitigationPlan.revision_no.desc()).limit(1)
    ).scalar_one_or_none()
    plan = MitigationPlan(
        incident_id=incident_id, agent_run_id=run_id,
        revision_no=(latest or 0) + 1,
        steps=steps, steps_hash=h,
        canonical_bytes=canonical_bytes(steps),          # HASH-001
        revision_created_by=run.created_by if run else None,  # SEC-002
        status="draft_only" if variant == "naive" else "draft_for_validation",
    )
    db.add(plan)
    db.flush()
    if step_limit_reached:
        db.add(AgentMessage(agent_run_id=run_id, role="assistant",
                            payload={"marker": "STEP_LIMIT_REACHED",
                                     "plan_id": str(plan.id)}))
        db.flush()
    return str(plan.id)


def create_run(db: Session, *, incident: Incident, variant: str, created_by=None,
               model_name: str = "qwen2.5:7b-instruct") -> AgentRun:
    """DEC-005: explicit creation; DB partial-unique index enforces ≤1 active."""
    config_hash = uuid.uuid5(uuid.NAMESPACE_URL,
                             f"{variant}|{model_name}|{get_settings().agent_max_steps}").hex
    run = AgentRun(incident_id=incident.id, model_name=model_name, variant=variant,
                   status="running", config_hash=config_hash, created_by=created_by)
    db.add(run)
    db.flush()
    return run


def get_run_or_404(db: Session, run_id) -> AgentRun:
    from app.core.exceptions import NotFoundError

    run = db.get(AgentRun, run_id)
    if run is None:
        raise NotFoundError("agent_run_not_found")
    return run


def list_runs(db: Session, incident_id) -> list[AgentRun]:
    return list(db.execute(select(AgentRun).where(AgentRun.incident_id == incident_id)
                           .order_by(AgentRun.started_at)).scalars())
