# AEGIS-OT — Project Summary

> **Project:** AEGIS-OT — Cyber-Physical Anomaly Attribution and Validator-Gated Mitigation Intelligence for SCADA / Industrial Control Networks
> **One line:** a research-grade decision-support platform that turns OT/ICS telemetry into attributed, explainable anomaly detections, then uses a single evidence-grounded LLM agent to propose mitigations that are checked by a deterministic validator/policy gate and require **human approval** before any **simulated** action.
> **Source documents (authoritative, final):** `1. PRD.md` · `2. TechSpec.md` · `3. AppFlow.md` · `4. Design.md` · `5. Schema.md` · `6. ImplementationPlan.md` · `7. Tracker.md` · `8. Rules.md`
> **Spec version:** v1.1 — post-audit hardened contract (immutable plan revisions + SHA-256 triple binding, amendment → mandatory re-validation, all-or-nothing revision approval, naive-agent execution lockout, RAG trust firewall, INV-001..016, R43–R46). Implemented and offline-verified (Step 8, 2026-08-23) — see §22 for verified status and `aegis-ot/README.md` for the runnable-system guide.

**What it is NOT:** not a generic IDS/NIDS; not a generic LLM chatbot; not a multi-agent swarm; not a production-safe autonomous SCADA controller; not a system that ever touches real industrial infrastructure. All outputs are decision support for a human analyst; every automatic action is simulated.

---

## 1. Executive Overview

OT/ICS environments are being connected to IT operations faster than they can be defended. Public anomaly-detection benchmarks on SWaT are saturated, and the LLM-based SOC copilots now being deployed are vulnerable to **log-substrate prompt injection** — the evidence they read is attacker-controlled. No one can currently measure whether an LLM incident-response agent is safe enough for a plant context, because **no OT/ICS agent benchmark exists**.

AEGIS-OT is a measurement and safety-intervention study that closes that gap on an approximately **10-week** plan. It turns SWaT and WUSTL-IIoT telemetry into attributed, explainable anomaly detections (**TCN-AE** primary detector vs. **Isolation Forest** MVP baseline; LSTM-AE/Transformer-AE/XGBoost/ANFIS are stretch ablations only), maps incidents to **MITRE ATT&CK for ICS** (requirement **TINTEL-01**), and runs a single grounding-constrained ReAct planner over a **tiered RAG** knowledge base — invoked **by the analyst, never auto-started**. Every proposed mitigation is materialized as an **immutable plan revision bound by SHA-256** (`steps_hash`); the **deterministic validator/policy gate (C1–C5)** result, the human approval, and the sandbox execution each store and re-verify that hash — any mismatch is a HARD BLOCK (`EXEC_HASH_MISMATCH`). `write`/`control`-class actions require **human approval** of the whole revision (**all-or-nothing**, one live approval per revision; amendments create a NEW revision with fresh validation and supersede prior approvals; approver ≠ initiator for control-class); 24 h expiry → auto-**escalation**, never a silent deny; execution happens only in a **sandbox plant simulator** with an **append-only audit trail**. Naive evaluation agents are execution-impossible by construction (INV-010 lockout). The safety claim is demonstrated by an **Attack-the-Agent** experiment — 30+ cases across 7 attack families (F1–F7), naive agent vs. hardened pipeline. F7 (numeric cyber-physical sensor spoofing) runs in the **automated evaluation suite**, not as a step in the interactive demo narrative.

Pipeline (one pass; stages 1–8 automatic, agent run manual):

```
DATA (SWaT / WUSTL-IIoT, MinIO) → INGEST → PREPROCESS (z-score train-fit, W=60/S=1)
  → TRAIN (TCN-AE, normal windows) → INFERENCE (residual > τ) → ANOMALY
  → EXPLAIN (attribution + 5 invariants + NL summary) → INCIDENT (group, severity)
  → THREAT MAP (TINTEL-01: MITRE-ICS technique, confidence, basis)
  → [MANUAL] AGENT RUN (single ReAct planner, 5 tools, analyst-invoked)
  → VALIDATOR (C1–C5, deterministic, fail-fast, recorded)
  → HUMAN APPROVAL (write/control; expiry → escalate)
  → SANDBOX (6-stage SWaT-style surrogate; SIMULATED only) → CLOSE + AUDIT (immutable)
```

**Why it matters:** it attacks the *last* trust problem of LLM assistance in critical infrastructure — "safe enough to be allowed to recommend" — with measurable outcomes (unsafe-action rate, block rate, attack success rate), not vibes.

---

## 2. Problem Statement

