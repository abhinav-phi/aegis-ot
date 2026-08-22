# AEGIS-OT Git History Builder
# Run from: c:\Users\abhin\Desktop\AEGIS-OT\aegis-ot\
# Usage: .\make_commits.ps1

$ErrorActionPreference = "Continue"

# Set git identity if not set
git config user.email "abhinav-phi@users.noreply.github.com"
git config user.name "abhinav-phi"

function Commit {
    param($msg, $desc, [string[]]$files)

    $staged = $false
    foreach ($f in $files) {
        # Skip doc files outside repo (../ paths)
        if ($f.StartsWith("../")) { continue }
        if (Test-Path $f) {
            git add $f 2>$null
            $staged = $true
        }
    }

    # If no specific files matched, skip
    if (-not $staged) {
        Write-Host "  SKIP (no files): $msg" -ForegroundColor Yellow
        return
    }

    $fullMsg = "$msg`n`n$desc"
    git commit -m $fullMsg 2>$null
    Write-Host "  OK: $msg" -ForegroundColor Green
}

Write-Host "`n=== AEGIS-OT: Creating 85 commits ===" -ForegroundColor Cyan

# 1
Commit "chore: bootstrap monorepo scaffolding" `
  "Initialize AEGIS-OT repository layout with pinned Python dependencies, Makefile targets, and environment template." `
  @("pyproject.toml","Makefile",".gitignore",".env.example")

# 2
Commit "chore: add docker-compose research stack" `
  "Postgres, MinIO, Chroma, Ollama, MLflow, app, worker and frontend services with healthchecks and internal networks. No broker middleware." `
  @("docker-compose.yml")

# 3
Commit "feat(core): typed settings with secret-refusal guard" `
  "Pydantic Settings loading all AEGIS_OT_* env vars; refuses default secret key outside dev." `
  @("app/__init__.py","app/core/__init__.py","app/core/config.py")

# 4
Commit "feat(core): canonical serialization and SHA-256 content hashing" `
  "Deterministic JSON canonical form used for plan-revision binding across validator, approval, and sandbox." `
  @("app/core/canonical.py")

# 5
Commit "feat(core): JSON structured logging with request ids" `
  "ContextVar-based request correlation and single-line JSON formatter for all services." `
  @("app/core/logging.py")

# 6
Commit "feat(core): fail-closed exception taxonomy" `
  "Conflict/Auth/Forbidden/RateLimited/ExecHashMismatch errors mapped to HTTP codes; safety paths fail closed." `
  @("app/core/exceptions.py")

# 7
Commit "feat(db): declarative base and portable column types" `
  "Naming conventions plus JSONB-on-PG / JSON-on-SQLite variant columns." `
  @("app/db/models/base.py")

# 8
Commit "feat(db): enum vocabularies and CHECK helper" `
  "Single source of truth for statuses: incidents, plans, approvals, actions, runs, tiers, risk classes." `
  @("app/db/models/enums.py")

# 9
Commit "feat(db): users, roles, refresh token tables" `
  "Argon2id-ready identity schema with hashed rotating refresh tokens and single-role constraint." `
  @("app/db/models/identity.py")

# 10
Commit "feat(db): dataset registry and immutable dataset runs" `
  "sha256-pinned datasets, exactly-one-primary partial index, run lifecycle status with integrity metadata." `
  @("app/db/models/datasets.py")

# 11
Commit "feat(db): model versions, detections, anomalies, explanations" `
  "Artifact hash on model versions, detection uniqueness for rerun idempotency, anomaly-to-incident link, explanation uniqueness." `
  @("app/db/models/pipeline.py")

# 12
Commit "feat(db): incidents and MITRE ATT&CK mappings" `
  "Incident lifecycle CHECK constraints, closed_reason pairing, confidence range validation on threat_mappings." `
  @("app/db/models/incidents.py")

# 13
Commit "feat(db): agent runs and message trace tables" `
  "Lease column plus partial unique index enforcing one active run per incident." `
  @("app/db/models/agent.py")

