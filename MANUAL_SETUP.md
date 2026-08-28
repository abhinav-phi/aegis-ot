# AEGIS-OT — Manual Setup Guide

> **How to read this file:** everything the code handles automatically is marked **AUTOMATIC**. Everything *you* must personally do is marked **MANUAL**. Every command is Windows PowerShell, copy-paste ready, and exists in this repository.
>
> Safety first: AEGIS-OT must **never** be connected to real SCADA/PLC/OT infrastructure. The only executor in the codebase is a pure-Python simulator (`pipeline/sandbox/simulator.py`) whose outputs are labeled `SIMULATED`.

---

## 1. What I Need to Do (Summary)

1. Install prerequisites (Python 3.11+, Node 18+, optionally Docker Desktop).
2. Create `.env` from `.env.example` and fill in a real secret key (+ admin credentials outside dev).
3. Start the Docker services **or** stay fully offline (SQLite + local stores + scripted LLM).
4. Run migrations → seed → start backend → worker → frontend.
5. Verify health, log in as bootstrap admin, run the test suite and demo.

That's it. No API keys, no cloud accounts, no paid services exist anywhere in this codebase. The only external gate is dataset licensing (Section 6).

---

## 2. Prerequisites

| Requirement | Version | Why | How to Verify |
|---|---|---|---|
| Python | ≥ 3.11 | backend, pipeline, eval (`pyproject.toml` requires ≥3.11) | `python --version` |
| pip / venv | bundled | dependency install | `python -m venv --help` |
| Node.js + npm | 18+ | dashboard build/dev only | `node --version; npm --version` |
| Docker Desktop | latest | optional: PostgreSQL/MinIO/Chroma/Ollama/MLflow stack | `docker compose version` |
| Git | any | clone/branch | `git --version` |
| GPU | ❌ not required | all model paths run on CPU by design | — |

Offline development needs **only Python** (tests use SQLite in-memory, filesystem object/vector stores, scripted LLM).

---

## 3. Environment Variables

**MANUAL:** create the file once:

```powershell
Copy-Item .env.example .env
notepad .env
```

Location: repository root (`aegis-ot\.env`). It is git-ignored — never commit it.

Variables you must personally decide/fill:

```text
AEGIS_OT_SECRET_KEY
→ What: JWT signing secret (server-side only)
→ Why needed: access tokens are HMAC-signed with it
→ Where to obtain: generate one yourself, e.g.
  python -c "import secrets; print(secrets.token_urlsafe(48))"
→ Example format: 43+ random URL-safe characters
→ Where to paste: .env → AEGIS_OT_SECRET_KEY=...
→ Note: startup REFUSES the default 'change-me' when AEGIS_OT_ENV != dev

AEGIS_OT_ADMIN_EMAIL / AEGIS_OT_ADMIN_PASSWORD
→ What: bootstrap admin consumed by `python -m app.db.seed`
→ Why needed: first login + role administration (R14)
→ Example format: admin@aegis.local / ≥12 characters
→ Required (enforced) whenever AEGIS_OT_ENV != dev

DATABASE_URL
→ What: SQLAlchemy connection string
→ Default offline: sqlite:///./aegis_dev.db   (no setup needed)
→ With Docker: postgresql+psycopg://aegis:aegis@localhost:5432/aegis_ot
```

Everything else in `.env.example` has working defaults:

- **Development-only defaults you can keep:** `AEGIS_OT_OBJECT_STORE=local`, `AEGIS_OT_VECTOR_STORE=local`, `AEGIS_OT_LLM_BACKEND=scripted`, `AEGIS_OT_LOCAL_OBJECT_ROOT=./.objects`, `AEGIS_OT_LOCAL_VECTOR_ROOT=./.vectors`
- **Optional tuning:** token lifetimes, limiter window, approval expiry hours, agent max steps, LLM timeout
- **Only when switching backends:** MinIO endpoint/keys (object_store=minio), Chroma host/port (vector_store=chroma), Ollama host/model + `AEGIS_OT_LLM_BACKEND=ollama`, MLflow URI

Both spellings work for settings fields: `DATABASE_URL` ≡ `AEGIS_OT_DATABASE_URL`. `.env.example` ships the exact mix that the code reads.

