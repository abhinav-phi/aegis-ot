---
tier: trusted
title: Playbook SPD-026 Staged Recovery and Restart
source: configs/kb/playbook_spd026.md
owner: AEGIS-OT Team
---
# SPD-026 — Staged Recovery and Restart

After an incident is resolved (closed reason: resolved), staged recovery may proceed. Each recovery step must be a separate mitigation plan revision with its own C1–C5 validation and human approval. Steps: (1) restore sensor readings to nominal via cross-check, (2) stabilize tank levels within operating range, (3) resume pump at minimum speed, (4) verify flow consistency, (5) return to normal setpoint. Any step that fails validation must be re-evaluated before proceeding. All recovery actions are logged to the audit trail. Do not skip steps.