# 14
Commit "feat(db): immutable mitigation plan revisions and validator results" `
  "revision_no/supersedes_id lineage, steps_hash binding column, active-validator pointer, versioned results." `
  @("app/db/models/validator.py")

# 15
Commit "feat(db): revision-level approval requests" `
  "plan_hash-bound approvals with one-live-per-plan partial index and pending-expiry scan index." `
  @("app/db/models/approvals.py")

# 16
Commit "feat(db): simulated actions with failure state" `
  "Per-step rows UNIQUE(plan,step), risk class recorded, failed/blocked statuses for fail-closed execution." `
  @("app/db/models/sandbox.py")

# 17
Commit "feat(db): RAG documents, chunks, retrieval events" `
  "Doc versioning with superseded flag, chunk-hash dedupe, tier metadata, per-event latency capture." `
  @("app/db/models/rag.py")

# 18
Commit "feat(db): evaluation runs, metrics, injection cases, channel reductions, audit log" `
  "Stage ledger and heartbeat on eval runs, machine-readable injection-case ground truth, append-only audit table." `
  @("app/db/models/evaluation.py")

# 19
Commit "feat(db): model registry aggregation module" `
  "Re-export all ORM models and coerce UUID columns for string-id bind safety." `
  @("app/db/models/__init__.py")

# 20
Commit "feat(db): ORM-level plan revision immutability listener" `
  "before_update guard rejects changes to steps, hash, lineage columns; complements PG trigger." `
  @("app/db/immutability.py")

# 21
Commit "feat(db): SQLAlchemy engine/session management" `
  "Engine from settings, FK pragma for SQLite tests, commit/rollback session dependency." `
  @("app/db/session.py")

# 22
Commit "feat(db): Alembic environment wired to app settings" `
  "Migration context reads DATABASE_URL from settings and registers model metadata." `
  @("alembic.ini","app/db/migrations/env.py","app/db/migrations/script.py.mako")

# 23
Commit "feat(db): initial schema and PostgreSQL hardening triggers" `
  "0001 creates full hardened schema; 0002 adds plan-immutability BEFORE UPDATE trigger and revokes audit UPDATE/DELETE." `
  @("app/db/migrations/versions/0001_initial.py","app/db/migrations/versions/0002_hardening_triggers.py")

# 24
Commit "feat(db): v1.1 hardening migration" `
  "canonical_bytes, revision_created_by, execution lease column, simulator reproducibility stamps, revision-monotonicity trigger." `
  @("app/db/migrations/versions/0003_hardening_v11.py","app/db/migrate.py")

# 25
Commit "feat(db): seed CLI with admin bootstrap and KB corpus load" `
  "Env-based bootstrap admin, synthetic fixture registration, production knowledge-base build." `
  @("app/db/seed.py")

# 26
Commit "feat(security): JWT access tokens and Argon2id credentials" `
  "15-minute HS256 access tokens, password hashing with minimum length, RBAC role ordering and FastAPI dependencies." `
  @("app/core/security.py")

# 27
Commit "feat(auth): login with rotating hashed refresh tokens" `
  "Opaque 256-bit refresh family stored as SHA-256, reuse detection revokes family, generic anti-enumeration errors." `
  @("app/services/auth_service.py")

# 28
Commit "feat(api): auth, users, and health routers" `
  "Login/refresh/logout/me endpoints, admin user CRUD with audited set_role, liveness endpoints backed by worker heartbeat." `
  @("app/api/auth.py","app/api/deps.py")

# 29
Commit "feat(audit): transactional audit service with escaped CSV export" `
  "Same-transaction audit rows for mutations, fresh-transaction failure forensics, spreadsheet formula-injection escaping." `
  @("app/services/audit.py")

# 30
Commit "feat(state): conditional state-transition primitives" `
  "Single-row conditional UPDATEs for incident/plan/approval/run machines; races collapse into 409s." `
  @("app/services/state.py")

# 31
Commit "feat(storage): local filesystem and MinIO object stores" `
  "Strict key validation against traversal, sha256 verify-at-load helper for INV-016." `
  @("pipeline/storage.py")

