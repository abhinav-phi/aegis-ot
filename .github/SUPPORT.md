# Support

Thanks for your interest in AEGIS-OT! This is a solo-maintained research
prototype, so support is best-effort — the resources below will answer most
questions faster than filing an issue.

> ⚠️ **Safety boundary:** AEGIS-OT never connects to real SCADA/PLC/plant
> infrastructure. It is a research instrument for sandbox environments only.

## Documentation

Start here, in this order:

1. **[README](../README.md)** — what the project is, architecture, features,
   safety model, quick start.
2. **[MANUAL_SETUP.md](../MANUAL_SETUP.md)** — from-scratch setup without
   Make: every service (PostgreSQL, MinIO, Chroma, Ollama, MLflow), every
   env var, and the licensed-dataset (SWaT / WUSTL-IIoT-2021) procedure.
3. **[docs/](../docs)** — the full research documentation set:
   - [PRD](../docs/1.%20PRD.md) — problem, research question, scope
   - [TechSpec](../docs/2.%20TechSpec.md) — component design
   - [AppFlow](../docs/3.%20AppFlow.md) — end-to-end flows
   - [Design](../docs/4.%20Design.md) — dashboard design
   - [Schema](../docs/5.%20Schema.md) — data model
   - [Implementation Plan](../docs/6.%20ImplementationPlan.md)
   - [Tracker](../docs/7.%20Tracker.md) — step-by-step build record with evidence
   - [Rules](../docs/8.%20Rules.md) — invariants and safety rules (INV-*, R*)
4. **[CHANGELOG.md](../CHANGELOG.md)** — what changed in each version.

## Common Tasks

| Task | Command |
| --- | --- |
| Full setup (Python + services + migrate + seed) | `make setup` |
| Generate synthetic fixture | `make fixture` |
| Start API (dev, reload on :8000) | `make api` |
| Start worker | `make worker` |
| Run all tests | `make test` |
| Lint / typecheck | `make lint` / `make typecheck` |
| Run demo | `make demo` |
| Run full experiment matrix | `make eval` |

Frontend: `cd frontend && npm ci && npm run dev` (Vite on :5173).

Full dockerized stack: `docker compose up -d --build`
(app :8000 · frontend :5173 · MLflow :5001).

## Getting Help

- **Questions / usage / setup help:** open a thread in
  [GitHub Discussions](https://github.com/abhinav-phi/aegis-ot/discussions).
- **Bug:** open a
  [bug report](ISSUE_TEMPLATE/1-bug-report.md) with your environment details
  and the experiment/config hash if it's a pipeline/eval mismatch.
- **Security vulnerability:** do **not** file an issue — follow the
  [Security Policy](SECURITY.md) (private disclosure only).
- **Feature / research proposal:** use the
  [feature request template](ISSUE_TEMPLATE/4-feature-request.md).

## Response Expectations

This is a best-effort, spare-time research project. There are no SLAs —
but issues with a minimal reproduction, environment info, and logs get
attention fastest.
