---
tier: trusted
title: Playbook SPD-020 Flow Sensor Zeroing Response
source: configs/kb/playbook_spd020.md
owner: AEGIS-OT Team
---
# SPD-020 — Flow Sensor Zeroing Response

If FIT-101 reports zero while pump P-101 is running and valve MV-201 is open, the flow reading is likely spoofed (numeric sensor attack). Do NOT trust the zero reading. Cross-check with tank level LIT-101 rate of change and pump speed. A rising level with zero reported flow confirms spoofing. Record the discrepancy as evidence. Invariant checks R2 (pump-flow consistency) and R5 (flow range) must be re-evaluated. No control action is warranted until the true flow is determined.