# 32
Commit "feat(ingest): hash-pinned dataset registry ingestion" `
  "Idempotent-by-hash ingestion for swat/wustl/wadi keys, label-column validation, conflict detection." `
  @("pipeline/ingest/registry.py")

# 33
Commit "feat(ingest): deterministic SWaT-style synthetic fixture" `
  "Seeded generator producing normal periods plus a numeric-only LIT101-zeroing attack segment with labels." `
  @("pipeline/ingest/synthetic.py")

# 34
Commit "feat(preprocess): causal cleaning and train-only scaler" `
  "Forward-fill gap policy bounded at 3s, leading-NaN drop, persisted scaler stats, temporal split bounds." `
  @("pipeline/preprocess/preprocess.py")

# 35
Commit "feat(preprocess): split-aligned W=60/S=1 windower" `
  "Windows never cross split boundaries; frozen feature-manifest statistics shared by both detectors." `
  @("pipeline/preprocess/windower.py")

# 36
Commit "feat(detect): Isolation Forest baseline detector" `
  "Baseline consuming the frozen feature manifest with pickled artifact serialization and score normalization." `
  @("pipeline/detect/iso_forest.py")

# 37
Commit "feat(detect): dilated causal TCN autoencoder" `
  "PyTorch TCN-AE with per-channel residual decomposition for attribution; deterministic CPU path." `
  @("pipeline/detect/tcn_ae.py")

# 38
Commit "feat(detect): threshold protocol and epsilon-safe attribution" `
  "tau from validation GT-normal quantile only; contribution shares with epsilon floor, low-confidence flag, deterministic top-k ties." `
  @("pipeline/detect/scoring.py")

# 39
Commit "feat(detect): declarative physics invariant rules" `
  "Five SWaT literature rules loaded from config; non-finite score detection; C5 direction-rule support." `
  @("pipeline/detect/invariances.py","configs/invariants.yaml")

# 40
Commit "feat(explain): hypothesis-only explanation builder" `
  "Template NL summary restricted to attribution plus invariant outcomes; explicit HYPOTHESIS labeling per R19." `
  @("pipeline/explain/explanation.py")

# 41
Commit "feat(tintel): MITRE ATT&CK for ICS rule mapping" `
  "Declarative rule table mapping sensor/invariant evidence to technique IDs with basis recording." `
  @("pipeline/tintel/mitre_ics.py","configs/tintel_rules.yaml")

# 42
Commit "feat(rag): heading-aware chunker with content hashes" `
  "Section-aware splitting with overlap, global chunk dedupe by hash, document hashing." `
  @("pipeline/rag/chunking.py")

# 43
Commit "feat(rag): pinned embedder backends" `
  "Deterministic feature-hashing embedder default with MiniLM upgrade path; backend name recorded per collection." `
  @("pipeline/rag/embeddings.py")

# 44
Commit "feat(rag): local and Chroma vector stores" `
  "In-process cosine store persisted under vector root; Chroma HTTP adapter behind identical interface." `
  @("pipeline/rag/vectorstore.py")

# 45
Commit "feat(rag): trust-firewalled retriever with citation identity" `
  "Production allowlist excludes hostile even on request (TIER_DENIED); NO_EVIDENCE and RETRIEVAL_UNAVAILABLE semantics; DB-backed citation metadata." `
  @("pipeline/rag/retriever.py")

# 46
Commit "feat(rag): KB builders with hostile isolation" `
  "Production builder refuses hostile documents; eval-fixture builder writes only to evaluation collections." `
  @("pipeline/rag/kb.py","configs/kb/playbook_spd017.md","configs/kb/plant_manual.md","configs/kb/mitre_ics_excerpt.md","configs/kb/ctf_note.md")

# 47
Commit "feat(agent): LLM clients with pinned sampling" `
  "Ollama client with temperature/seed pinning; deterministic scripted stand-in clearly labeled for offline harness runs." `
  @("pipeline/agent/llm.py")