**Never commit:** `.env`, `.objects/`, `.vectors/`, `*.db`, uploaded files under `.uploads/`.

---

## 4. API Keys / External Credentials

**There are none.** Verified against the codebase: no OpenAI key, no SaaS tokens, no model-marketplace accounts. The local Ollama server is the only model runtime, and the deterministic scripted backend removes even that dependency for tests/demo.

The single external gate is **dataset licensing** (next section).

---

## 5. Dataset Manual Steps (License-Gated)

Raw SWaT/WUSTL/WADI data is **NOT bundled** (Rules R21/R22, DEC-016). Nothing below is automated because licenses require a human requester.

### SWaT (primary)

```text
MANUAL  Step 1 — Request access from iTrust Labs (Singapore University of Technology and Design),
                https://itrust.sutd.edu.sg — sign the dataset usage agreement.
MANUAL  Step 2 — Download the Normal and Attack period network/sensor datasets you are licensed for.
MANUAL  Step 3 — Export/convert to CSV with columns:
                    timestamp, <sensor columns...>, label        ('label' column REQUIRED;
                    1 = attack window; sensors e.g. FIT101, LIT101, P101_STATE, AIT502)
MANUAL  Step 4 — Place the file anywhere readable, e.g.  C:\data\swat_normal.csv
AUTOMATIC AFTER COMMAND — hash pinning + registry row + object-store upload:
                POST /datasets/ingest/swat   (admin JWT)
                or pipeline.ingest.registry.ingest_dataset(db, key="swat", source_path=r"C:\data\swat_normal.csv")
```

The ingest computes sha256, rejects a *changed* file for the same key (`dataset_hash_conflict`), verifies the hash again at every later read (INV-016), and writes an audit row.

### WUSTL-IIoT-2021 (secondary) — same flow with `key="wustl_iiot2021"`.
### WADI (optional stretch) — same flow with `key="wadi"`.

Until licensed files are ingested, everything runs on the committed deterministic synthetic fixture (`pipeline/ingest/synthetic.py`) — clearly labeled synthetic everywhere it appears.

---

## 6. Docker / Services

Only needed if you want the full stack (PostgreSQL etc.). Offline dev skips this entirely.

```powershell
# Option A — infrastructure only (recommended while developing locally)
docker compose up -d postgres minio chroma ollama mlflow

# Option B — full containerized stack incl. app/worker/frontend
docker compose up -d
```

Services and ports (from `docker-compose.yml`):

| Service | Port(s) | Purpose | Health check |
|---|---|---|---|
| postgres:16-alpine | 5432 | metadata/state/audit DB | `docker compose ps` → `healthy` (pg_isready) |
| minio | 9000 API · 9001 console | raw features/artifacts (S3 API) | `docker compose ps` → `healthy` |
| chromadb/chroma | 8000 | RAG vector store | heartbeat endpoint |
| ollama/ollama | 11434 | local LLM server | see §10 |
| mlflow | 5001 | training-run tracking | web UI opens |
| app (image build) | 8000 | FastAPI | `curl http://localhost:8000/health` |
| worker (image build) | — | expiry scheduler + reaper | `/health/worker` via app |
| frontend (nginx) | 5173 → :80 | dashboard | open `http://localhost:5173` |

Compose credentials: Postgres `aegis/aegis` db `aegis_ot`; MinIO `aegis/aegis-secret`.

---

## 7. Database Setup

Order matters: schema → seed.

```powershell
# Terminal location: repo root, venv active

python -m app.db.migrate          # AUTOMATIC — alembic upgrade head (0001_initial → 0002_triggers → 0003_hardening_v11)
# Expected: 'Running upgrade ... -> 0003_hardening_v11 (head)'
# If it fails: check DATABASE_URL reachable (docker compose ps); fix creds; re-run.

python -m app.db.seed             # AUTOMATIC content, MANUAL prerequisite (.env admin vars)
# Expected output:
#   seed: created admin admin@aegis.local      (skipped if already present or vars unset)
#   seed: registered synthetic fixture dataset
#   seed: OK
# Also AUTOMATIC: builds production KB corpus from configs/kb into the configured vector store.

# Verify
python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health').read())"
# (backend must be running — Section 8)
```

