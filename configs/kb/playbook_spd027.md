---
tier: trusted
title: Playbook SPD-027 Invariant Re-Verification Before Control
source: configs/kb/playbook_spd027.md
owner: AEGIS-OT Team
---
# SPD-027 — Invariant Re-Verification Before Control

Before any control-class action is approved, the operator must re-verify all five plant invariants: R1 (tank level 0–100%), R2 (pump on implies flow > 0), R3 (open valve implies flow—if closed, flow near zero), R4 (level change rate ≤ 2%/s), R5 (flow within 0–15 m³/h). The invariant check is a read-only agent tool and does not require approval. A control action that contradicts a failed invariant automatically triggers a C5 invariant_conflict flag and escalates the plan. Invariant results must be cited in the mitigation plan evidence.