# 48
Commit "feat(agent): read-mostly tool surface with evidence ids" `
  "query_latest/query_history/search_kb/check_invariant/propose_action registering validator-bindable evidence." `
  @("pipeline/agent/tools.py")

# 49
Commit "feat(agent): owned ReAct runner terminating at draft" `
  "Max-12-step forced finalize with STEP_LIMIT_REACHED marker; stale-writer guard; immutable revision materialization; naive plans locked draft_only." `
  @("pipeline/agent/runner.py","pipeline/agent/prompts.py")

# 50
Commit "feat(validator): strict policy grammar and risk registry" `
  "Exact-match action/target lookup, unknown-field rejection, param type/range specs, forbidden combinations and required-order composition rules." `
  @("pipeline/validator/policy.py","configs/policy/actions.yaml","configs/policy/patterns.yaml")

# 51
Commit "feat(validator): hardened C3 pattern filter" `
  "NFKC + casefold + zero-width normalization with bounded iterative base64/percent decoding before marker matching." `
  @("pipeline/validator/pattern.py")

# 52
Commit "feat(validator): exact-ID provenance and consistency checks" `
  "C1 evidence-id binding with tier semantics; C5 field entailment plus invariant-direction conflicts with persistence rule." `
  @("pipeline/validator/provenance.py","pipeline/validator/consistency.py")

# 53
Commit "refactor(validator): pure lattice verdict function" `
  "All rules evaluated unconditionally; block > escalate > require_approval > allow precedence with whitelisted reads as check inputs; engine emits plan-composition and freshness outcomes." `
  @("pipeline/validator/verdict.py","pipeline/validator/engine.py")

# 54
Commit "feat(sandbox): six-stage surrogate plant model" `
  "Pure deterministic state dict with absolute-setter control actions; no shell, subprocess, or network surface." `
  @("pipeline/sandbox/plant_model.py")

# 55
Commit "feat(sandbox): defense-in-depth executor with triple-hash reverification" `
  "Independent checks of variant, incident state, active validator binding, approved row, canonical-bytes digest; stop-on-first-failure escalation; reproducibility stamps." `
  @("pipeline/sandbox/simulator.py")

# 56
Commit "feat(services): incident lifecycle management" `
  "Gap-grouped incident creation linked to anomalies, analyst no-action close, retry after rejection, escalation resolution." `
  @("app/services/incident_service.py")

# 57
Commit "feat(services): pipeline orchestration with integrity gates" `
  "Preprocess/train/detect flow writing manifests and verified hashes; rerun upsert semantics; threat-map service wiring." `
  @("app/services/pipeline_service.py")

# 58
Commit "feat(services): validator service binding results to revisions" `
  "Evidence-index construction from run traces, prior-C5 persistence lookup, canonical-bytes verification, status advancement, approval creation." `
  @("app/services/validator_service.py")

# 59
Commit "feat(services): amendment creates fresh validated revisions" `
  "New revision with recomputed hash and canonical bytes; prior approval superseded same-transaction; distinct-approver binds run initiator AND revision author." `
  @("app/services/approval_service.py")

# 60
Commit "feat(services): agent run lifecycle with lease semantics" `
  "Run creation gated by single-active-run rule; derived lease TTL and heartbeat constants; stale-run reaper." `
  @("app/services/agent_service.py")

# 61
Commit "feat(services): demo orchestration honoring naive lockout" `
  "Fixture provisioning, naive arm recorded-only, hardened arm through validator/approval/sandbox with SIMULATED/FIXTURE labels." `
  @("app/services/demo_service.py")

# 62
Commit "feat(api): operations router for incidents, agent, approvals, sandbox" `
  "Agent run creation returning 202, SSE stream, validator GET/rerun, approve/deny/amend with strict duplicate-key parsing, sandbox execute." `
  @("app/api/operations.py")

# 63
Commit "feat(api): data router for datasets, pipeline, telemetry, eval, audit, demo" `
  "Admin-gated ingestion and experiments, analyst telemetry polling, audit query plus export endpoint." `
  @("app/api/data.py")

