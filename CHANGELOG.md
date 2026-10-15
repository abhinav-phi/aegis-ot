# Changelog

All notable changes to **AEGIS-OT** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> ⚠️ **Safety reminder:** AEGIS-OT never connects to real OT/ICS infrastructure.
> Every mitigation executes only inside a labeled sandbox simulator.

## [Unreleased]

### Planned
- Licensed-dataset (SWaT / WUSTL-IIoT-2021) automated runner behind hash-pinned
  manifest checks — currently a documented manual procedure ([Manual Setup](MANUAL_SETUP.md)).
- TCN-AE detector training loop exposed as a first-class CLI (`pipeline/detect/tcn_ae.py`).
- Frontend component tests (Vitest + React Testing Library).
- Structured export of experiment tables (EXP-01…EXP-09) to CSV/Parquet.

## [1.0.0] — 2026-09-01

Initial public release of the research prototype. Full pipeline, safety chain,
evaluation framework, and dashboard are implemented and verified offline on a
committed synthetic mini-fixture.

### Added

**Detection & explainability**
- Isolation Forest baseline detector on frozen per-window statistics
  (`pipeline/detect/iso_forest.py`).
- TCN-AE proposed detector — dilated causal-conv autoencoder with per-channel
  residual decomposition (torch optional; honest skip recorded when absent).
- Sensor attribution with contribution percentages, deterministic tie-breaks,
  and a low-confidence floor.
- Declarative SWaT-style physics invariants with config-traced bounds
  (`configs/invariants.yaml`).
- Hypothesis-only NL explanations consuming structured attribution and
  invariant outcomes exclusively — no execution authority.

**Agentic reasoning**
- Single ReAct planner (deliberately no multi-agent swarm) with read-mostly
  tools: `query_latest`, `query_history`, `search_kb`, `check_invariant`,
  `propose_action`.
- Grounding contract: evidence-cited answers or an explicit
  *"insufficient data"* response.
- Naive-variant isolation: `variant='naive'` plans are terminal at
  `draft_only` — never validated, never approved, never executed (INV-010/R44).

**Safety chain (research core)**
- C1–C5 validator: provenance → allowlist → pattern filter → risk class →
  consistency. C1–C4 fully deterministic; every check records its
  `deterministic` flag.
- Immutable plan revisions: DB trigger + ORM listener lock `steps_hash`;
  amendments create revision N+1 and supersede prior approvals in the same
  transaction.
- SHA-256 triple binding (executed ≡ validated ≡ approved content) with hard
  `EXEC_HASH_MISMATCH` blocking.
- Approval workflow: pending → approve/deny/amend, distinct-approver
  enforcement for control-class actions, 24 h expiry auto-escalation
  (never silent-denies).
- Sandbox-only execution: 6-stage SWaT-style surrogate plant, idempotent step
  resume, lease-based crash recovery that escalates instead of resuming
  half-applied plans.
- Append-only audit trail: every security mutation writes `audit_logs` in the
  same transaction.

**Knowledge & evaluation**
- Tiered RAG (trusted / public / hostile) with production retriever
  hard-excluding hostile tier even on request (`TIER_DENIED` recorded on every
  denial path); hostile fixtures restricted to eval collections (INV-012).
- MITRE ATT&CK for ICS mapping via declarative rules producing technique IDs
  with confidence and basis.
- Adversarial injection suite: 32 fixtures across families F1–F7 (including
  numeric-only F7 sensor attacks), reporting naive vs hardened ASR/block rate.
- Experiment matrix (EXP-01…EXP-09) + stress protocol + fuzzy-rough
  channel-reduction arm from a single CLI, rerun-safe canonical runs keyed by
  committed config hashes.
- Dashboard: dark command-center UI — telemetry, timeline, attribution bars,
  agent trace, validator panel, approval modal, demo stepper, audit viewer.

**Infrastructure**
- FastAPI backend, PostgreSQL 16 + Alembic migrations, MinIO artifact store,
  Chroma vector store, Ollama LLM runtime, MLflow experiment tracking.
- React 18 + TypeScript + Vite frontend served by nginx.
- Docker Compose topology with internal network isolation for data services.

### Verified
- 78 backend tests green (unit, security, state_machine, validator, rag,
  concurrency, e2e) on the committed offline fixture.
- Frontend TypeScript build clean.

[Unreleased]: https://github.com/abhinav-phi/aegis-ot/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/abhinav-phi/aegis-ot/releases/tag/v1.0.0