SQLite note: offline CLIs call `ensure_lite_schema()` themselves; for a manual SQLite session run:
`python -c "from app.db.session import ensure_lite_schema; ensure_lite_schema()"`

---

## 8. Backend Startup

```text
Terminal 1
→ .\.venv\Scripts\Activate.ps1
→ uvicorn app.main:app --reload --port 8000
```

- Host/port: `http://localhost:8000`
- Expected log: `Uvicorn running on http://127.0.0.1:8000`
- Health: `curl http://localhost:8000/health` → `{"status":"ok","database":true,...}`
- Interactive OpenAPI docs: `http://localhost:8000/docs`

Non-dev environments refuse to boot with default secrets (config.validate_safety).

---

## 9. Worker Startup

```text
Terminal 2
→ .\.venv\Scripts\Activate.ps1
→ python -m app.workers.main
```

Runs two broker-free asyncio loops (single process; duplicate instances degrade to no-ops):

| Loop | Interval | Effect |
|---|---|---|
| Expiry scheduler | 60 s | pending approvals past `expires_at` → approval `expired`, plan + incident `escalated` (never silent-deny, R3) |
| Reaper | 30 s | stale agent runs (lease expired) → `interrupted`; stuck `executing` plans → escalated (fail-closed recovery) |

Verify alive (writes `.worker_heartbeat` in repo root):
`curl http://localhost:8000/health/worker` → `{"worker_alive": true}`

---

## 10. RAG / OLLAMA / CHROMA Setup

All three have deterministic offline fallbacks — configure them only for the full experience.

### Ollama (real LLM planner)

```powershell
docker compose up -d ollama                       # or install Ollama natively
docker exec -it aegis-ot-ollama-1 ollama pull qwen2.5:7b-instruct   # exact pinned model name
curl http://localhost:11434/api/tags              # verify model appears
# then in .env:  AEGIS_OT_LLM_BACKEND=ollama      (restart backend afterwards)
```

Sampling is pinned server-side (temperature 0, top_p 1, seed 0) for reproducibility. Until you switch the backend, everything uses `ScriptedClient` — the deterministic stand-in whose measured numbers are always labeled `scripted-offline`.

### Chroma (vector service)

```powershell
docker compose up -d chroma
# .env: AEGIS_OT_VECTOR_STORE=chroma   (CHROMA_HOST=localhost, CHROMA_PORT=8000)
```

### KB population (AUTOMATIC after command)

```powershell
python -m app.db.seed            # builds configs/kb → collection 'aegis_kb_prod'
python -m eval.kb_qa             # verify retrieval: prints hit-rate@5 + MRR over 20 canned queries
```

Hostile fixtures never touch this collection — they are built per-run into `aegis_kb_eval_*` collections only (R11/INV-012).

---

## 11. Frontend Startup

```powershell
Terminal 3
cd frontend
npm install                      # MANUAL once
npm run dev                      # dev server → http://localhost:5173  (/api proxied to :8000)

npm run build                    # production type-check + bundle → dist/  (must pass clean)
```

Dashboard routes: `/login`, `/dashboard`, `/incidents`, `/incidents/:id`, `/approvals`, `/demo`, `/audit`, `/eval`, `/datasets`.

---

## 12. First Login / Admin Bootstrap

1. **MANUAL:** set `AEGIS_OT_ADMIN_EMAIL` + `AEGIS_OT_ADMIN_PASSWORD` in `.env` (password ≥ 12 chars).
2. **AUTOMATIC:** `python -m app.db.seed` creates that user with role `admin` (idempotent).
3. Login at `/login` (UI) or `POST /auth/login`. Access token lives in memory; refresh arrives as the `aegis_refresh` cookie and rotates on every `/auth/refresh` (reuse revokes the whole family).
4. Create analyst/viewer users yourself (admin only): `POST /users` then `PUT /users/{id}/role` — there is deliberately **no client-side role selection** (R14).

---

## 13. Demo Setup (Attack-the-Agent)

Everything is generated at runtime from committed fixtures — nothing to download.

```powershell
# Backend prerequisites: DB migrated + seeded, backend + worker running, LLM_BACKEND=scripted (offline)
python -m eval.demo_runner       # headless 7-step narrative; prints naive vs hardened outcome
```