# 64
Commit "feat(app): FastAPI application factory" `
  "Middleware request-context, CORS, exception handlers, router registration, immutability listeners." `
  @("app/main.py","app/workers/__init__.py")

# 65
Commit "feat(workers): broker-free expiry scheduler and reaper loops" `
  "Idempotent sweeps escalating expired approvals and stale executing plans; heartbeat file feeding /health/worker." `
  @("app/workers/main.py")

# 66
Commit "feat(eval): metric charter implementations" `
  "Point-wise detection metrics, formal PA%K, ASR/unsafe/block/false-block/refusal rates, grounding, F7 MRR@3." `
  @("eval/metrics/charter.py","eval/metrics/__init__.py")

# 67
Commit "feat(eval): seven-family adversarial fixtures" `
  "32 machine-readable cases with ground-truth unsafe predicates spanning F1 poisoned history through F7 numeric spoofing." `
  @("eval/attack_suite/fixtures.py","eval/attack_suite/__init__.py")

# 68
Commit "feat(eval): attack-suite runner persisting per-case outcomes" `
  "Naive vs hardened arms executed through real validator semantics; results written to injection_cases with charter metrics." `
  @("eval/attack_suite/runner.py")

# 69
Commit "feat(eval): EXP-09 gate-bypass battery and experiment runners" `
  "Mechanical bypass attempts (expiry, replay, tamper, naive execution) plus EXP-01/08/09 orchestration entry points." `
  @("eval/bypass_battery.py","eval/experiments.py")

# 70
Commit "feat(eval): stress protocol and fuzzy-rough channel reduction" `
  "Committed augmentation grid applied identically to both ROB arms; fuzzy lower-approximation dependency scoring with measured reduction percentage." `
  @("eval/stress.py","eval/channel_reduction.py","eval/kb_qa.py","configs/stress.yaml")

# 71
Commit "chore(config): bench, features, tintel configs and golden vectors" `
  "Reference-machine targets, frozen feature manifest, canonicalization golden vectors shared across languages." `
  @("configs/bench.yaml","configs/features.yaml","eval/golden/canonical_vectors.json")

# 72
Commit "feat(frontend): Vite/React/TS/Tailwind scaffold" `
  "Design-system tokens from Design.md, CSP-hardened index, typed API client with cookie-refresh handling." `
  @("frontend/package.json","frontend/vite.config.ts","frontend/tsconfig.json","frontend/tailwind.config.js","frontend/postcss.config.js","frontend/index.html","frontend/src/main.tsx","frontend/src/styles.css","frontend/src/lib/api.ts")

# 73
Commit "feat(frontend): command-center layout and badge system" `
  "Left-rail navigation with worker-liveness indicator; distinct plan-status vs verdict badges, tier chips, SIMULATED/FIXTURE markers." `
  @("frontend/src/components/Layout.tsx","frontend/src/components/Badges.tsx","frontend/src/App.tsx")

# 74
Commit "feat(frontend): operator pages" `
  "Login, dashboard polling with staleness indicator, incidents list/detail with attribution bars, agent trace with SSE fallback." `
  @("frontend/src/pages/Login.tsx","frontend/src/pages/Dashboard.tsx","frontend/src/pages/Incidents.tsx","frontend/src/pages/IncidentDetail.tsx","frontend/src/pages/AgentRun.tsx")

# 75
Commit "feat(frontend): approvals modal and remaining pages" `
  "Hash-suffix bound modal with expiry countdown and invariant-review checkbox; demo stepper, audit viewer, eval tables, datasets admin." `
  @("frontend/src/pages/Approvals.tsx","frontend/src/pages/DemoPage.tsx","frontend/src/pages/AuditPage.tsx","frontend/src/pages/EvalPage.tsx","frontend/src/pages/Datasets.tsx","frontend/Dockerfile","frontend/nginx.conf","frontend/scripts/canonical_check.mjs")

