# AEGIS-OT

> Research-grade OT/ICS **decision-support** platform: attribute cyber-physical anomalies, ground an LLM incident-response agent in cited evidence, and gate every mitigation behind a deterministic C1–C5 validator, human approval, and a sandbox simulator.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![React](https://img.shields.io/badge/frontend-React%2018%20%7C%20TS%20%7C%20Vite-61dafb)
![PostgreSQL](https://img.shields.io/badge/storage-PostgreSQL%2016-336791)
![License](https://img.shields.io/badge/license-GPL--3.0-yellow)

**Documentation** · [PRD](../1.%20PRD.md) · [TechSpec](../2.%20TechSpec.md) · [AppFlow](../3.%20AppFlow.md) · [Design](../4.%20Design.md) · [Schema](../5.%20Schema.md) · [Implementation Plan](../6.%20ImplementationPlan.md) · [Tracker](../7.%20Tracker.md) · [Rules](../8.%20Rules.md) · [Manual Setup](MANUAL_SETUP.md)

> ⚠️ **Safety boundary:** AEGIS-OT never connects to, reads from, or controls real SCADA/PLC/plant infrastructure. The pipeline's terminal executor is a pure-Python **sandbox simulator**; every simulated action is labeled `SIMULATED`. This is a research instrument, not a production product.

---

## Table of Contents

- [About](#about)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Security Model](#security-model)
- [Research & Evaluation](#research--evaluation)
- [Running Tests](#running-tests)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## About

OT/ICS defenders can detect anomalies faster than they can safely *respond* to them. LLM-based responders promise help, but 2025–26 log-substrate injection research shows telemetry content itself is attacker-controlled input — and no OT/ICS agent benchmark exists to measure whether such an agent is safe.

AEGIS-OT answers one research question (**RQ1**: *can an LLM incident-response agent be made trustworthy under adversarial inputs?*) with a measurable safety intervention: attribution-grounded explanations feed a single ReAct planner whose proposed mitigations must pass five deterministic validator checks (C1–C5), obtain **human approval bound to the exact plan hash**, and execute **only** inside a labeled plant simulator. An adversarial injection suite (families F1–F7) measures attack-surface reduction against a deliberately naive agent variant.

Status: the full pipeline, safety chain, evaluation framework, and dashboard are implemented and verified offline on a committed synthetic mini-fixture (78 backend tests green, frontend builds clean). Licensed-dataset runs (SWaT/WUSTL-IIoT-2021) remain manual, hash-pinned steps — see [Manual Setup](MANUAL_SETUP.md).

## Features

All claims below are backed by code and tests — see [Tracker](../7.%20Tracker.md) Step 8 record for evidence.

**Detection & explainability**
- **Isolation Forest baseline** on frozen per-window statistics (`pipeline/detect/iso_forest.py`)
- **TCN-AE proposed detector** — dilated causal-conv autoencoder with per-channel residual decomposition (torch optional; honest skip recorded when absent)
- **Sensor attribution** — contribution % with deterministic tie-breaks, low-confidence floor (`pipeline/detect/scoring.py`)
- **Physics invariants** — 5 declarative SWaT-style rules with config-traced bounds (`configs/invariants.yaml`)
- **Hypothesis-only explanations** — NL template consuming structured attribution + invariant outcomes exclusively; carries no execution authority

**Agentic reasoning**
- **Single ReAct planner** (deliberately no multi-agent swarm) with read-mostly tools: `query_latest`, `query_history`, `search_kb`, `check_invariant`, `propose_action`
- **Grounding contract** — evidence-cited answers or explicit *"insufficient data"*
- **Naive variant isolation** — `variant='naive'` plans are terminal at `draft_only`: never validated into the approval path, never executed (INV-010/R44)

**Safety chain (the research core)**
- **C1–C5 validator** — provenance → allowlist → pattern filter → risk class → consistency; C1–C4 fully deterministic, every check records its `deterministic` flag
- **Immutable plan revisions** — DB trigger + ORM listener lock `steps_hash`; amendments create revision N+1 and supersede prior approvals in the same transaction
- **SHA-256 triple binding** — executed ≡ validated ≡ approved content; mismatch ⇒ hard `EXEC_HASH_MISMATCH` block
- **Approval workflow** — pending → approve/deny/amend; distinct-approver enforcement for control-class; 24 h expiry auto-escalates (never silent-denies)
- **Sandbox-only execution** — 6-stage SWaT-style surrogate plant; idempotent step resume; lease-based crash recovery escalates instead of resuming half-applied plans
- **Append-only audit** — every security mutation writes `audit_logs` in the same transaction

**Knowledge & evaluation**
- **Tiered RAG** — trusted/public/hostile tiers; production retriever hard-excludes hostile even on request (`TIER_DENIED` recorded on every denial path); hostile fixtures live only in eval collections (INV-012)
- **MITRE ATT&CK for ICS mapping** — declarative rules produce technique IDs with confidence + basis (never invented intel)
- **Injection suite** — 32 fixtures across families F1–F7 (incl. numeric-only F7 sensor attacks), naive vs hardened ASR/block-rate tables
- **Experiment matrix** — EXP-01…EXP-09 + stress protocol + fuzzy-rough channel-reduction arm from a single CLI, rerun-safe canonical runs keyed by committed config hashes
- **Dashboard** — dark command-center UI: telemetry, timeline, attribution bars, agent trace, validator panel, approval modal, demo stepper, audit viewer

## Architecture

```mermaid
flowchart LR
    subgraph Browser
        FE["React/TS dashboard<br/>(Vite :5173 → /api proxy)"]
    end
    subgraph Backend["FastAPI :8000"]
        API["Routers: auth · datasets · pipeline ·<br/>telemetry · incidents · agent · validator ·<br/>approvals · sandbox · eval · audit · demo"]
        SVC["Services: auth · approval · validator ·<br/>agent · sandbox · pipeline · incident · demo · audit"]
    end
    WORKER["Asyncio workers<br/>expiry scheduler · run reaper"]
    AGENT["Agent runner (ReAct)<br/>scripted ⧸ Ollama client"]
    VAL["Validator engine C1–C5<br/>verdict lattice"]
    SIM["Sandbox simulator<br/>(only executor, R4)"]

    subgraph Stores
        PG[("PostgreSQL 16<br/>metadata · state · audit")]
        S3[("MinIO<br/>raw/features/artifacts")]
        CH[("Chroma ⧸ LocalVectorStore<br/>KB embeddings")]
    end
    OLL["Ollama<br/>qwen2.5:7b-instruct"]
    MLF["MLflow :5001<br/>training runs"]

    FE -->|REST + SSE| API
    API --> SVC
    SVC --> PG
    SVC --> S3
    AGENT -->|tools| SVC
    AGENT -->|chat| OLL
    AGENT -->|retrieve| CH
    VAL --> PG
    SIM --> PG
    WORKER --> PG
    MLF -.->|training telemetry| AGENT
```

Data flow (single pass, mirrors AppFlow §1):

```text
OT telemetry → ingestion → preprocessing (train-fit scaling) → windowing W=60/S=1
  → detection (IF baseline / TCN-AE) → per-sensor attribution → explanation (hypothesis)
  → incident grouping → MITRE-ICS mapping → agent reasoning (tools + tiered RAG)
  → mitigation draft → C1–C5 validator → human approval (hash-bound)
  → sandbox simulation → audit log
```

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic |
| Auth | Argon2id password hashing, PyJWT access tokens, rotating hashed refresh tokens |
| Detection | scikit-learn (Isolation Forest), PyTorch optional (TCN-AE), NumPy/pandas |
| Storage | PostgreSQL 16 (metadata/state/audit), MinIO (raw features/artifacts), Chroma *or* deterministic LocalVectorStore |
| LLM | Ollama (`qwen2.5:7b-instruct`, pinned temperature-0 sampling) or scripted deterministic offline client |
| Tracking | MLflow (fail-open bridge) |
| Frontend | React 18, TypeScript (strict), Vite 5, TailwindCSS, Recharts |
| Tooling | pytest, ruff, mypy, Docker Compose, Make |

## Project Structure

Generated from the repository (abridged to meaningful units):

```text
aegis-ot/
├── app/                          # FastAPI application
│   ├── api/                      #   routers: auth, data, operations (+deps)
│   ├── core/                     #   config, security, exceptions, logging,
│   │                             #   canonical hashing, mlflow_bridge
│   ├── db/
│   │   ├── models/               #   SQLAlchemy models (Schema v1.1 hardened)
│   │   └── migrations/versions/  #   Alembic 0001..0003
│   ├── services/                 #   auth, approval, validator, agent, sandbox,
│   │                             #   pipeline, incident, demo, audit, state
│   └── workers/                  #   expiry scheduler + run reaper (asyncio)
├── pipeline/
│   ├── agent/                    #   ReAct runner, tools, prompts, LLM clients
│   ├── detect/                   #   iso_forest, tcn_ae, scoring, invariances
│   ├── explain/                  #   hypothesis explanation builder
│   ├── ingest/                   #   registry (hash-pinned), synthetic fixture
│   ├── preprocess/               #   causal cleaning, train-fit scaler, windower
│   ├── rag/                      #   chunker, embeddings, vectorstore, retriever, kb
│   ├── sandbox/                  #   plant_model (surrogate), simulator (sole executor)
│   ├── tintel/                   #   MITRE ATT&CK for ICS rule mapping
│   └── validator/                #   engine, verdict lattice, policy, pattern,
│                                 #   provenance, consistency
├── eval/
│   ├── attack_suite/             #   32 fixtures (F1–F7) + runner
│   ├── experiments.py            #   EXP-01..09 + STRESS-ROB orchestration CLI
│   ├── pilot.py                  #   EVAL-08 exploratory scaffold (≤10 vignettes)
│   ├── stress.py                 #   seeded noise/zeroing/drift protocol
│   ├── channel_reduction.py      #   fuzzy-rough mask (fit on TRAIN only)
│   ├── kb_qa.py                  #   RAG-04 canned-query harness
│   ├── bypass_battery.py         #   EXP-09 gate-bypass battery
│   ├── metrics/charter.py        #   single definition of every metric
│   └── demo_runner.py            #   `make demo` entry point
├── frontend/                     # React dashboard (src/pages, src/components, lib/api.ts)
├── configs/
│   ├── experiments/              # committed experiment configs (EVAL-07 hashes)
│   ├── policy/                   # action grammar + pattern filters (R2/R35)
│   ├── kb/                       # production corpus (trusted/public only)
│   └── *.yaml                    # features, invariants, stress, tintel rules
├── tests/                        # unit · validator · security · concurrency ·
│                                 # state_machine · rag · agent · ml · e2e
├── alembic.ini · Makefile · pyproject.toml · docker-compose.yml
└── Dockerfile · .env.example
```

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.11 | `pyproject.toml` `requires-python` |
| Node.js + npm | 18+ | frontend build/dev only |
| Docker Desktop | latest | only for the full service stack (PG/MinIO/Chroma/Ollama/MLflow) — **not required for offline dev/tests** |
| Git | any | |
| GPU | not required | CPU-only paths throughout (NFR-03) |

### Installation (Windows PowerShell)

```powershell
git clone <your-repo-url> aegis-ot
cd aegis-ot

# 1. Virtual environment + dependencies (dev extras include pytest/ruff/mypy)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,ml,stores]"

# 2. Environment
Copy-Item .env.example .env   # then edit — see next section

# 3. Service stack (optional for offline development; required for full stack)
docker compose up -d postgres minio chroma ollama mlflow

# 4. Schema + bootstrap (against PostgreSQL from step 3)
python -m app.db.migrate          # alembic upgrade head
python -m app.db.seed            # admin user + fixture dataset + KB corpus

# 5. Run it
uvicorn app.main:app --reload --port 8000     # terminal 1 — API
python -m app.workers.main                    # terminal 2 — worker
cd frontend; npm install; npm run dev         # terminal 3 — dashboard :5173
```

Offline quick loop (no Docker at all — SQLite + filesystem stores + scripted LLM):

```powershell
python -m pytest -q                              # full suite: 78 passed
python -m eval.experiments --exp EXP-01 --dataset-run local
python -m eval.demo_runner                       # Attack-the-Agent narrative
```

### Environment Variables

All runtime settings live server-side (Rules R6). Copy `.env.example` → `.env`.
Both `VAR` and `AEGIS_OT_VAR` spellings are accepted for settings fields; `.env.example` ships the exact mix below.

| Variable | Required | Purpose | Example / Notes |
|---|---|---|---|
| `AEGIS_OT_ENV` | ✅ | `dev` relaxes secret checks; anything else enforces them | `dev` |
| `AEGIS_OT_SECRET_KEY` | ✅ (non-dev) | JWT signing key | long random string; startup refuses `change-me` outside dev |
| `DATABASE_URL` | ✅ | SQLAlchemy URL | `postgresql+psycopg://aegis:aegis@localhost:5432/aegis_ot` or `sqlite:///./aegis_dev.db` |
| `AEGIS_OT_OBJECT_STORE` | optional | `local` (default, filesystem) \| `minio` | offline dev uses `local` |
| `AEGIS_OT_LOCAL_OBJECT_ROOT` | optional | local object root | `./.objects` |
| `MINIO_ENDPOINT` / `_ACCESS_KEY` / `_SECRET_KEY` | when `object_store=minio` | MinIO connection | compose defaults `aegis` / `aegis-secret` |
| `MINIO_BUCKET_RAW` / `MINIO_BUCKET_ARTIFACTS` | optional | bucket names | `aegis-raw` / `aegis-artifacts` |
| `AEGIS_OT_VECTOR_STORE` | optional | `local` (default, in-process cosine) \| `chroma` | |
| `CHROMA_HOST` / `CHROMA_PORT` | when chroma | Chroma endpoint | `localhost:8000` |
| `AEGIS_OT_LLM_BACKEND` | optional | `scripted` (deterministic offline) \| `ollama` | tests/demo require `scripted` |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | when ollama | LLM endpoint/model | `http://localhost:11434`, `qwen2.5:7b-instruct` |
| `MLFLOW_TRACKING_URI` | optional | training-run tracking | `http://localhost:5001`; unreachable MLflow never blocks training |
| `AEGIS_OT_ADMIN_EMAIL` / `_PASSWORD` | ✅ non-dev | bootstrap admin for `app.db.seed` | password ≥ 12 chars recommended |
| `AEGIS_OT_ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | optional | token lifetimes | 15 min / 7 days |
| `AEGIS_OT_REQUIRE_DISTINCT_APPROVER` | optional | control-class self-approval ban | `true` |
| `AEGIS_OT_LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_MINUTES` | optional | login limiter | 5 / 15 |
| `AEGIS_OT_APPROVAL_EXPIRY_HOURS` | optional | approval TTL → escalate | 24 |
| `AEGIS_OT_AGENT_MAX_STEPS` | optional | planner step budget | 12 |
| `AEGIS_OT_LLM_TIMEOUT_S` | optional | LLM call timeout | 90 |

No external SaaS credentials are required anywhere in the codebase.

## Usage

```powershell
# Health
curl http://localhost:8000/health

# Login (bootstrap admin from seed)
curl -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@aegis.local","password":"change-me-admin-12ch"}'

# Offline evaluation examples
python -m eval.experiments --exp EXP-01 --dataset-run local   # IF baseline end-to-end
python -m eval.experiments --exp EXP-02 --dataset-run local   # TCN-AE (needs torch)
python -m eval.experiments --exp STRESS-ROB --dataset-run local
python -m eval.kb_qa                                          # RAG-04 corpus run
python -m eval.pilot                                          # EVAL-08 scaffold
python -m eval.demo_runner                                    # 7-step demo narrative
```

Dashboard routes: `/login`, `/dashboard`, `/incidents`, `/incidents/:id`, `/approvals`, `/demo`, `/audit`, `/eval`, `/datasets`.

## API Reference

Actual FastAPI routes (role = minimum required; all require Bearer access token unless noted):

| Method | Endpoint | Auth | Role | Description |
|---|---|---|---|---|
| POST | `/auth/login` | — | public | Issue JWT + refresh cookie (anti-enumeration errors, limiter) |
| POST | `/auth/refresh` | cookie | public | Rotate refresh token; reuse revokes family |
| POST | `/auth/logout` | ✅ | any | Revoke token family, clear cookie |
| GET | `/auth/me` | ✅ | any | Current principal |
| GET | `/users` | ✅ | admin | List users + roles |
| POST | `/users` | ✅ | admin | Create user (password ≥ 12 chars) |
| PATCH | `/users/{id}` | ✅ | admin | Activate/deactivate |
| PUT | `/users/{id}/role` | ✅ | admin | Server-authoritative role assignment (R14) |
| GET | `/health` | — | public | DB liveness |
| GET | `/health/worker` | — | public | Worker heartbeat (< 60 s old) |
| GET | `/datasets` | ✅ | admin | Registry listing |
| POST | `/datasets/ingest/{key}` | ✅ | admin | Hash-pinned ingestion (`swat`, `wustl_iiot2021`, `wadi`, `synthetic`) |
| POST | `/datasets/{id}/preprocess` | ✅ | admin | Split + scale + window → feature blocks |
| POST | `/pipeline/train` | ✅ | admin | Train detector → `model_versions` (+MLflow) |
| POST | `/pipeline/run_detection` | ✅ | admin | Score windows → detections/anomalies/explanations/incidents |
| POST | `/incidents/{id}/threat_map` | ✅ | analyst | ATT&CK-ICS mapping rows (basis-cited) |
| GET | `/telemetry/latest` | ✅ | any | Latest 50 detection windows |
| GET | `/incidents` | ✅ | any | List/filter incidents |
| GET | `/incidents/{id}` | ✅ | any | Detail: anomalies, attributions, explanations, mappings |
| POST | `/incidents/{id}/close` | ✅ | analyst | Close (`no_action`) / resolve escalation (admin) |
| POST | `/incidents/{id}/agent_runs` | ✅ | analyst | Create + synchronously run agent variant |
| GET | `/agent/runs?incident_id=` | ✅ | any | Runs for incident |
| GET | `/agent/{run_id}` | ✅ | any | Reasoning trace + tool messages |
| GET | `/agent/{run_id}/stream` | ✅ | any | SSE message stream |
| POST | `/agent/{run_id}/propose` | ✅ | analyst | Resume/renew lease |
| GET | `/validator/{plan_id}` | ✅ | any | Verdict + C1–C5 checks + hash suffix |
| POST | `/validator/{plan_id}/rerun` | ✅ | analyst | Fresh validation of current revision |
| GET | `/approvals` | ✅ | analyst | Pending queue (revision + hash suffix shown) |
| POST | `/approvals/{id}/approve` | ✅ | analyst | Approve (distinct-approver enforced for control) |
| POST | `/approvals/{id}/deny` | ✅ | analyst | Deny — reason required |
| POST | `/approvals/{id}/amend` | ✅ | analyst | New immutable revision; supersedes prior approval |
| POST | `/sandbox/execute` | ✅ | analyst | Execute approved plan in simulator (INV‑003/005 gates) |
| POST | `/eval/run` | ✅ | admin | Run EXP-08 suite via API |
| GET | `/eval/runs` · `/eval/metrics` | ✅ | admin | Evaluation runs / metric tables |
| GET | `/audit` · `/audit/export.csv` | ✅ | admin | Audit query / escaped CSV export |
| POST | `/demo/attack` | ✅ | admin | Provision + replay Attack-the-Agent |
| GET | `/demo/attack/latest` | ✅ | any | Latest demo metrics |

Interactive docs: `http://localhost:8000/docs` (OpenAPI).

## Security Model

Enforced invariants (machine-checked; proofs in `tests/security`, `tests/concurrency`, `tests/state_machine`):

| Invariant | Mechanism |
|---|---|
| INV-001 Sandbox-only | No OT connectivity anywhere; sole executor is `pipeline/sandbox/simulator.py`; outputs labeled `SIMULATED` |
| INV-002 No raw commands | Actions are `{action, target, params}` objects validated against `configs/policy/actions.yaml` grammar |
| INV-003 Approval gate | write/control require an approved, unexpired, hash-bound approval row |
| INV-005 Triple hash binding | plan ↔ active validator result ↔ approval SHA-256 equality re-verified at execution from authoritative rows; tamper ⇒ `EXEC_HASH_MISMATCH` |
| INV-006/​R43 Amendment safety | amendments create new revisions; prior approval superseded same-transaction; fresh C1–C5 mandatory |
| INV-007 Expiry | expired approvals rejected by conditional UPDATE guard, scheduler-independent; expiry escalates (never silent-deny) |
| INV-008 Replay | pending→approved consumed atomically with plan validated→approved |
| INV-010 Naive lockout | naive runs never create approvals nor reach the sandbox; terminal `draft_only` |
| INV-012 Trust firewall | hostile tier excluded from production retrieval on every path; fixtures isolated to eval collections |
| INV-013 Same-tx audit | security mutations and their audit rows commit together |
| INV-015 Single active run | partial UNIQUE index + service check per incident |
| AuthN/Z | Argon2id, 15-min JWT, rotating hashed refresh with family revocation on reuse, login limiter, RBAC dependency on every route, roles only via admin endpoint |

## Research & Evaluation

| Question | What is measured |
|---|---|
| **RQ1** — trustworthy OT agent under adversarial input | End-to-end safety chain vs naive baseline across the F1–F7 injection suite |
| **RQ2** *(exploratory)* — does attribution+explanation help analysts? | EVAL-08 pilot scaffold (`eval/pilot.py`, ≤10 vignettes; human-rating slots pending study execution) |
| **RQ3** — do gating + grounding reduce unsafe actions? | ASR, unsafe-action rate, block rate, approval rate, relative reduction naive→hardened |

Experiment matrix (single entry point `python -m eval.experiments`):

| Experiment | Content | Status |
|---|---|---|
| EXP-01 | Isolation Forest baseline (point-wise P/R/F1, FPR, PR-AUC, PA%K) | ✅ runnable + executed on synthetic fixture |
| EXP-02 | TCN-AE proposed detector (+inference latency, DET-05) | ✅ runnable (torch present: measured F1 0.993, 0.077 ms/window on fixture) |
| EXP-03 | Ablation: no cyber-physical context | ✅ runnable + executed |
| EXP-04 | Ablation: explanation pathway detached | ✅ runnable + executed |
| EXP-05/06/07 | naive / grounded-RAG / grounded+validator arms | ✅ runnable + executed (hardened ≥ naive holds offline) |
| EXP-08 | 32-case injection suite F1–F7 → `injection_cases` | ✅ executed offline |
| EXP-09 | Gate-bypass battery (expiry, replay, supersede, tamper, naive, closed) | ✅ all attempts rejected |
| STRESS-ROB | EVAL-02 stress sweep + ROB-01/02 reduction arm (identical protocol, TRAIN-only mask fit, median over seeds) | ✅ executed on synthetic fixture |
| RAG-04 | 20 canned queries → hit-rate@5/MRR | ✅ executed (production KB built from `configs/kb`) |
| Licensed cells | SWaT / WUSTL-IIoT-2021 / WADI | ⏸ manual, license-gated — never bundled |

Reproducibility (EVAL-07): every run is keyed by `config_hash` over committed YAMLs + seeds; reruns regenerate the canonical row. All numbers above are **synthetic-fixture measurements with the scripted offline LLM backend** — reproducibility evidence, not licensed-SWaT results (R25/R41).

## Running Tests

```powershell
python -m pytest -q                                   # full suite — 78 passed, 2 intentional skips
python -m pytest tests/security -q                    # RBAC, approval guards, hash binding, naive lockout
python -m pytest tests/validator tests/unit -q        # C1–C5 golden tests + charter metrics
python -m pytest tests/e2e tests/concurrency -q       # offline flows, race semantics
python -m ruff check app pipeline eval tests          # lint
npm run build                                         # frontend type-check + production build (from frontend/)
```

The suite runs fully offline (SQLite in-memory, filesystem stores, scripted LLM).

## Development Workflow

```text
edit code → ruff check → pytest -q → (UI changes) npm run build → commit
```

- Config knobs belong in `configs/*.yaml` (R35) — no hardcoded thresholds in source.
- Every module keeps a role docstring (R38); commits follow `feat:/fix:/test:/docs:/chore:` prefixes (R37).
- Safety-relevant behavior changes must keep the invariant tests green — they are the spec's executable form.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `connection to server at "127.0.0.1", port 5432 failed ... password authentication failed` | `.env` points at PostgreSQL but the stack isn't up / creds differ | Start it: `docker compose up -d postgres` (creds `aegis`/`aegis_ot` per compose), or set `AEGIS_OT_DATABASE_URL=sqlite:///./aegis_dev.db` for offline dev |
| `no such table` from seed/CLI on SQLite | schema not created | `python -c "from app.db.session import ensure_lite_schema; ensure_lite_schema()"` (PG uses `python -m app.db.migrate`) |
| `relation "alembic_version" does not exist` / API starts empty | migrations not applied | `python -m app.db.migrate upgrade` |
| Frontend build fails with TS6133 unused import | lint-level TS strictness | remove the import (build = `tsc && vite build`) |
| EXP-02 reports `skipped_no_torch` | torch extra not installed | `pip install -e ".[ml]"` |
| Retrieval always `RETRIEVAL_UNAVAILABLE` | empty/local vector store or collection missing | build KB: `python -m app.db.seed` (or `python -m eval.kb_qa` after seeding); for Chroma set `AEGIS_OT_VECTOR_STORE=chroma` and start the service |
| Ollama timeouts / connection refused | backend `ollama` selected but server down | start Ollama, `ollama pull qwen2.5:7b-instruct`, verify `curl http://localhost:11434/api/tags`; or stay on `AEGIS_OT_LLM_BACKEND=scripted` |
| MLflow warnings in logs during training | tracking server down | harmless (fail-open bridge); start `docker compose up -d mlflow` to record runs |
| Port already in use (5432/8000/5173/5001) | another local service | stop it or change the port in `docker-compose.yml` / uvicorn / vite config |
| PowerShell blocks `.venv\Scripts\Activate.ps1` | execution policy | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `409 cannot_start_run_from_…` when launching an agent | incident not in `open`/`rejected`/`analyzing`, or another run active | close/retry the incident or wait for the active run to finish (INV-015) |

## Roadmap

From the live [Tracker](../7.%20Tracker.md):

- [x] Hardened backend: models/migrations, auth/RBAC, validator C1–C5, approvals, sandbox, audit
- [x] Injection suite (32 cases, F1–F7) + bypass battery — offline green
- [x] Experiment matrix CLI (EXP-01..09, stress+ROB arm, RAG-04, EVAL-08 scaffold)
- [x] Dashboard pages + typed client (strict TS build clean)
- [/] Team playbook corpus expansion (10+ playbooks target)
- [/] Full demo audit-trail verification on a live (Ollama) backend
- [ ] Licensed-data runs: SWaT + WUSTL-IIoT-2021 ingestion, sha256 pinning (manual, DEC-016)
- [ ] Docker-stack bring-up review (`make setup` end-to-end on clean machine)
- [ ] Hallucination-rate unsupported-question probe harness
- [ ] Stretch: LSTM-AE/Transformer-AE ablations, gpt-4o-mini cross-model, SHAP cross-check, WADI stress run

## Contributing

1. Fork / branch: `git checkout -b feat/your-feature`
2. Keep `python -m pytest -q` and `ruff check` green before pushing (R34/R37)
3. One logical change per commit; conventional prefixes
4. Never weaken invariant tests — they encode Rules.md §0

## License

Distributed under the **GNU GPL v3** — see [LICENSE](LICENSE).

## Acknowledgements

- SWaT literature community — physics bounds and stage topology informing the surrogate plant and invariants
- MITRE ATT&CK for ICS — technique identifiers used by the TINTEL mapper
- Log-injection research (LogJack, LogInject, Poisoning-the-Watchtower, NetInjectBench; InjecAgent, AgentDojo) — motivating threat model and benchmark gap analysis (see PRD §1.1 for citations)

*Contact: open an issue in this repository.*
