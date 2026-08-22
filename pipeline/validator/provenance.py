"""C1 provenance check: exact evidence-ID binding (VAL-007).

Every step must cite evidence IDs that exist in the run's EvidenceIndex. Tier
semantics: hostile support counts as ZERO trusted; public-only support is
flagged; a citation-free step can only be allowed if its action class permits
citation-free reads.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProvenanceResult:
    status: str  # pass | flag_missing_citations | flag_public_only | flag_hostile
    trusted_ids: list[str]
    detail: str


def check_provenance(step: dict, index) -> ProvenanceResult:
    citations = step.get("citations") or []
    unknown = [c for c in citations if c not in index]
    if unknown:
        return ProvenanceResult("flag_missing_citations", [],
                                f"unknown_evidence_ids:{unknown[:5]}")
    tiers = [index[c]["tier"] for c in citations]
    trusted = [c for c, t in zip(citations, tiers) if t == "trusted"]
    if any(t == "hostile" for t in tiers):
        return ProvenanceResult(
            "flag_hostile" if trusted else "block_hostile_only",
            trusted,
            "hostile_tier_cited",
        )
    if not citations:
        return ProvenanceResult("flag_missing_citations", [], "no_citations")
    if not trusted:
        return ProvenanceResult("flag_public_only", [], "public_only_support")
    return ProvenanceResult("pass", trusted, "trusted_provenance")


def has_trusted_support(step: dict, index) -> bool:
    return bool([c for c in (step.get("citations") or [])
                 if c in index and index[c]["tier"] == "trusted"])
