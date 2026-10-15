# Contributing to AEGIS-OT

First off, thank you for considering a contribution. 🙌

AEGIS-OT is a research-grade OT/ICS decision-support platform whose entire
purpose is a **measurable safety chain**: attribution-grounded reasoning,
a deterministic C1–C5 validator, hash-bound human approval, and sandbox-only
execution. Because of that, contributions are held to a higher bar than a
typical web app — a change that improves convenience but weakens a documented
safety invariant will be rejected, no matter how clean the code is.

> ⚠️ **Safety boundary:** the platform never connects to real SCADA/PLC/plant
> infrastructure. Do not submit code, datasets, or issues describing connections
> to operational OT networks.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Project Status](#project-status)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features & Enhancements](#suggesting-features--enhancements)
  - [Security Vulnerabilities](#security-vulnerabilities)
  - [Research & Evaluation Contributions](#research--evaluation-contributions)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Style Guidelines](#style-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Safety-Critical Change Review](#safety-critical-change-review)
- [License](#license)

## Code of Conduct

By participating, you are expected to uphold the
[Code of Conduct](CODE_OF_CONDUCT.md). Report unacceptable behaviour to the
maintainer via the channels listed there.

## Project Status

AEGIS-OT is a solo-maintained research prototype. The full pipeline, safety
chain, evaluation framework, and dashboard are implemented and verified
offline on a committed synthetic mini-fixture (78 backend tests, frontend
builds clean). Licensed datasets (SWaT / WUSTL-IIoT-2021) are handled as
manual, hash-pinned steps — see [Manual Setup](../MANUAL_SETUP.md).

Expect honest scoping in responses: contributions that keep the offline
fixture path green are the fastest to merge.

## How Can I Contribute?

### Reporting Bugs

- Open a GitHub issue using the
  [bug report template](ISSUE_TEMPLATE/1-bug-report.md) (auto-selected when
  you create an issue).
- Include: what you ran, expected vs actual behaviour, relevant log output,
  and your OS/Python/Docker versions.
- For pipeline/eval mismatches, include the experiment ID (e.g. `EXP-03`) and
  the config hash reported in the run output.

### Suggesting Features & Enhancements

- Open an issue using the
  [feature request template](ISSUE_TEMPLATE/4-feature-request.md).
- Proposals that touch the safety chain (validator, approvals, hash binding,
  sandbox executor, tiered RAG) must state which invariants are preserved and
  how — see [Safety-Critical Change Review](#safety-critical-change-review).

### Security Vulnerabilities

**Do not open a public issue.** Follow the
[Security Policy](SECURITY.md) — use private vulnerability reporting or
email the maintainer.

### Research & Evaluation Contributions

This is the highest-value area for a research project. Especially welcome:

- New adversarial injection fixtures for the F1–F7 families (or a reasoned new
  family), following the fixture conventions in `eval/attack_suite/`.
- Detector variants benchmarked against the committed fixture with honest
  skip/mismatch reporting.
- Experiment-matrix extensions (EXP-01…EXP-09) with reproducible config hashes.
- Literature-grounded proposals with clear baselines.

## Development Setup

Prerequisites: Python 3.11+, Node.js 20+, Docker (with Compose), Git.

```bash
git clone https://github.com/abhinav-phi/aegis-ot.git
cd aegis-ot

# 1. Python environment + services (postgres, minio, chroma, ollama, mlflow)
make setup

# 2. Synthetic fixture (data/fixtures/swat_mini.csv)
make fixture
```

Frontend (separate process):

```bash
cd frontend
npm ci
npm run dev   # Vite dev server on :5173
```

Full environment-variable reference: [`.env.example`](../.env.example).
For a from-scratch, no-Make walkthrough see
[MANUAL_SETUP.md](../MANUAL_SETUP.md).

## Development Workflow

```bash
make test        # pytest -q            (must be green before every PR)
make lint        # ruff check app pipeline eval tests
make typecheck   # mypy app pipeline    (best-effort; regressions are blocking)
```

- Backend: FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2. Migrations go in
  `app/db/` via Alembic — never edit the DB by hand.
- Frontend: React 18 + TypeScript (strict) + Vite + Tailwind. `npm run build`
  (which runs `tsc`) must pass.
- Tests live in `tests/` by area (`unit/`, `security/`, `state_machine/`,
  `validator/`, `rag/`, `concurrency/`, `e2e/`). New behaviour needs a test;
  bug fixes need a regression test.
- CI must pass on your PR: ruff + pytest on the backend, `tsc && vite build`
  on the frontend.

## Style Guidelines

- Python: line length 100, target py311, formatted/linted with ruff.
  The `B008` exemption for `app/api/**` and `app/core/**` is intentional —
  FastAPI's `Depends(...)` pattern. Do not widen it.
- Type hints for all public functions; mypy runs over `app` and `pipeline`.
- Docstrings for anything in the safety chain — validator checks (C1–C5),
  approval state machine, hash binding, sandbox executor, tiered retriever —
  should state the invariant being enforced, not just the mechanics.
- TypeScript: strict mode is on; no `any` without a justification comment.
- Config files (`configs/*.yaml`) are load-bearing: detector bounds, invariant
  bounds, and experiment definitions are keyed by committed hashes. Changing
  one is a research result — document the intent in the PR.

## Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
feat(validator): add risk-class check for write-class commands
fix(rag): record TIER_DENIED on hostile-tier retrieval attempts
docs(security): expand sandbox scope section
test(state_machine): cover 24h approval expiry escalation
refactor(worker): extract lease renewal helper
chore(deps): bump fastapi to 0.115
```

Rules of thumb:

- Present tense, imperative mood (`add`, not `added`/`adds`).
- One logical change per commit; keep safety-chain changes in isolated commits.
- Reference issues in the body (`Refs #12`, `Fixes #7`).

## Pull Request Process

1. Fork / branch from `main`: `feat/<topic>`, `fix/<topic>`, or `eval/<topic>`.
2. Keep the offline fixture path green: `make test`, `make lint` before
   pushing.
3. Fill in the [PR template](pull_request_template.md) — including the
   safety-impact declaration.
4. If the PR touches DB state, include an Alembic migration and note any
   backfill behaviour.
5. Link related issues and experiments (e.g. `EXP-05`).
6. One review round is normal; safety-chain PRs may take longer.

## Safety-Critical Change Review

The following are the research core. PRs here get extra scrutiny:

| Component | Location | Invariants that must hold |
| --- | --- | --- |
| C1–C5 validator | `app/core/` | C1–C4 stay fully deterministic; `deterministic` flag recorded per check |
| Approval workflow | `app/core/` | distinct-approver for control class; 24 h expiry escalates, never silently denies |
| Plan hash binding | `app/core/`, `app/db/` | `steps_hash` immutable; executed ≡ validated ≡ approved (SHA-256) |
| Sandbox executor | `app/services/` | no real-IO path; all actions labeled `SIMULATED`; lease recovery escalates |
| Tiered retriever | `app/services/` | hostile tier unreachable in production (INV-012); `TIER_DENIED` recorded |
| Naive-variant gate | `app/core/`, `app/services/` | `variant='naive'` terminal at `draft_only` (INV-010/R44) |

If your change interacts with any row above, the PR description must contain a
short **Safety Impact** section: which invariants are touched, why they still
hold, and which tests cover that. When in doubt, open an issue first.

## License

By contributing, you agree that your contributions will be licensed under the
[GPL-3.0 License](../LICENSE) that covers this project.
