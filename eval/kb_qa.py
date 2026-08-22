"""RAG-04 retrieval QA: 20 canned queries with expected-source ground truth."""
from __future__ import annotations

CANNED_QUERIES: list[dict] = [
    {"q": "high level alarm response procedure", "expect_source_contains": ["SPD-017", "playbook"]},
    {"q": "pump speed reduction steps", "expect_source_contains": ["SPD-017"]},
    {"q": "level sensor false reading verification", "expect_source_contains": ["SPD-017"]},
    {"q": "T0875 technique description", "expect_source_contains": ["mitre"]},
    {"q": "supply pump compromise technique", "expect_source_contains": ["mitre"]},
    {"q": "process manipulation ATT&CK ICS", "expect_source_contains": ["mitre"]},
    {"q": "valve flow consistency check", "expect_source_contains": ["plant-manual", "invariant"]},
    {"q": "tank level operating range", "expect_source_contains": ["plant-manual"]},
    {"q": "MV-501 valve purpose", "expect_source_contains": ["plant-manual"]},
    {"q": "incident response first steps OT", "expect_source_contains": ["playbook"]},
    {"q": "when to escalate an incident", "expect_source_contains": ["playbook"]},
    {"q": "who approves control actions", "expect_source_contains": ["playbook", "policy"]},
    {"q": "sandbox execution meaning", "expect_source_contains": ["plant-manual", "policy"]},
    {"q": "LIT-101 sensor semantics", "expect_source_contains": ["plant-manual"]},
    {"q": "FIT-101 flow range", "expect_source_contains": ["plant-manual"]},
    {"q": "maintenance ticket workflow", "expect_source_contains": ["playbook"]},
    {"q": "invariant R4 meaning", "expect_source_contains": ["plant-manual", "invariant"]},
    {"q": "unauthorized command message detection", "expect_source_contains": ["mitre"]},
    {"q": "water treatment stage 6", "expect_source_contains": ["plant-manual"]},
    {"q": "verify invariants before action", "expect_source_contains": ["playbook"]},
]

assert len(CANNED_QUERIES) == 20


def evaluate_retriever(retrieve_fn) -> dict:
    """hit-rate@5 and MRR against expected source substrings."""
    hits, rr = 0, []
    for item in CANNED_QUERIES:
        res = retrieve_fn(item["q"])
        rank = 0
        for pos, cite in enumerate((res.get("citations") or [])[:5], start=1):
            src = str(cite.get("source", "")).lower()
            if any(exp.lower() in src for exp in item["expect_source_contains"]):
                rank = pos
                break
        if rank:
            hits += 1
            rr.append(1.0 / rank)
        else:
            rr.append(0.0)
    return {"hit_rate_at_5": hits / len(CANNED_QUERIES),
            "mrr": sum(rr) / len(rr), "n_queries": len(CANNED_QUERIES)}
