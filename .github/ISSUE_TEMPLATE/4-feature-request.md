---
name: ✨ Feature Request
about: Suggest a capability or research extension for AEGIS-OT
title: "[Feature]: "
labels: ["enhancement", "triage"]
assignees: []
---

## Problem / Motivation

<!-- What problem does this solve? For research proposals: what question does
it answer, and what is the baseline it improves on? -->

## Proposed Solution

<!-- What should happen? Be concrete: API shape, CLI command, UI panel,
validator behaviour, experiment definition, etc. -->

## Area

- [ ] Backend API (`app/api`)
- [ ] Core safety chain — validator / approvals / hash binding (`app/core`)
- [ ] Services — sandbox executor / tiered RAG / audit (`app/services`)
- [ ] Pipeline — detection / attribution / invariants (`pipeline`)
- [ ] Evaluation — experiments / attack suite (`eval`)
- [ ] Frontend dashboard (`frontend`)
- [ ] Infrastructure / tooling
- [ ] Documentation

## Safety Impact

<!-- Does this touch the safety chain? Be explicit. -->

- [ ] **No safety-chain interaction** — touches none of the components below.
- [ ] **Interacts with the safety chain** — list below which invariants are
      affected and how they remain enforced:
      - C1–C5 validator (deterministic C1–C4, per-check `deterministic` flag)
      - Approval workflow (distinct-approver, 24 h expiry escalation)
      - Plan hash binding (executed ≡ validated ≡ approved, SHA-256)
      - Sandbox-only execution (`SIMULATED` labeling, lease recovery)
      - Tiered RAG (hostile tier unreachable in production, INV-012)
      - Naive-variant gate (`draft_only` terminal, INV-010/R44)

<!-- If you checked the second box, explain in 2–4 sentences here. -->

## Alternatives Considered

<!-- Other approaches you evaluated and why this one is preferable. -->

## Additional Context

<!-- Links, papers, related experiments (EXP-01…EXP-09), prior art. -->
