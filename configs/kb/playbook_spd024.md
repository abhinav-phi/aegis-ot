---
tier: trusted
title: Playbook SPD-024 Escalation Criteria
source: configs/kb/playbook_spd024.md
owner: AEGIS-OT Team
---
# SPD-024 — Escalation Criteria

An incident must be escalated to admin review when: (1) the C5 consistency check fails on two consecutive validations against the same incident, (2) an approval request expires (24 h) without resolution, (3) the sandbox reports a step failure during execution, or (4) the analyst explicitly requests escalation. Escalated incidents are locked for admin resolution only. The escalation path is: incident status → escalated, admin notified via audit trail, plan expires to new revision. This is not a silent deny — escalation preserves the option to re-validate.