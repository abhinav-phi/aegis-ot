---
tier: trusted
title: Playbook SPD-018 Pump Speed Spike Response
source: configs/kb/playbook_spd018.md
owner: AEGIS-OT Team
---
# SPD-018 — Pump Speed Spike Response

A sudden increase in pump P-101 speed with no corresponding setpoint change may indicate a supply pump compromise (T0862). The operator must FIRST verify the flow reading FIT-101 and tank level LIT-101 cross-correlation. If flow and level do not match the pump speed, flag the sensor readings as suspect. Do NOT reduce pump speed — that is a control-class action requiring human approval. Escalate if the spike persists across two consecutive windows.