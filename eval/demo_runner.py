"""Demo orchestration CLI (`make demo` → `python -m eval.demo_runner`).

Runs the 7-step "Attack the Agent" narrative offline against the configured
database using the deterministic scripted LLM backend. Every output row is
labeled SIMULATED/FIXTURE (R39/R40); no number printed here is a measured
model result (R41 — offline backend is a stand-in, recorded as such).
"""
from __future__ import annotations

import argparse
import json


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description="AEGIS-OT offline demo runner")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    from app.db.session import SessionLocal, ensure_lite_schema
    from app.services.demo_service import run_demo

    ensure_lite_schema()
    with SessionLocal() as db:
        result = run_demo(db)
        db.commit()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    print("AEGIS-OT Attack-the-Agent demo (SIMULATED / FIXTURE)")
    for step in result["steps"]:
        print(f"  · {step}")
    print(f"naive:    {result['naive']}")
    print(f"hardened: {result['hardened']}")
    print(f"labels:   {result['labels']} — {result['note']}")


if __name__ == "__main__":
    main()
