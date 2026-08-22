"""Canonical enum vocabularies + SQL helper. Single source of truth for statuses."""
from __future__ import annotations

ROLES = ("admin", "analyst", "viewer")
SEVERITIES = ("low", "medium", "high", "critical")
INCIDENT_STATUSES = (
    "open", "analyzing", "awaiting_approval", "simulating",
    "rejected", "escalated", "closed",
)
CLOSED_REASONS = ("'resolved'", "'no_action'", "'escalated'")
VERDICTS = ("allow", "require_approval", "block", "escalate")
RISK_CLASSES = ("read", "write", "control", "forbidden")
TIERS = ("trusted", "public", "hostile")
APPROVAL_STATUSES = ("pending", "approved", "denied", "expired", "superseded")
ACTION_STATUSES = ("queued", "executed", "failed", "blocked", "invalid")  # CHG-DB-10 (+failed)
AGENT_RUN_STATUSES = ("running", "completed", "error", "interrupted")
PLAN_STATUSES = (
    # DEC-009: 'expired' removed; expiry escalates.
    "draft_for_validation", "validated", "approved", "executing",
    "executed", "rejected", "escalated", "superseded", "draft_only",
)
DATASET_RUN_STATUSES = ("pending", "running", "completed", "failed")
EVAL_RUN_STATUSES = ("pending", "running", "completed", "failed")
AGENT_VARIANTS = ("naive", "grounded", "grounded_validated")


def check_in(column: str, values: tuple[str, ...] | list[str]) -> str:
    """Build a `col IN (...)` SQL fragment for CHECK constraints."""
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"