In the UI: log in as **admin** → `/demo` → trigger **Attack demo** (`POST /demo/attack`), then `/demo/attack/latest` feeds the stepper page.

What you should see (and nothing more): malicious context embedded → naive unsafe recommendation recorded (`UNSAFE — recorded only`, never gated/executed, INV-010) → provenance/pattern flags → trusted SPD-017 grounding surfaced → control action gated → safer plan approved by distinct approver → simulated execution labeled `SIMULATED`. Every card carries `SIMULATED`/`FIXTURE` badges (R39/R40). Note: with the scripted backend the hardened arm typically ends at *"insufficient data"* refusal rather than producing an approved plan — the UI comparison still shows naive-unsafe vs hardened-refusal honestly.

---

## 14. Commands I Should Run (Testing)

```powershell
# Environment verification
python --version ; node --version ; docker compose version

# Database
python -m app.db.migrate
python -m app.db.seed

# Services health
curl http://localhost:8000/health
curl http://localhost:8000/health/worker

# Full test suite (offline; ~15 s)
python -m pytest -q                        # expected: 78 passed, 2 skipped, 0 failed

# Targeted suites
python -m pytest tests/security -q         # RBAC, approvals, hash binding, naive lockout
python -m pytest tests/validator tests/unit -q
python -m pytest tests/e2e tests/concurrency -q

# Static checks
python -m ruff check app pipeline eval tests

# Frontend
cd frontend; npm run build                 # tsc strict + vite bundle, zero errors

# Evaluation smoke (offline)
python -m eval.experiments --exp EXP-01 --dataset-run local
python -m eval.experiments --exp EXP-08
python -m eval.kb_qa
python -m eval.demo_runner
```

---

## 15. Manual vs Automatic

| Task | Me (Manual) | Code/Script Handles |
|---|---|---|
| Install Python/Node/Docker | ✅ | ❌ |
| Create `.env` | ✅ | ❌ |
| Generate `SECRET_KEY`, choose admin password | ✅ | ❌ |
| Accept dataset licenses & download SWaT/WUSTL | ✅ | ❌ |
| Pull Ollama model | ✅ (if using real LLM) | ❌ |
| Start/stop Docker services | ✅ command | containers themselves |
| Virtualenv + `pip install -e ".[dev,ml,stores]"` | ✅ command | resolves/installs packages |
| Schema migrations | ❌ | `python -m app.db.migrate` |
| Bootstrap admin + fixture dataset + KB | ❌ | `python -m app.db.seed` |
| Hash-pinning ingested datasets | provide file path | sha256 + registry + audit |
| Preprocessing/windowing/scaling | ❌ | preprocess service (train-fit only) |
| Detector training + MLflow logging | ❌ | train path (MLflow fail-open) |
| Detection/attribution/explanations/incidents/tintel | ❌ | detection pipeline |
| Agent reasoning trace + validator C1–C5 | trigger only | runner + engine |
| Approval decisions | ✅ human, mandatory for write/control | workflow/guards around you |
| Sandbox execution | trigger only | simulator (sole executor) |
| Audit trail | ❌ | same-tx audit service |
| Tests/lint/build | run commands | everything asserted inside |

---

## 16. One-Time vs Every-Run

