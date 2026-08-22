---
tier: trusted
title: Playbook SPD-017 High Level Alarm
source: configs/kb/playbook_spd017.md
---
# SPD-017 — High Level Alarm Response

On a high level alarm, the operator FIRST verifies whether the level sensor
(LIT-101) is producing a false reading by cross-checking flow (FIT-101) and
pump status. Pump speed reduction is a SECONDARY action and requires human
approval. All invariants (tank range, pump-flow consistency, valve-flow
consistency, level rate, flow range) must be re-checked before any control
action. Escalate to the incident administrator if verification fails twice.
