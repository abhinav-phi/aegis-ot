---
tier: trusted
title: Playbook SPD-022 Unauthorized Stop Response
source: configs/kb/playbook_spd022.md
owner: AEGIS-OT Team
---
# SPD-022 — Unauthorized Stop Response

An equipment stop command that does not match a known procedure (T0838 Unauthorized Stop) must be treated as adversarial. Verify the command source and timestamp. If the stop targets a critical pump or valve, do NOT re-start without a full validated mitigation plan. Re-start is a control-class action. Capture the stop command audit trail and telemetry before/after the event. Invariant R3 (valve-flow consistency) may fail if a valve closes unexpectedly — record the violation.