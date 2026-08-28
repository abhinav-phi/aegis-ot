---
tier: trusted
title: Playbook SPD-025 Incident Triage
source: configs/kb/playbook_spd025.md
owner: AEGIS-OT Team
---
# SPD-025 — Incident Triage

First 15 minutes of an incident: (1) confirm the incident severity from the max anomaly score, (2) review the sensor attribution bars to identify which channels contributed, (3) read the explanation hypothesis and invariant check results, (4) check the MITRE ATT&CK for ICS technique mapping (TINTEL-01), (5) determine if the incident requires an agent run or can be closed as no_action. Do NOT skip to mitigation before triage. Triage is read-only and does not require approval. If the incident involves a control-class action, mark it for agent review.