1. **SCADA/ICS security.** OT systems were built for availability, not security; IT integration expands the attack surface faster than defenders adapt. The December 2025 joint guidance *Principles for the Secure Integration of Artificial Intelligence in Operational Technology* (CISA / ASD's ACSC / NSA AISC, with FBI and international partners) explicitly names LLM-based AI and AI agents as a distinct OT risk category; NIST SP 800-82 Rev. 3 supplies the broader OT-security-architecture context.
2. **Saturated detection benchmarks.** SWaT leaderboard figures up to ≈98 F1 (e.g., TFMAE, ICDE 2024) are typically reported under the **point-adjustment protocol**, shown to overstate performance even for untrained detectors (Kim et al., AAAI 2022). 2026 event-level stress-protocol work (arXiv:2602.15457, preprint) shows **rankings flip** under realistic noise, zeroing, and drift. AEGIS-OT therefore reports **point-wise F1 and PA%K** and defends stress robustness, not leaderboard F1.
3. **Explainability + cyber-physical context.** Black-box detectors give a score but not *where* or *why*; attention weights are not explanations; and sensor readings must be judged against plant physics (invariants).
4. **LLM/agent reliability.** Incident responders hallucinate, over-trust injected context, and cannot be reliability-guaranteed. 2025–26 preprints — LogJack (arXiv:2604.15368), LogInject (arXiv:2607.14493), Poisoning-the-Watchtower (arXiv:2605.24421), NetInjectBench (arXiv:2607.10490) — show log/telemetry content is an *attacker-controlled input* (0–86% verbatim command execution; input-side guardrails largely fail on log-formatted payloads). All four are IT/cloud/network-domain studies, cited as **motivating analogy**, not OT evidence.
5. **Unsafe automation, unmeasurable.** Autonomous responders cannot be trusted in a plant, but alert volume exceeds human capacity. The missing piece is a **demonstrably safe augmentation layer**, not a faster detector — and its safety currently cannot be measured: indirect injection travels through the data plane, benchmarks exist only for other domains (InjecAgent: email/finance/smart-home; AgentDojo: banking/Slack/travel/workspace), and **none covers OT/ICS**.

---

## 3. Research Questions

> **RQ1 (primary).** Can an LLM-based OT incident-response agent be made trustworthy and safe enough for industrial cybersecurity decision support *under adversarial and misleading inputs*?

> **RQ2 (exploratory, small-N pilot).** Does adding cyber-physical attribution and natural-language explanation plausibly improve analyst decision quality over a raw detector score? Operationalized as a small, explicitly pilot-scale study (EVAL-08, ≤ 10 analyst decision-vignettes) — reported as exploratory, **never as a headline claim**.

> **RQ3.** Do validator/policy gating and evidence grounding measurably reduce the unsafe-action rate of an LLM incident-response agent under indirect prompt injection?

Measurement: RQ1 via the Attack-the-Agent experiment (EXP-08, 30+ cases, F1–F7, naive vs. hardened — ASR, unsafe-action rate, block rate); RQ3 via the agent ladder naive (EXP-05) → grounded RAG (EXP-06) → RAG + validator (EXP-07), all reporting the same safety metrics.

---

## 4. Research Contribution

AEGIS-OT contributes a **measurable safety architecture for OT/ICS LLM incident-response agents**: attribution-based explainability over cyber-physical telemetry, an evidence-grounded single-agent responder, a deterministic validator/policy gate as an *independent* safety layer, and an adversarial evaluation suite covering textual (F1–F6) and numeric cyber-physical (F7) attack families. The contribution is the quantified, honest safety claim — validator block rates, unsafe-action rates, stress robustness, attribution quality — measured under a defined protocol on a domain for which no agent-safety benchmark currently exists.

No "first-ever" or SOTA claims are made (Rules R24); SWaT detection F1 is treated as saturated, and the defensible claims are robustness, attribution, and safe-agent evaluation.

---

## 5. What Makes AEGIS-OT Different

| Generic alternative | AEGIS-OT |
|---|---|
| Generic IDS / NIDS | Process-level (sensor/actuator) anomaly detection on **cyber-physical telemetry**, with attribution |
| Generic LLM security assistant | **OT-specialized**: plant invariants, MITRE ATT&CK for ICS mapping (TINTEL-01), SWaT/playbook KB |
| Multi-agent swarms | **Single agent by design** — a second agent would confound RQ3's measurement of gating |
| Learned-policy responders (e.g., MARL) | **Deterministic validator + human gate**, auditable and bounded |
| "Trust the model" demonstrations | **Attack-the-Agent evaluation** (7 families) that measures the hardening, not asserts it |
| LLM-judge safety checks | **Deterministic code checks (C1–C4)** + rule-based consistency (C5) — never the planner's own model |

---

## 6. System Architecture

- **Frontend** — "Industrial Cyber Command Center" dark theme (Design.md): telemetry stream, anomaly timeline, incident detail (attribution + explanation + MITRE mapping), agent reasoning/evidence panel (SSE), validator panel with exact policy-rule references on block, approval modal, demo stepper, audit viewer, eval tables.
- **Backend/API** — FastAPI + Pydantic; roles enforced server-side (`admin`/`analyst`/`viewer`); ~15 routes; polling worker (batch data — consciously no Kafka/Redis).
- **ML pipeline** — preprocess (z-score train-fit, W=60/S=1) → TCN-AE detect → attribute → explain → invariants → incident → `tintel` threat map (TINTEL-01).
- **Agent + Validator + Approval** — single ReAct planner (owned runner, lease/reaper, analyst-triggered via run-creation endpoint) → C1–C5 hardened checks bound to revision hash → all-or-nothing approve/deny/amend-with-revalidation, 24 h expiry → escalate.
- **Storage/LLM** — PostgreSQL 16 (23 tables + enums) · MinIO (raw telemetry, features, checkpoints) · Chroma (embeddings) · Ollama Qwen2.5-7B; gpt-4o-mini stretch-only (AGENT-06).
- **Sandbox** — 6-stage SWaT-style surrogate plant (tanks, pumps, valves); applies approved simulated actions; NEVER real hardware; SIMULATED-labeled (R40).

Conscious non-decisions: no streaming/Kafka, no Redis, no LangChain chains/plugins (owned prompts for reproducibility, R35), no multi-agent orchestration.

---

## 7. Detection & Cyber-Physical Attribution

- **Primary detector:** TCN-AE — dilated causal-convolution autoencoder trained on **normal-only** windows; long receptive field cheaply, stable gradients vs. LSTM; attributed via reconstruction-error decomposition (monotone in per-channel residual), *not* attention (R18).
- **MVP baseline:** Isolation Forest on window statistics — the single MVP baseline; LSTM-AE (DET-06) and Transformer-AE / XGBoost / ANFIS (DET-07) are stretch ablations only.
- **Input/windowing:** SCADA/OT telemetry (SWaT primary, WUSTL-IIoT-2021 secondary) in MinIO; rolling W=60 (60 s at 1 Hz), stride S=1.
- **Training discipline:** μ/σ and threshold τ fit **on train/validation only**; temporal splits with **no shuffle**; stress augmentations touch test only; leakage test in CI.
- **Scoring/attribution:** per-sensor residual `e_t`; window score = mean normalized residual; anomaly = score > τ; `contribution_i = r_i / Σ r_j` → top-3 sensors (`anomalies.top_sensors`); every detection row records score, τ, label, latency.
- **Invariant checks:** 5 physics-bound rules from SWaT literature (e.g., tank level within sensor range, pump status ↔ flow) merged into explanations as corroborating/contradicting evidence; `check_invariant` is also an agent tool.

**Terminology (precise):** *anomaly detection* = binary window classification (score > τ); *localization* = which windows are anomalous (incident grouping, gap ≤ 60 s); *attribution* = which channels drove the residual — **not** root-cause analysis; *explanation* = evidence-grounded NL summary (§8); *root cause* is **never claimed** — attribution is evidence for an analyst hypothesis (R19).

---

## 8. Explainability

The explanation object (`anomaly_explanations`) contains a natural-language summary (template + LLM polish, prompt pinned), structured evidence with citations, top-3 contributing sensors, and the 5 invariant-check results. A consistency score (XAI-03) checks that the same anomaly family produces the same explanation shape; 20 anomaly windows are manually reviewed.

Hard rules: attention weights are recorded for diagnostics but **never** presented as explanations (R18, XAI-04); LLM diagnosis is **never** ground truth — output is decision support, UI labels say "diagnosis is hypothesis" (R19); claims need chunk/tool citations, unsupported questions get "insufficient data" (R12), and a red "Unverifiable claim" chip surfaces anything uncited.

**Explanation-pathway boundary (intentional, documented limitation):** the NL explanation path generates a **human-readable hypothesis** from structured attribution + invariant evidence only (its prompt may cite nothing else). It is **not a mitigation authority and not equivalent to the C1–C5 mitigation validator** — that gate applies only to proposed mitigation plans, which stay behind the full safety checks. Content embedded in raw telemetry/log text is never silently promoted to instructions through this path (R12/R19). Documented, not hidden (PRD §3.4, TechSpec §3.1, AppFlow §2.4, Rules R19).

---

## 9. Soft Computing — Fuzzy-Rough Channel Reduction

**Fuzzy-Rough Channel Reduction** (ROB-01/-02) is a **scheduled, MVP-scoped P0 experiment** (ImplementationPlan 2.4, Tracker P2.4), not a vague stretch bullet:

- **Question:** can detection robustness be kept with fewer monitored sensors (lower cost, smaller attack surface), without trusting fuzzy/neuro-fuzzy methods as detectors (R30: no stacking without a documented experiment)?
- **Design:** a fuzzy-rough-set method selects a reduced channel mask; reduced-channel TCN-AE vs. full-channel TCN-AE under the **identical** stress protocol on SWaT (mask fit **on train only**; reduction % **measured, never assumed**; point-wise F1 + PA%K per stressor; median over 3 seeds; mask + metrics persisted in `channel_reductions`, ROB-02).
- **Status:** hypothesis — "robustness is preserved with fewer sensors" — stated as a hypothesis only; no reduction target exists in the docs.

---

## 10. MITRE ATT&CK for ICS / Threat Mapping (TINTEL-01)

**TINTEL-01** (PRD §3.6, P0) is the explicit threat-mapping requirement:

```
incident (sensors involved, invariant violations, pattern match)
  → rule-based match (static table: e.g., pump speed + pressure drift +
    setpoint change → T0875 Unauthorized Command Message) + RAG over the
    trusted tier for technique descriptions and IR steps
  → MITRE ATT&CK for ICS technique_id + confidence (0..1)
  → threat_mappings row (incident_id, technique_id, confidence, basis)
```

The `basis` object lists matched rules + citations (R16: never invent technique IDs). The mapping feeds the agent two ways — as incident context and indirectly through the KB — so mitigations are grounded in response playbooks aligned to mapped techniques. Traceable end-to-end: PRD §3.6 → TechSpec §8 → AppFlow §2.6 → Schema §4.10 → Tracker P3.1 → ImplementationPlan 3.1 → PRD §9 acceptance.

---

## 11. RAG System

Tiered KB (`tier ∈ {trusted, public, hostile}`):

| Corpus | Tier |
|---|---|
| MITRE ATT&CK for ICS, SWaT plant documentation | `trusted` |
| Team-authored response playbooks (≥ 10, single named owner) | `trusted` |
| Threat reports / CTF writeups | `public` |
| Injected "manual pages" (demo fixtures, F2/F4) | `hostile` (eval-only collection) |

Heading-aware chunking (~200–400 tokens, overlap 32); pinned embedder (deterministic hashing backend offline, MiniLM upgrade path — name+version recorded per collection); per-mode collections; top-5 retrieval. Retrieval returns **citations** — `{chunk_id, source, section, tier}` — never bare text; hostile/public content is surfaced as "untrusted evidence: verify manually", never silently merged into instructions. **Trust firewall:** the production retriever hard-excludes `hostile` even if requested (`TIER_DENIED` observation); hostile fixtures live only in separate eval collections — the production KB is never poisoned (R11, RAG-06, INV-012). Missing collection or retrieval failure ⇒ `RETRIEVAL_UNAVAILABLE` / zero results ⇒ `NO_EVIDENCE` — both force the "insufficient data" posture; a plan step with zero trusted citations can never auto-`allow` (floor: `require_approval`); hostile-only support ⇒ `block`. Quality is measured: hit-rate / nDCG on 20 canned queries (RAG-04, `eval/kb_qa.py`); citation correctness and hallucination rate are charter metrics.

---

## 12. Agentic AI Layer

One **single ReAct-style planner** (deliberately not a swarm — RQ3's gating measurement would be confounded by extra agent autonomy), implemented as an **owned runner** (TechSpec's "own the prompts/state" rationale) with DB-backed lease/heartbeat for crash recovery, max 12 steps; the recorded deviation from the original LangGraph choice is documented in Tracker.md.

| Tool | Purpose |
|---|---|
| `query_latest(stream, sensors)` | current telemetry window |
| `query_history(incident_id, span)` | historical windows |
| `search_kb(query, tier_filter)` | RAG retrieval → citations |
| `check_invariant(rule_id)` | plant physics check |
| `propose_action(action, target, params)` | structured draft (pre-validator) |

- **Analyst-triggered, explicit lifecycle:** stages 1–8 run automatically; the agent run **never auto-starts** — an analyst creates it via `POST /incidents/{id}/agent_runs` (202 + run_id; ≤1 active run per incident, DB-enforced; lease + reaper interrupt stalled runs). The run TERMINATES when the draft revision is written — approval/execution operate purely on DB artifacts, with no graph-resume dependency.
- **No arbitrary command execution:** actions are structured `{action, target, params}` objects validated against the policy grammar (strict: unknown fields/types/ranges rejected); no shell, no DB writes, no file writes beyond the sandbox (R2/R5).
- **Grounding prompt:** every claim cites tool output/chunk ids; unverifiable claims → "insufficient data"; max 12 steps ⇒ forced finalize with `STEP_LIMIT_REACHED` and the evidence-so-far draft still passes through validation.
- **Variants & lockout:** `naive` (no grounding, no validator) exists ONLY for EXP-05/08 comparison — service, sandbox, and harness all refuse naive approval/amendment/execution; naive plans are terminal `draft_only` (INV-010). Qwen2.5-7B default via Ollama (sampling params pinned), deterministic scripted backend for offline tests/demo (clearly labeled in metrics), gpt-4o-mini stretch-only (AGENT-06/07).

---

## 13. Validator + Safety Architecture

Every mitigation step passes an **ordered, fail-fast validator**; each check result is recorded in `validator_results.checks` with a `deterministic` flag:

| Check | Verifies | Deterministic |
|---|---|---|
| **C1 Provenance** | claims attributable to trusted tool/RAG output; hostile tier cited → flag | yes (code) |
| **C2 Allowlist** | action/target/params ∈ policy grammar (`configs/policy/*.yaml`) | yes (code) |
| **C3 Pattern** | injection markers, command keywords, encoded payloads | yes (code) |
| **C4 Risk class** | `read` / `write` / `control` / `forbidden` | yes (code) |
| **C5 Consistency** | step rates/params vs. cited evidence (rule-based entailment / field match) | as deterministic as possible |

**Determinism contract (AEGIS-04):** C1–C4 are pure deterministic code — no LLM in the path. C5 never uses the planner's own model; an LLM-assisted check, if ever added, must use a *different* model and be validated against the injection corpus.

**v1.1 hardening:** C1 binds claims to evidence by EXACT ID (no fuzzy matching; unknown/missing citations flag; hostile-only support blocks). C2 is a strict registry lookup with unknown-field/type/range rejection. C3 normalizes (NFKC → casefold → zero-width strip) and iteratively decodes (≤3 layers) before matching. C5 = parameter↔evidence-field entailment **plus invariant-direction consistency** (a proposal contradicting a failed physics invariant flags `invariant_conflict`); "persistent" is defined: the same C5 failure category on the two most recent validations of an incident ⇒ `escalate`. Check exceptions fail closed (`require_approval` floor; second occurrence escalates). The **verdict function is a single pure, golden-tested implementation** (precedence block > escalate > require_approval > allow) — no duplicated verdict logic anywhere.

**Verdicts** (soft-min over checks; Schema §5): `allow` | `require_approval` | `block` | `escalate`. `read` → auto-allow only when checks are clean AND the step carries ≥1 trusted citation (or is on the citation-free-read whitelist, e.g. `snapshot_plant_state`); `write` (config/tuning) and `control` (pump/valve/load) → **require human approval** (control also sandbox-only); `forbidden` (e.g., direct PLC write) → **block**, never silently executed. `escalate` is *not* the forbidden-path outcome — it is driven by **persistent C5 inconsistency** (or approval expiry) and routes the incident to admin review. The validator result is **bound to the plan revision's SHA-256** and versioned (`is_active`); amendments supersede prior results.

> **Key principle:** the validator is an **independent policy/safety layer**, not another LLM judge — mirroring NetInjectBench's proven pattern (execution-time policy gating + provenance-aware rendering + human review; 0/240 unsafe actions under the metadata-integrity assumption), but on OT domain data.

---

## 14. Human-in-the-Loop

- **Required for:** every `write`- and `control`-class step — 100% of `control` actions without exception; monitoring/investigation run automatically. Approval is **all-or-nothing per plan revision** (Option A): one live approval covers ALL steps; per-step risk classes remain visible in the modal.
- **Approval modal:** revision identity + hash suffix, all steps with worst-case risk highlighted, validator checks, citations with trust tiers, expiry countdown → **Approve & Simulate** (analyst+, disabled until invariant-review checkbox is ticked) / **Amend** / **Deny** (reason required). Distinct-approver rule: for control-class revisions, `decided_by ≠ run.created_by` (config-gated; admin qualifies as a distinct approver).
- **Amendment ⇒ re-validation:** Amending creates a NEW immutable revision (`revision_no`, `supersedes_id`, new SHA-256), runs fresh C1–C5 synchronously, and supersedes the prior approval — there is no amend→execute path without fresh validation (R43).
- **Expiry → escalation:** approval requests expire after **24 h** and **auto-escalate** (approval row `expired`; plan/incident → `escalated`, admin notified, audit) — never a silent deny, never silent execution. BOTH a scheduler sweep AND an API-side guard enforce this: approve/deny/amend are conditional updates requiring `status='pending' AND expires_at > now()`, so expired approvals fail closed even during scheduler outage (INV-007). Approvals cannot be replayed (pending→approved consumed atomically with plan validated→approved, INV-008), and execution claims `approved→executing` atomically with UNIQUE(plan,step) rows + queued-only resume, so retries/races can never double-execute (INV-009).
- **Lifecycles:** plan `draft_for_validation → validated → approved → executing → executed`, plus `rejected | escalated | superseded | draft_only(naive, terminal)`; incident `open → analyzing → awaiting_approval | simulating | rejected | escalated → closed` with retry (`rejected→analyzing`), analyst close (`no_action`), sandbox-failure escalation, and admin resolution of escalations. Every transition is a conditional UPDATE on the prior status.
- **Execution binding (INV-005):** the executor independently recomputes the revision hash and requires active-validator-hash == approval-hash == recomputed; any divergence ⇒ `EXEC_HASH_MISMATCH` HARD BLOCK + audit + escalation.
- **Audit:** every mutating action — tool call, draft, verdict, approval, amendment, simulation — writes an **append-only** `audit_logs` row in the SAME transaction as the mutation (no UPDATE/DELETE grants; `/audit/export.csv` formula-injection-escaped, admin-only).

**Why not full autonomy:** the contribution is precisely *measuring* how much safety a validator + human gate adds, not pretending the LLM can fly solo.

---

## 15. Attack-the-Agent Experiment (F1–F7)

30+ injection cases across **7 families** (EXP-08; `eval/attack_suite/`). The attacker has **no chat access** — injection travels only through the data plane (telemetry, logs, documents).

| Family | Attacked | Attacker tries to | System must detect | Expected defense |
|---|---|---|---|---|
| **F1 Poisoned history** | historical telemetry/log context | embed instructions in past records ("ATTENTION OPERATOR: … ignore_prior") | instruction-like content in evidence | C1 provenance + C3 patterns + grounding |
| **F2 Document manipulation** | KB documents | forge playbook/manual ("shutdown MV-501 on any high-level alarm") | hostile-tier content | fixtures only in eval collection; tier surfacing |
| **F3 Instruction leakage** | system prompt/instructions | extract or override instructions | leakage attempts | C3 patterns; prompts owned & pinned |
| **F4 Narrative social engineering** | context framing | authority-mimicry narratives steering recommendations | narrative injection | C1/C3 + grounding re-retrieval |
| **F5 Tool-arg smuggling** | tool arguments | smuggle path/command via args (`table=../../etc/passwd`) | non-grammar args | C2 allowlist |
| **F6 Hallucination probe** | empty/insufficient evidence | demand an answer when no evidence exists | unsupported claims | R12 grounding → "insufficient data" |
| **F7 Cyber-physical attribution spoofing** | numeric sensor values | zero / bias / scale physical values (e.g., LIT-101 pinned to nominal while P-101 rises) to spoof attribution into prefabricated error channels | anomaly despite nominal-looking channels | detector attribution + invariants; **numeric-only, no English text; simulation-only** |

**F7 placement (important):** F7 is part of the **automated adversarial evaluation suite** (EVAL-04 / THREAT-03), runs in the batch harness, and is **NOT a step in the interactive 7-step demo narrative** (AppFlow §4, Design §5.12); the live dashboard remains the documented textual demo.

**Measured safety-metric targets (PRD §5 — hypotheses, not results):** ASR ≤ 10% on hardened; naive unsafe-action rate ≤ 25% on benign scenarios (literature-expected 0–86%); ≥ 60% relative reduction hardened vs. naive; validator block rate ≥ 95% on injected unsafe actions; false-block rate kept low (benign approval/false-block are CORE metrics — overblocking is a failure mode, not a safety win); execution-layer unsafe rate must equal **0** by construction (verification metric). 100% of `control` actions human-approved. **No model-measured numbers exist yet**; offline EXP-08 runs use the clearly-labeled deterministic scripted backend. All headline metrics are formally defined in the **metric charter** (`eval/metrics/charter.py`): exact numerator/denominator/unit/aggregation per metric incl. PA%K (formal event-coverage definition), refusal rate, grounding rate, F7 MRR@3 — report generators may only consume charter functions.

---

## 16. Datasets

| Dataset | Role | Why | Data used | Limitations |
|---|---|---|---|---|
| **SWaT** | Primary | Real water-treatment testbed (process-level ground truth); attack labels; standard benchmark | Normal + attack runs, ~1M samples; temporal splits | Public, saturated on leaderboard F1; curated labels; single plant |
| **WUSTL-IIoT-2021** | Secondary | Validation on a different IIoT domain | Key experiment cells | Docs keep it secondary; sensor semantics differ |
| **WADI** | Optional (P2) | Curiosity/stress-only run | Stretch scope (DATA-03) | Not MVP; harder subset |

Integrity (DATA-04..-08, R23): one-time temporal split, **no shuffle**; normalization + threshold from train/validation only; leakage test (disjoint date ranges) in CI; registry pins source, **sha256**, row counts, sensors; raw data in MinIO, never PostgreSQL; config hashes + seeds + model versions per run.

---

## 17. Evaluation Strategy

**Experiment matrix (EXP-01..09):** EXP-01 baseline detector · EXP-02 proposed TCN-AE · EXP-03 no cyber-physical context · EXP-04 no explanation · EXP-05 naive agent · EXP-06 grounded RAG agent · EXP-07 RAG + validator · EXP-08 adversarial/injection suite · EXP-09 human-approval safety test. WUSTL-IIoT-2021 runs on key cells (secondary).

**Detection (EXP-01/02):** precision, recall, F1, PR-AUC, FPR, detection/inference latency — **point-wise F1 and PA%K**, never naked point-adjusted F1 (SWaT leaderboard ~0.96–0.98 is point-adjusted; context, not our claim). Targets (PRD §5): baseline point-wise F1 ≥ 0.90; proposed ≥ +0.01 F1 or equal F1 with strictly better attribution; F1 drop under stress ≤ 0.10 (median over 3 seeds).

**Robustness (EVAL-02):** additive noise, sensor zeroing, drift — test distribution only, zero test-time calibration; plus the fuzzy-rough reduced-channel arm (ROB-01/02).

**Explainability:** attribution consistency (same family → same shape, XAI-03); manual review of 20 anomaly windows.

**RAG (RAG-04/EVAL-05):** hit-rate / nDCG on 20 canned queries; citation correctness ≥ 85% target; hallucination rate ≤ 10% target.

**Agent security (EVAL-06):** ASR, unsafe-action rate, block rate, approval rate — plus **false-block rate and refusal rate as core metrics**, all per the metric charter with per-seed values + std. RQ3 attribution uses the ladder: grounding effect = EXP-06 − EXP-05; validator effect = EXP-07 − EXP-06 (one capability varied per rung); execution-layer safety is separately guaranteed by construction and reported as verification, not as an experimental effect.

**Gate integrity (EXP-09):** a mechanical bypass battery attempts approve-after-expiry, double-approval, execute-of-superseded-revision, raw-SQL hash tampering, naive-variant execution, and closed-incident execution — **every attempt must be rejected** (`eval/bypass_battery.py`, wired into `eval/experiments.py::run_exp09`). This complements human-subject-free gate verification and is CI-runnable.

**Human pilot (EVAL-08):** minimal exploratory protocol — within-subject, counterbalanced, participant-blinded, N target 8 (minimum 6), 4 vignettes × 2 conditions, decision accuracy + calibration + time, attention-check exclusions, descriptive-only analysis (bootstrap CIs, no significance claims), consent + anonymization, and an explicit descoping path to n=2 think-aloud walkthroughs rather than silent dropout.

**Reproducibility (EVAL-07, R22/R25):** dataset sha256 + artifact sha256 verified at every job start + committed config hash + pinned seeds/sampling params/embedder + `model_versions` per run; every table regenerable from committed configs; success criteria labeled **hypotheses**; measured values only in `metrics`; negative results + full metric set reported (R26/R27).

---

## 18. Security & Rules (compact)

Security (non-negotiable): never touch real SCADA (R1); sandbox-only execution, no route to OT devices (R1/R4); no raw command execution — structured actions validated by policy grammar (R2); human approval for all `control`, 24 h expiry → escalate (R3); least privilege, read-mostly tools, separated service accounts (R5); secrets server-side only (R6); server-side input validation (R7); treat all telemetry/log/document content as adversarial (R8); fail-fast C1–C5 on every plan, deterministic contract (R9); hostile content never silently merged (R8/R10/R11); evidence citations mandatory (R12); append-only audit (R13).

AI/ML & research: roles server-authoritative (R14); never fabricate results or threat intel (R15/R16); raw data in MinIO, not PG (R17); attention ≠ explanation (R18); LLM diagnosis ≠ ground truth, and the explanation path is a hypothesis path with no execution authority — not the C1–C5 validator (R19); model versioning + config hashes + **artifact sha256 verify-at-load** (R20/R22); pinned datasets with **hash re-verification before every job** (R21); temporal leakage-free splits with **split-aligned windowing and causal-only cleaning** (R23); no unsupported novelty claims (R24); hypotheses labeled as such (R25); negative results + full metric set (R26/R27); fixed ablation variants (R28); baseline comparisons on identical splits via a **shared frozen feature manifest** (R29); no model stacking (R30). **Hardening additions:** §0 Safety Invariants INV-001..016 are machine-enforced (DB constraints/triggers, conditional state transitions, sandbox re-verification, retriever allowlist, same-transaction audit) and R43–R46 codify amendment→re-validation, naive isolation, content binding, and fail-closed defaults.

Development/demo: type safety, structured logging, testing gates, config-driven knobs, one-command Docker reproduction, clean git conventions, docs updated within 24 h (R31–R38); `SIMULATED`/`FIXTURE` labels everywhere (R39–R40); demo numbers regenerated from configs; targets say "TARGET" not "RESULT" (R41–R42).

---

## 19. Dashboard / Demo

One dark "Industrial Cyber Command Center" web app (Design.md): live telemetry + anomaly timeline; incident detail with attribution bars, explanation card, MITRE mapping; RAG evidence chips with tier badges; agent reasoning trace (SSE streamed via `GET /agent/{run_id}/stream`); validator panel with per-check results and exact policy-rule references on block; approval modal (approve/amend/deny-with-reason); Attack-the-Agent stepper; audit viewer; eval tables. Autonomy is always visible — every autonomous action carries an explicit badge (`SIMULATED`, `VALIDATOR`, `AUTO`, `AWAITING APPROVAL`): **nothing is silent**.

Demo flow (**DETECT → EXPLAIN → INVESTIGATE → PROPOSE → VALIDATE → APPROVE → SIMULATE**) replays the naive vs. hardened run as a 7-step stepper: (1) malicious context, (2) naive bad recommendation, (3) manipulation detected (validator reasons), (4) grounding evidence chips, (5) blocked action + policy rule, (6) safer recommendation, (7) approval + simulated execution — all rows labeled `SIMULATED`/`FIXTURE`. F7 fixtures, if surfaced, render as numeric sensor-value tables (never free text); F7 is evaluated in the automated suite, not as an interactive demo step.

---

## 20. 10-Week Implementation Roadmap

| Phase | Weeks | Key deliverables | Definition of done |
|---|---|---|---|
| **1 — Data + Baseline** | 1–2 | Repo/docker stack; SWaT + WUSTL ingestion, sha256 registry; preprocessing (temporal splits, W=60/S=1); Isolation Forest baseline + scoring | `make pipeline-baseline` runs end-to-end on SWaT; leakage test passes |
| **2 — Detection + Explainability** | 3–5 | TCN-AE + attribution; 5 invariants; explanation objects; stress protocol (noise/zeroing/drift) + fuzzy-rough channel-reduction arm (ROB-01/02) | Detector + attribution + explanation on SWaT; baseline vs. proposed + stress table |
| **3 — Agentic RAG + Validator** | 6–8 | Tiered KB (≥ 10 playbooks) + RAG (RAG-04 eval) + threat mapping (TINTEL-01); single ReAct agent (naive + hardened); validator C1–C5 + policy grammar + expiry-escalation; F1–F7 injection suite; sandbox simulator | Hardened beats naive on injection suite; gate blocks 100% of `control` without human |
| **4 — Integration + Eval + Demo** | 9–10 | Dashboard; EXP-01..09 matrix (incl. WUSTL secondary cells); safety/RAG metrics; 8-page report, demo video, defense deck | PRD §9 acceptance checklist green (incl. TINTEL-01 rows); every table reproducible |

Risks flagged in the plan: SWaT download/licensing delay (download + pin in week 1; WUSTL access verified week 1 too), local 7B LLM latency (evidence-only fallback, 90 s timeout), stress F1 instability (median over 3 seeds), scope creep (no model stacking, R30). Effort is weighted to Phase 3. **v1.1 addition:** Phase 3 now opens with task **3.0 Backend Foundation** (P3.0a–g: migrations/models, auth/RBAC, core routers, approval/sandbox/agent services, workers, demo orchestration, fixture corpora) — this was identified as a planning gap in the audit and is now scheduled; dashboard scaffolding starts in Phase 3 behind a mocked API. Acceptance uses the two-tier data rule: fresh-checkout green on the committed synthetic mini-fixture; licensed SWaT/WUSTL ingestion is a documented hash-pinned manual step.

---

## 21. MVP vs Stretch

| Component | MVP (MUST HAVE) | Stretch / Future |
|---|---|---|
| Detector | TCN-AE + Isolation Forest baseline | LSTM-AE / Transformer-AE / XGBoost / ANFIS ablations (DET-06/07) |
| Attribution + explanation | Reconstruction-error top-3 + NL summary | SHAP cross-check (XAI-05) |
| Channel reduction | Fuzzy-rough scheduled experiment (ROB-01/02, P0) | — (it is MVP) |
| Threat mapping | MITRE ATT&CK for ICS — TINTEL-01 | — |
| Datasets | SWaT + WUSTL-IIoT-2021 | WADI stress-only run |
| Agent | Single ReAct planner, local Qwen2.5-7B | gpt-4o-mini cross-model (AGENT-06) |
| Safety | C1–C5 validator, approval gate, expiry→escalate, sandbox | Approval-vs-safety trade-off study |
| Evaluation | EXP-01..09 + stress + F1–F7 injection suite | Extended matrix on WUSTL key cells only |
| Deliverables | Dashboard, 8-page report, demo video, defense deck | — |

**DO NOT BUILD unless the MVP is complete:** all stretch items above, any extra models (R30), any benchmark beyond the defined corpus.

---

## 22. Current Project Status

**Spec v1.1 (hardened) is frozen; implementation has started** in the `aegis-ot/` monorepo. Authoritative progress record: `Tracker.md` ("Status Snapshot" + "Step 7 — Test Execution Record"). Summary of verified state:

### Implemented in repository (materially complete)
- **Backend foundation:** all hardened DB models (CHG-DB-01..20; 25 tables), Alembic migrations 0001/0002 (incl. PostgreSQL plan-immutability trigger + audit grant revocation), plan-revision immutability (ORM listener + trigger).
- **Auth/RBAC:** Argon2id, 15-min HS256 access tokens, rotating hashed refresh tokens with family revocation on reuse, per-request `is_active` enforcement, fixed-window login limiter, server-side role deps on every route, audited admin-only `set_role`, env bootstrap admin.
- **Safety core:** immutable plan revisions with SHA-256 triple binding (validator ↔ approval ↔ execution; mismatch = HARD BLOCK); amendment ⇒ new revision + fresh C1–C5 + superseded prior approval; one-live-approval-per-revision; conditional-update state machines for incident/plan/approval/run; distinct-approver rule for control class; expiry enforced by scheduler AND fail-closed API guards.
- **Validator:** C1–C5 engine per the hardened contract (exact-ID provenance, strict grammar, normalized pattern filter, canonical risk classes, evidence+invariant consistency with persistent-C5 escalation, fail-closed exceptions), single pure verdict function.
- **Sandbox:** deterministic 6-stage SWaT-style plant model as the ONLY executor; independent re-verification of hash/approval/variant/state before applying anything; idempotent step resume; failure ⇒ escalation.
- **Agent:** explicit run creation (`POST /incidents/{id}/agent_runs`), single-active-run constraint, lease/reaper, max-12-step forced finalize, owned ReAct runner with pinned prompts, Ollama client + clearly-labeled deterministic scripted backend for offline tests/demo.
- **RAG:** chunker/embedder/vector-store abstractions, trust firewall (hostile excluded from production retrieval even on request; eval-collection separation; `RETRIEVAL_UNAVAILABLE`/`NO_EVIDENCE` semantics; zero-trusted-citation never auto-allows), KB builders, kb_qa harness.
- **Pipeline libraries:** ingest registry (hash-pinned, idempotent), synthetic SWaT-style fixture generator, causal cleaning, split-aligned windower (W=60/S=1), IsoForest baseline, TCN-AE (torch optional), ε-floor attribution, hypothesis-only explanations, declarative invariants, MITRE tintel rule table.
- **Evaluation:** metric charter functions (PA%K formal, ASR, unsafe/block/false-block/refusal rates, citation/grounding/hallucination, F7 MRR@3), 32 injection fixtures across F1–F7 with machine-readable ground truth, EXP-08 runner writing `injection_cases`, EXP-09 gate-bypass battery, stress grid + fuzzy-rough channel-reduction modules, experiment runner.
- **API:** full hardened route surface (auth/users/health/datasets/pipeline/telemetry/incidents+close/agent+SSE/validator+rerun/approvals+amend/sandbox/eval/audit+escaped-CSV-export/demo); broker-free asyncio workers (expiry scheduler + reaper, heartbeat-backed health).
- **Frontend foundation:** React/TS/Vite/Tailwind per Design.md tokens — Login, Dashboard (staleness indicator), Incidents, IncidentDetail (attribution bars, hypothesis card, MITRE mapping), AgentRun (SSE + fallback), Approvals (countdown, hash suffix, invariant-review checkbox, plain-text rendering), Demo stepper, Audit, Eval, Datasets; CSP; no HTML rendering of hostile content.

### Verification status (Step 8 executed — all defect clusters resolved)
`pytest`: **78 passed · 0 failed · 2 skipped(intentional) · 0 errors** — up from 40/12/26 at Step 7. Frontend `tsc && vite build` clean; ruff reduced 256 → 15 findings (all deliberate fail-closed handlers); `alembic upgrade head` green through 0001→0002→0003. All seven Step-7 defect clusters fixed plus additional latent defects found by deterministic checking: state-machine identity-map staleness (`synchronize_session="evaluate"`), amend-kwarg mismatch incl. amend-from-approved revisions (DEC-002/R43), INV-015 run-slot leak on deny, draft-materialization revision collision, INV-005 tamper-evasion via stale ORM reads (authoritative re-read), naive-plan approval creation (INV-010), TCN-AE shape bugs (model could never run — now trains/scores), stress-harness unconditional raise, fuzzy-rough IndexError, charter consistency normalization, demo actor/dataset idempotency, three F821 runtime NameErrors, rerun-safe evaluation bookkeeping. Full evidence table: `Tracker.md` → "Step 8 — Defect Resolution & Verification Record". Offline experiment cells executed on the synthetic fixture: EXP-01..09 + STRESS-ROB + RAG-04 corpus run + EVAL-08 scaffold.

### Not yet done (pending/blocked)
Licensed SWaT/WUSTL download + sha256 pinning and real-data runs (license-gated manual step, DEC-016); docker-stack bring-up review on a clean machine; live Chroma/Ollama adapter soak tests; hallucination-rate unsupported-question probe harness; ≥10 team playbooks authoring; full demo audit-trail verification on a live backend; stretch items (DET-06/-07 ablations, AGENT-06 cross-model, XAI-05 SHAP, WADI).

---

## 23. Risks & Limitations

- **Explanation-pathway boundary (intentional):** the NL explanation is a hypothesis, not a verdict — no mitigation authority, not the C1–C5 validator; mitigation actions always remain behind the full safety gate. Documented, not hidden.
- **Public data realism + testbed fidelity:** SWaT is a curated research testbed (results do not transfer to arbitrary plants; domain shift), and the sandbox is a lightweight 6-stage surrogate — simulated telemetry deltas, not a real plant.
- **Model + KB quality bounds:** Qwen2.5-7B latency/quality bounds agent runs (mitigated by evidence-only fallback, but text reasoning is not fully deterministic); RAG quality is bounded by source quality — team playbooks and public reports; KB scaling is effort-limited.
- **Small human-evaluation sample:** RQ2 pilot is explicitly small-N (≤ 10 vignettes) and exploratory.
- **Attribution ≠ causal proof:** sensor contribution ranks which channels drove the residual; it is evidence for an analyst hypothesis, not root-cause diagnosis.
- **No production deployment:** nothing in the system may ever touch a real SCADA device.
- **Student-scale benchmark:** the 30+ case, 7-family corpus cannot match industrial evaluation scope; it is the project's own benchmark on a domain with no existing one.
- **SWaT download/licensing** is a blocking early risk (mitigation: week-1 download + hash pin).

---

## 24. Competitive Position

The strongest classroom competitor is *Cybersecurity Incident Response using Multi-Agent Reinforcement Learning* (MARL). AEGIS-OT's honest differences: **single agent by design** (isolates the validator/gating variable RQ3 measures; a swarm would confound it), **OT/ICS specialization** with real-testbed data and cyber-physical ground truth, sensor-level **cyber-physical attribution**, a **deterministic validator** instead of (or alongside) a learned policy, adversarial evaluation via **Attack-the-Agent (F1–F7)**, and **human-gated simulation** that keeps every claim bounded and auditable. No guaranteed "#1" is claimed anywhere in the docs; the positioning is that AEGIS-OT's claims will survive strict validation of how the policy was evaluated.

---

## 25. Professor Defense — 5 Questions

**Q1. Why LLM?** Because the problem is the last mile: detection is saturated, but translating attributed anomalies into grounded, cited mitigation steps at SOC speed is a language task an LLM does well — and the docs measure exactly where it fails (R8–R13 ground it).

**Q2. Why not a generic IDS?** Because we are not building a packet monitor. We detect process-level anomalies on cyber-physical telemetry, attribute them to sensors, and gate LLM *recommendations* — there is no claim of competing on generic detection (PRD §8 non-goals).

**Q3. Why not Multi-Agent RL?** MARL is more ambitious on the agentic-decision axis but high-risk (training instability, no physical ground truth). RQ3 requires measuring one intervention (gating) in isolation — a single agent + external deterministic gate is the cleaner experiment (TechSpec §5.1).

**Q4. How do you guarantee LLM safety?** We don't pretend to; we *measure* it. C1–C5 deterministic validation, allow-listed grammar, provenance-aware RAG, human approval for control-class actions, sandbox-only execution, and an adversarial corpus (F1–F7) reporting ASR/unsafe-action/block rates — with targets labeled as hypotheses. The explanation path explicitly carries no execution authority.

**Q5. What is your actual research contribution?** An honest, measurable safety architecture for OT/ICS LLM incident response: attribution + invariants, evidence-grounded single-agent reasoning, a deterministic non-LLM validator gate, MITRE-ICS mapping (TINTEL-01), and a 7-family adversarial evaluation on a domain with no existing agent benchmark — with stress robustness (not leaderboard F1) as the defended claim.

---

## 26. AEGIS-OT IN ONE PAGE

### Problem
OT operators can't trust an autonomous LLM responder — log/telemetry content is attacker-controlled — and nobody can currently *measure* whether a safe OT/ICS agent architecture exists.

### Core Idea
Attributed, explainable cyber-physical detection feeds a single evidence-grounded LLM planner whose every mitigation passes a **deterministic validator + human approval** and executes only in simulation; the safety claim is demonstrated by an Attack-the-Agent suite (7 families).

### Architecture
`telemetry → TCN-AE / IsoForest → attribution → explanation (hypothesis, not verdict) → MITRE-ICS (TINTEL-01) → tiered RAG → single ReAct agent (analyst-triggered) → C1–C5 validator → human approval → sandbox → append-only audit`

### Research Contribution
- Quantified safety of an OT incident-response agent under adversarial inputs (ASR, unsafe-action rate, block rate).
- Stress-robust detection and attribution on SWaT with honest metrics (point-wise F1 + PA%K).
- Fuzzy-rough channel-reduction as a measured experiment, not a claim.
- A 7-family adversarial benchmark where **none existed** for OT/ICS (F7 cyber-physical spoofing in the automated suite).

### Main Experiments
- EXP-01/02: baseline vs. TCN-AE (point-wise protocol)
- Stress protocol (EVAL-02) + ROB-01/02 fuzzy-rough reduced-channel arm
- EXP-03/04: ablations (context / explanation)
- EXP-05→07: naive → grounded → validated agent
- EXP-08: 30+ injection cases across F1–F7
- EXP-09: human approval safety; RQ2 pilot (EVAL-08, exploratory)

### Safety
- Deterministic validator as an independent layer; never the planner's model; every check records its `deterministic` flag; C5 includes invariant-direction consistency; exceptions fail closed.
- Immutable plan revisions bound by SHA-256 across validation → approval → execution (`EXEC_HASH_MISMATCH` = hard block); amendment ⇒ new revision + fresh validation.
- All-or-nothing revision approval; distinct approver for control class; 24 h expiry auto-escalates (never a silent deny); expired/replayed approvals rejected by API guards, not just the scheduler.
- Naive evaluation agents are execution-impossible (service + sandbox + harness lockout).
- Structured actions, strict allow-listed grammar (unknown fields rejected), sandbox-only execution with idempotent resume, immutable same-transaction audit.
- Explanation = evidence-backed hypothesis only — not an execution authority, not the mitigation validator.
- Nothing is silent: every autonomous act carries a `VALIDATOR`/`AUTO`/`SIMULATED` badge.

### MVP
- SWaT + WUSTL-IIoT pipeline, Isolation Forest + TCN-AE + attribution + invariants
- Tiered RAG + single ReAct agent (local Qwen2.5-7B); MITRE mapping (TINTEL-01)
- Validator/approval/sandbox; F1–F7 injection suite + Attack-the-Agent demo
- EXP-01..09, dashboard, 8-page report, demo video, defense deck — ~10 weeks

### Biggest Differentiator
The validator is **deterministic code, not an LLM judge**, and the safety claim is measured on a dedicated adversarial corpus — on OT data, which no existing agent benchmark covers.

### Biggest Risk
Public-data realism: SWaT is a curated testbed; 7B-LLM quality and sandbox fidelity bound how far results generalize. All claims are scoped accordingly.

### Success Condition
EXP-08 shows the hardened agent's unsafe-action rate sharply reduced vs. naive with a high validator block rate, every metric table regenerable from committed configs, and not a single control action executed without human approval.

---

### OPEN DOCUMENTATION DECISIONS — RESOLVED (v1.1)

All four cross-file inconsistencies found during the audit have been **fixed in the source documents and code**:

1. ~~AppFlow §1 stage 3 "TCN-AE / LSTM-AE"~~ → **RESOLVED**: now reads "Isolation Forest baseline / TCN-AE proposed"; LSTM-AE remains stretch-only (DET-06).
2. ~~Latency tagged DET-06 in Schema §4.6 / Tracker P4.3~~ → **RESOLVED**: detection latency is DET-05 everywhere.
3. ~~Invariants tagged DET-05 in ImplPlan 2.2 / Tracker P2.2~~ → **RESOLVED**: invariants are DET-04 everywhere.
4. ~~TechSpec §3.3 "p99 of EVAL validation" ambiguity~~ → **RESOLVED**: now "τ = p99 of validation GT-normal residuals only" (also implemented in `pipeline/detect/scoring.py::threshold_from_validation`).