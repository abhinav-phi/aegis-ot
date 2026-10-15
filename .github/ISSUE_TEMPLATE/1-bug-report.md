---
name: 🐛 Bug Report
about: Report something that behaves incorrectly or unexpectedly
title: "[Bug]: "
labels: ["bug", "triage"]
assignees: []
---

<!-- Read this first:
AEGIS-OT is a sandbox-only research platform. It never connects to real
SCADA/PLC/plant infrastructure. Issues describing connections to operational
OT networks will be closed. -->

## Description

<!-- A clear and concise description of what the bug is. -->

## Component / Area

<!-- Which part does this affect? Check all that apply. -->

- [ ] Backend API (`app/api`)
- [ ] Core safety chain — validator / approvals / hash binding (`app/core`)
- [ ] Services — sandbox executor / tiered RAG / audit (`app/services`)
- [ ] Pipeline — detection / attribution / invariants (`pipeline`)
- [ ] Evaluation — experiments / attack suite (`eval`)
- [ ] Frontend dashboard (`frontend`)
- [ ] Docker / setup / tooling
- [ ] Documentation

## Steps to Reproduce

<!-- Minimal, numbered steps. For eval mismatches include the experiment ID
(e.g. EXP-03) and the config hash reported in the run output. -->

1.
2.
3.

## Expected Behaviour

<!-- What did you expect to happen? -->

## Actual Behaviour

<!-- What actually happened? Include error messages. -->

## Logs / Evidence

<details>
<summary>Log output</summary>

```
<!-- Paste relevant logs here. Redact secrets and tokens. -->
```

</details>

## Environment

- OS: <!-- e.g. Windows 11, Ubuntu 22.04, macOS 14 -->
- Python version: <!-- e.g. 3.11.9 -->
- Node version (if frontend): <!-- e.g. 20.11.0 -->
- Install method: <!-- make setup / MANUAL_SETUP.md / docker compose -->
- Run mode: <!-- offline fixture / docker compose / licensed dataset (manual) -->

## Additional Context

<!-- Screenshots (dashboard issues), config snippets, or anything else.
Sanity checks:
- [ ] I have searched existing issues for duplicates.
- [ ] I am running against the sandbox / offline fixture — no real OT systems.
-->