### One-time setup
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev,ml,stores]"
Copy-Item .env.example .env    # + edit secrets/admin
docker compose up -d           # if using the stack
cd frontend; npm install
```

### Every development session
```powershell
.\.venv\Scripts\Activate.ps1
docker compose up -d postgres minio chroma ollama mlflow   # only if stack needed
uvicorn app.main:app --reload --port 8000                  # terminal 1
python -m app.workers.main                                 # terminal 2
cd frontend; npm run dev                                   # terminal 3
```

### Before running experiments
```powershell
python -m app.db.migrate ; python -m app.db.seed            # once per fresh DB
python -m eval.experiments --exp EXP-01 --dataset-run local # offline cells
# Licensed cells additionally need Section 5 dataset steps first.
```

### Before the final demo
```powershell
python -m pytest -q                     # green suite
cd frontend; npm run build              # clean build
python -m eval.demo_runner              # narrative smoke
# fresh DB optional: drop volume (docker compose down -v) → migrate → seed → rerun demo
```

---

## 17. Troubleshooting (Symptom → Cause → Fix → Verify)

| Symptom | Cause | Exact fix | Verify |
|---|---|---|---|
| `password authentication failed for user "aegis"` on any command | `.env` targets PG but stack down / creds differ | `docker compose up -d postgres` (compose creds aegis/aegis), or set `AEGIS_OT_DATABASE_URL=sqlite:///./aegis_dev.db` | `docker compose ps` shows healthy; retry command |
| `seed:` crashes with `no such table` (SQLite) | schema missing before seed | `python -c "from app.db.session import ensure_lite_schema; ensure_lite_schema()"` then re-seed | seed prints `OK` |
| Alembic fails connecting | wrong/unreachable `DATABASE_URL` | align with compose (`postgresql+psycopg://aegis:aegis@localhost:5432/aegis_ot`) | `python -m app.db.migrate current` → `0003_hardening_v11 (head)` |
| Frontend build error `TS6133 ... never read` | unused import under strict TS | delete the flagged import line | `npm run build` exits 0 |
| EXP-02 result says `skipped_no_torch` | torch extra absent | `pip install -e ".[ml]"` | rerun returns metrics |
| Retrieval always `RETRIEVAL_UNAVAILABLE` | empty vector store / wrong backend | seed KB (`python -m app.db.seed`); or switch `AEGIS_OT_VECTOR_STORE` appropriately | `python -m eval.kb_qa` reports hit-rate |
| Ollama refused/timeout after switching backend | server down or model missing | start service; `ollama pull qwen2.5:7b-instruct` | `curl http://localhost:11434/api/tags` lists it |
| MLflow warnings during training | tracking server unreachable | harmless (fail-open); optionally `docker compose up -d mlflow` | training completes regardless |
| Port busy (5432/8000/5173/9000/11434/5001) | local conflict | stop conflicting process or change port in compose/uvicorn/vite config | affected service starts |
| `Set-ExecutionPolicy` error activating venv | PS policy | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` | activation succeeds |
| Login 401 `invalid_credentials` right after seed | admin vars changed after seeding | re-set `.env` values, delete/recreate user or re-run seed with original vars | login returns 200 |
| `409 active_run_exists_for_incident` | INV-015 single-active-run guard | wait for completion/interrupt (reaper) or resolve incident | new run accepted |

---

## 18. Safety Notes (mirrors Rules.md)

- **Never** connect this system to real SCADA/PLC/HMI/plant equipment. There is no OT interface in the code — keep it that way (R1/INV-001).
- All mitigation execution is simulation-only inside the surrogate plant; rows are labeled `SIMULATED` (R4/R40).
- Human approval for write/control actions is a hard requirement — do not weaken the gate, distinct-approver rule, or expiry escalation (R3, INV-003..009).
- Hostile KB fixtures are research/evaluation data confined to eval collections — never merge them into production corpora (R11/INV-012).
- Keep `.env` out of Git; rotate `AEGIS_OT_SECRET_KEY` outside dev (R6).
- Never present scripted-backend or synthetic-fixture numbers as licensed-SWaT results (R41/R42).

---

## 19. TL;DR — Start AEGIS-OT From Scratch

```text
1.  Install Python 3.11+, Node 18+, Docker Desktop
2.  cd aegis-ot
3.  python -m venv .venv ; .\.venv\Scripts\Activate.ps1
4.  pip install -e ".[dev,ml,stores]"
5.  Copy-Item .env.example .env     → set SECRET_KEY + ADMIN_EMAIL/PASSWORD
6.  docker compose up -d            (or skip for offline SQLite mode)
7.  python -m app.db.migrate
8.  python -m app.db.seed
9.  uvicorn app.main:app --reload --port 8000        (terminal 1)
10. python -m app.workers.main                        (terminal 2)
11. cd frontend ; npm install ; npm run dev           (terminal 3 → :5173)
12. curl http://localhost:8000/health                 → {"status":"ok"}
13. Log in as your bootstrap admin at http://localhost:5173/login
14. python -m pytest -q                               → 78 passed, 2 skipped
15. python -m eval.demo_runner                        → Attack-the-Agent smoke
```

*From fresh machine → verified running system, without guessing.*