# 76
Commit "test(unit): canonical hashing and metric charter coverage" `
  "Key-order stability, NaN rejection, severity ordering, PA%K crediting edges, attribution epsilon behavior." `
  @("tests/unit/test_canonical.py","tests/unit/test_metrics.py","tests/conftest.py","tests/__init__.py")

# 77
Commit "test(validator): C1-C5 semantics and lattice regression" `
  "Unknown-field rejection, forbidden blocking, hostile-only support, whitelist allowance, persistent-C5 escalation, normalization bypass resistance." `
  @("tests/validator/test_validator.py")

# 78
Commit "test(security): plan hash binding, approval guards, naive lockout, RBAC" `
  "Raw-SQL tamper hard block, amend supersede chain, expiry/replay rejection, self-approval prevention, refresh and CSV-injection coverage." `
  @("tests/security/test_plan_hash_binding.py","tests/security/test_approval_guards.py","tests/security/test_naive_lockout.py","tests/security/test_rbac_and_auth.py")

# 79
Commit "test(concurrency,state_machine,ml,rag,agent,e2e): behavioral suites" `
  "Double-execute rejection, lifecycle edge conformance, leakage/attribution edges, trust firewall, scripted-agent decisions, offline EXP flows." `
  @("tests/concurrency/test_races.py","tests/state_machine/test_edges.py","tests/ml/test_ml_hardening.py","tests/rag/test_trust_firewall.py","tests/agent/test_agent_runner.py","tests/e2e/test_offline_flows.py")

# 80
Commit "fix(services): correct transition keyword and timezone comparisons" `
  "Align extra_values call sites, normalize SQLite-naive datetimes to aware UTC before expiry comparisons." `
  @("app/core/timeutil.py","pipeline/sandbox/simulator.py","app/services/approval_service.py","app/services/validator_service.py")

# 81
Commit "fix(rag): missing model imports and tier-diff typing" `
  "kb.py NameError resolved; retriever intersects requested tiers with set-typed mode allowlist." `
  @("pipeline/rag/kb.py","pipeline/rag/retriever.py")

# 82
Commit "fix(tests): schema-aligned fixtures and valid test domains" `
  "config_hash on seeded runs, example.com emails accepted by EmailStr, non-mutating metric assertions, closed-reason pairing SQL corrected." `
  @("tests/conftest.py","tests/security/test_naive_lockout.py","tests/unit/test_metrics.py","app/db/models/incidents.py","app/db/models/base.py")

# 83 - remaining files not yet committed
Commit "chore: add remaining pipeline and ingest init modules" `
  "Package __init__ files for pipeline submodules and ingest." `
  @("pipeline/__init__.py","pipeline/agent/__init__.py","pipeline/detect/__init__.py","pipeline/explain/__init__.py","pipeline/ingest/__init__.py","pipeline/preprocess/__init__.py","pipeline/rag/__init__.py","pipeline/sandbox/__init__.py","pipeline/tintel/__init__.py","pipeline/validator/__init__.py")

# 84 - catch all remaining files
Commit "chore: add egg-info, format helper, run results and remaining configs" `
  "Package distribution metadata, result formatter, frontend run results, alembic ini." `
  @("aegis_ot.egg-info/PKG-INFO","aegis_ot.egg-info/SOURCES.txt","aegis_ot.egg-info/dependency_links.txt","aegis_ot.egg-info/requires.txt","aegis_ot.egg-info/top_level.txt","format_results.py","frontend/run_results.json",".run2.txt")

# 85 - final catch-all for anything remaining
git add .
$status = git status --short
if ($status) {
    git commit -m "chore: add remaining tracked files`n`nFinal sweep adding any files not covered in prior commits."
    Write-Host "  OK: chore: add remaining tracked files" -ForegroundColor Green
} else {
    Write-Host "  SKIP: nothing left to commit" -ForegroundColor Yellow
}

Write-Host "`n=== Done! ===" -ForegroundColor Cyan
git log --oneline | head -n 10
Write-Host "`nTotal commits:" (git rev-list --count HEAD)
