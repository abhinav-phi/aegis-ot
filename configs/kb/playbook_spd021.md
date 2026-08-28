---
tier: trusted
title: Playbook SPD-021 Level Sensor Spoofing Detection
source: configs/kb/playbook_spd021.md
owner: AEGIS-OT Team
---
# SPD-021 — Level Sensor Spoofing Detection

A level sensor LIT-101 that reports a constant nominal value while pump and flow readings indicate change is likely being spoofed (pinned sensor attack). The operator should compare the level reading against the cumulative flow balance (integral of FIT-101 minus outflows). If the balance differs from LIT-101 by more than 5% of tank range, flag the sensor as suspect. Invariant R1 (tank level range) will pass, but R4 (level rate) will show zero change contradicting the mass balance. Record the mismatch as evidence and escalate for maintenance.