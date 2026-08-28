---
tier: trusted
title: Playbook SPD-019 Valve Position Manipulation
source: configs/kb/playbook_spd019.md
owner: AEGIS-OT Team
---
# SPD-019 — Valve Position Manipulation

If MV-201 or MV-501 report an unexpected position (open when should be closed or vice versa), suspect an unauthorized command message (T0875) or unauthorized stop (T0838). Cross-check the valve state against the flow meter immediately downstream. A closed valve with non-zero flow indicates a sensor fault or instrumentation bypass. Record the valve position, timestamp, and flow reading as evidence. Any corrective action (open/close) requires a validated mitigation plan and human approval.