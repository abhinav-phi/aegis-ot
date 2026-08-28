---
tier: trusted
title: Playbook SPD-023 Evidence Preservation
source: configs/kb/playbook_spd023.md
owner: AEGIS-OT Team
---
# SPD-023 — Evidence Preservation

Before any mitigation action, the operator must ensure the incident telemetry, agent messages, validator results, and approval records are committed to the immutable audit log. Snapshots of the plant state (all sensor readings, pump speeds, valve positions, tank levels) should be recorded. The capture is a read-only action (risk class: read) and does not require approval. Evidence preservation is the first step in every incident response workflow. Preserved data supports attribution and post-incident review.