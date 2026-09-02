# Deep Literature-to-Project Analysis — AEGIS-OT vs. 21 Research Papers

> **Deliverable:** provenance dossier mapping every AEGIS-OT component against the 21 supplied papers, with overlap resolution, novelty stress-testing, and a citation plan.
> **Project:** AEGIS-OT — Cyber-Physical Anomaly Attribution and Validator-Gated Mitigation Intelligence for SCADA/ICS.
> **Method:** full text extracted from all 21 PDFs with page markers (`analysis/extracted/P01..P21.txt`); all 234 pages rendered to PNG (`analysis/pages/`); per-paper forensic dossiers with verified verbatim quotes (`analysis/notes/P01..P21.md`); implementation inventory read from the actual codebase (`analysis/CODE_INVENTORY.md`). Page numbers in this report are extraction-page numbers from those dossiers.
> **Confidence labels:** HIGH = explicit, unambiguous evidence · MEDIUM = strong conceptual match, some interpretation · LOW = weak/indirect · UNCERTAIN = evidence insufficient.

---

## ⚠️ Reading-fidelity disclosure (honesty first)

Every page of every paper was **text-extracted and read** (character-verified quote banks, machine-checked against source text). However, **the runtime available for this analysis could not display rendered page images** ("the selected model does not support image input" — verified for the main agent and all subagents). Figure and table analysis therefore rests on (a) the PDF vector text layer, (b) figure captions, (c) the papers' own in-text discussion of each figure/table, and (d) in two dossiers (P17, and partially P20/P21) OCR of high-resolution page crops. **Every per-paper dossier flags this in its Uncertainties section.** Where a value exists only inside a raster table or chart (e.g., P01 Tables 7–9, P02 Tables II–VIII, P17 Fig. 4), this report says so rather than inventing numbers. All numeric values quoted in this report come from the text layer and were located at a specific page.

---

## 1. Executive Summary

**The 21 papers decompose into four clusters.** Cluster A — ICS anomaly detection & explainability (P01, P02, P07, P09, P10, P15, P16, P17, P18, P19, P20, P21): normal-only autoencoders and lightweight detectors on SWaT/WADI with SHAP/CAM/attention explanations. Cluster B — agent-security defenses (P11 TrustAgent, P12 Task Shield, P13 IPIGUARD, P14 VIGIL): constitutions, task-alignment shields, tool-dependency graphs, and verify-before-commit against indirect prompt injection. Cluster C — network IDS alternatives (P03, P04, P05, P08): LLM-as-IDS, reject-option NIDS, CNN-LSTM classifiers. Cluster D — autonomous defense (P06): RL responders in CybORG.

**Best-source findings (overlap-resolved).** For AEGIS-OT's TCN-AE detector, **P15 is the strongest direct source** — it is a dilated causal-convolution autoencoder on SWaT trained normal-only (F1 0.7436), making it the closest published prior to PC-05; the residual-ratio attribution of PC-08 is then differentiated from P15's SHAP-based attribution (ALTERNATIVE), not derived from it. For XAI discipline, **P16 (WaXAI) provides the strongest empirical warning**: SHAP's top-ranked feature contradicted the true attacked device (attack 24, p11) — direct published evidence for AEGIS-OT's "explanation is a hypothesis" rule (PC-09/PC-17). For the validator gate, the four agent-security papers supply convergent support with divergent mechanisms: P13's plan-level tool allowlist ≈ C2, P14's two-stage verify-before-commit (compliance ∧ entailment) ≈ C2+C5, P12's tool-call/argument alignment ≈ C5 — but **all four enforce via LLMs; none uses deterministic code, human approval, or content binding**, which is exactly where AEGIS-OT's design differs.

**Novelty verdict (relative to this corpus, per §13 categories).** CONFIRMED-NOVEL-AT-CORPUS-LEVEL: (1) the **F7 numeric cyber-physical sensor-spoofing attack family** — every agent-security benchmark in the corpus is text-only (verified in P12 §5.1, P13 §4.1, P14 Table 1; P11 has no adversarial evaluation at all), so a no-text numeric spoofing family exists nowhere in the 21 papers; (2) the **SHA-256 content binding of validator verdict ↔ human approval ↔ execution** with hash-mismatch hard blocks — no paper contains hashing, approval workflows, or immutable revisions (grep-verified in P11–P14 dossiers); (3) the **deterministic (LLM-free) validator as an independent layer** — corpus-wide, every defense mechanism is LLM-mediated (P11 GPT-4 inspector, P12 same-model shield, P14 role-specialized LLM verifiers, P13 LLM planner) or absent; (4) the **OT/ICS agent-safety benchmark itself** — no paper evaluates any agent on OT/ICS data. POTENTIAL (system-level): the full integration detection→attribution→MITRE→RAG→agent→validator→approval→sandbox. Everything else is EXISTING IDEA, IMPLEMENTATION, MODIFICATION, or INTEGRATION and is labeled as such in §21–25.

**Critical honesty finding from the code inventory** (§13): production attribution is currently degenerate for Isolation-Forest anomalies (`run_detection` tiles the window score per sensor, so top-3 is alphabetical), EXP-01/02 fit and threshold on the same validation split, the `check_invariant` agent tool has empty sensor scopes (physics rules trivially pass), and EXP-09/F7-metrics are not wired into the CLI/API. These are provenance-relevant: AEGIS-OT can cite the literature for design, but three headline mechanisms are not yet fully effective in the wired pipeline.

---

## 2. Project Understanding

### 2.1 Problem
OT/ICS environments are IT-integrated faster than they can be defended; SWaT detection leaderboards are saturated (~0.98 point-adjusted F1, a protocol shown to overstate performance); LLM SOC assistants reading attacker-controlled logs/telemetry are manipulable via indirect prompt injection; and **no benchmark exists to measure whether an OT/ICS incident-response LLM agent is safe**. AEGIS-OT is a measurement-and-safety-intervention study: turn telemetry into attributed, explained incidents; let a grounded LLM agent *draft* mitigations; gate every draft deterministically; require hash-bound human approval; execute only in simulation; and attack the system itself to publish honest safety numbers.

### 2.2 Objectives (research questions)
- **RQ1:** can an LLM OT incident-response agent be made safe under adversarial inputs? (EXP-08 attack suite: ASR, unsafe-action rate, block rate)
- **RQ2 (exploratory pilot, ≤10 analysts):** do attribution + explanations improve analyst decisions? (EVAL-08)
- **RQ3:** do grounding and validator gating measurably reduce unsafe actions? (ladder EXP-05 naive → EXP-06 grounded → EXP-07 +validator)

### 2.3 Architecture (one pass)
DATA (SWaT/WUSTL, MinIO, sha256-pinned) → PREPROCESS (z-score train-fit, W=60/S=1) → DETECT (TCN-AE primary vs Isolation-Forest baseline; τ = p99 of validation residuals) → ATTRIBUTE (per-sensor residual share r_i/Σr_j, top-3) → EXPLAIN (hypothesis NL + invariants, never a verdict) → INCIDENT (gap ≤ 60 s grouping, severity) → MITRE-ICS map (rule table + basis) → [analyst-invoked] AGENT (single ReAct, 5 tools, ≤12 steps, Qwen2.5-7B/scripted) → VALIDATOR C1–C5 (deterministic, fail-fast) → HUMAN APPROVAL (all-or-nothing, SHA-256-bound, 24 h expiry → escalate) → SANDBOX (6-stage SWaT-style simulator, only executor) → AUDIT (append-only, same transaction).

### 2.4 Components
50-component inventory in `analysis/PROJECT_COMPONENTS.md` (PC-01..PC-50): detection layer PC-01–15, explainability PC-16–18, threat intel PC-19–20, RAG PC-21–24, agent PC-25–29, validator/safety PC-30–42, evaluation PC-43–50. The code-level realization (with deviations) is in `analysis/CODE_INVENTORY.md`.

### 2.5 Algorithms
TCN-AE (causal Conv1d k=3, dilations 1/2/4, latent 8, MSE, normal-only); residual-scale-normalized scoring + p99 threshold; ε-floor contribution shares; 5 declarative physics invariants + direction rules; 4-rule MITRE tintel table; hashing-embedder tiered RAG with mode allowlist firewall; ReAct runner (12 steps, lease/heartbeat/reaper); C1 exact-ID provenance, C2 strict grammar registry, C3 NFKC+casefold+zero-width-strip + ≤3-layer decode pattern filter (17 markers), C4 risk classes (unregistered ⇒ forbidden), C5 field-entailment (tol 1e-6) + invariant-direction conflict + persistent-C5 escalation; single pure verdict lattice (allow < require_approval < escalate < block); JCS-canonical SHA-256 triple binding; conditional-update approval state machine; 6-stage plant model with per-step idempotent resume; 17-function metric charter (incl. PA%K, ASR, block/false-block/refusal, F7 MRR@3).

### 2.6 Experimental design
EXP-01 (IF baseline) / EXP-02 (TCN-AE) / EXP-03 (no cyber-physical context) / EXP-04 (no explanation) / EXP-05–07 (agent ladder) / EXP-08 (32-fixture attack suite, F1–F7) / EXP-09 (6-attempt gate-bypass battery) / STRESS-ROB (noise σ ∈ {0.05,0.10,0.20}, zeroing {0.05,0.10}, drift {0.001,0.005}, seeds 1–3, median) / RAG-04 (20-query hit-rate/MRR) / hallucination probe (7 questions) / EVAL-08 pilot (6 vignettes scaffolded). All metrics from `eval/metrics/charter.py`.

### 2.7 Claimed contributions (to be stress-tested)
(a) measurable safety architecture for OT/ICS LLM incident response; (b) stress-robust detection + attribution with honest metrics (point-wise F1 + PA%K); (c) fuzzy-rough channel reduction as a measured experiment; (d) 7-family adversarial benchmark on a domain with none; explicitly **no** SOTA/first-ever claims (Rules R24).

---

## 3. Literature Corpus Overview

| ID | Short title | Venue / year | Pages | Cluster | One-line contribution |
|----|-------------|--------------|------:|---------|----------------------|
| P01 | Shapelet-XAD (IEEE Access 2025, 10.1109/ACCESS.2025.3560260) | IEEE Access 2025 | 18 | A | Attention-selected shapelets + RF for explainable anomaly detection on HAI; critique of SHAP/LIME as "likelihood, not cause" |
| P02 | LU-IDS (IEEE TII 2023, 10.1109/TII.2022.3200363) | IEEE TII 19(3) 2023 | 12 | A | CAM-distilled CNN rules encoding control logic; 35/35 SWaT, 15/15 WADI |
| P03 | LLM-IDS via ATT&CK ICS (ICUFN 2024, 10.1109/ICUFN61752.2024.10625633) | ICUFN 2024 | 3 | C | Preliminary: ATT&CK-ICS-organized TTP corpus + fine-tuned LLM for analyst queries; no experiments |
| P04 | Reject-option SCADA NIDS (IJCNN 2024, 10.1109/IJCNN60899.2024.10650735) | IJCNN 2024 | 8 | C | Dynamic selection + classification-with-reject-option routing uncertain traffic to honeypot |
| P05 | Parallel CNN-LSTM + self-attention (EIECS 2023, 10.1109/EIECS59936.2023.10435492) | EIECS 2023 | 5 | C | CNN+LSTM+attention IDS on UNSW-NB15; 98.66% acc headline |
| P06 | Normalized PPO defense (ICPADS 2023) | ICPADS 2023 | 8 | D | RL autonomous responder (N-PPO) in CybORG/CAGE + bandit attacker-type allocation |
| P07 | Interpretability-aware AE (IEEE Access 2023) | IEEE Access 2023 | 11 | A | IAAE: GradCAM-derived interpretability loss inside an SSIM+MSE AE (industrial images) |
| P08 | ML/DL ICS cybersecurity (ICEMCE 2023) | ICEMCE 2023 | 6 | C | Two-phase supervised classification — on a CAN dataset despite ICS framing; rigor counterexample |
| P09 | Decision-fusion real-time IDS (IEEE TICPS 2024) | IEEE TICPS 2024 | 11 | A | Open EDS hardware-testbed dataset + DT/SVM/LSTM/XGBoost hard/soft voting IDS |
| P10 | CGAAD graph-aware DL (IEEE IoT-J 2024) | IEEE IoT-J 2024 | 21 | A | Betweenness-centrality features + sparse-AE + GCN; 99.91%/99.19% acc on SWaT/WADI (shuffled splits) |
| P11 | TrustAgent (arXiv:2402.01586v4, 2024) | arXiv 2024 | 17 | B | Agent Constitution + pre/in/post-planning safety; GPT-4 inspector; LLM-judged metrics |
| P12 | Task Shield (arXiv:2412.16682v1, 2024) | arXiv 2024 | 16 | B | Task-alignment defense vs indirect injection on AgentDojo; ASR 47.69%→2.07% (GPT-4o) |
| P13 | IPIGUARD (arXiv:2508.15310v1, 2025) | arXiv 2025 | 16 | B | Tool-dependency-graph plan-then-execute defense; avg ASR 0.69% on AgentDojo |
| P14 | VIGIL (arXiv:2601.05755v2, 2026) | arXiv 2026 | 19 | B | Verify-before-commit + SIREN benchmark (959 tool-stream injection cases) |
| P15 | TCAE + Kernel SHAP (IJAAS 2025, 10.11591/ijaas.v14.i4.pp1420-1432) | IJAAS 14(4) 2025 | 13 | A | Dilated causal-conv AE on SWaT + per-attack Kernel SHAP; **closest prior to AEGIS-OT's detector+XAI** |
| P16 | WaXAI (ACM CPSS'24, 10.1145/3626205.3659147) | ACM CPSS 2024 | 13 | A | ECOD/DeepSVDD per-stage + 4-XAI comparison with IOU/accuracy faithfulness on SWaT |
| P17 | PbNN hybrid physics+data (IEEE TSMC-S 2022, 10.1109/TSMC.2021.3131662) | IEEE TSMC 52(9) 2022 | 12 | A | P&ID invariants + DCNN surrogates + CUSUM residuals; live-SWaT 100% Dr / 0% Fr |
| P18 | LSTM-AE + OCSVM (IEEE CARS 2025, 10.1109/CARS67163.2025.11337908) | IEEE CARS 2025 | 6 | A | LSTM-AE latent → OCSVM on SWaT; 96% threshold metrics vs AUC 0.8628 |
| P19 | Causal-Bayesian risk (IEEE ICM 2025, 10.1109/ICM66518.2025.11322488) | IEEE ICM 2025 | 4 | A | NOTEARS DAG on SWaT-Dec2019 + causal-break detection + calibrated risk |
| P20 | Spatio-temporal AE (IJCNN 2023, 10.1109/IJCNN54540.2023.10191873) | IJCNN 2023 | 8 | A | LSTM+attention+GCN AE, per-sensor dynamic thresholds, LIT-301 localization |
| P21 | Transparent ICS AE (MIUCC 2024, 10.1109/MIUCC62295.2024.10783503) | MIUCC 2024 | 7 | A | CNN-AE/LSTM-AE + SHAP/counterfactual + remove-one-feature validation probes |

Provenance note: bibliographic details above are transcribed from each paper's page 1 and PDF metadata as recorded in `analysis/notes/PXX.md`. P11/P12/P13/P14 are arXiv preprints — no venue is stated in their texts (flagged in their dossiers).

---

## 4. Paper-by-Paper Deep Analysis (condensed; full dossiers in `analysis/notes/`)

Each entry: what the paper does → strongest AEGIS-OT mappings → key page-referenced evidence → limitations relevant to the project. Page-by-page relevance logs, complete equations, figures/tables, and 10–13 verbatim quotes per paper are in the per-paper dossiers.

### P01 — Explainable Anomaly Detection via Operational Sequences (IEEE Access 2025)
Transformer-attention selects high-attention windows as multivariate "shapelets"; a Random Forest over shapelet Euclidean distances classifies anomalies on HAI 23.05 (window 20, temporal split 2.3:7.2, 48 attacks). **Core value to AEGIS-OT:** its thesis that feature-importance XAI "predicts the likelihood of a particular feature causing an anomaly, but not the cause" (p2; restated p15) is a citable, independent articulation of AEGIS-OT's attribution-discipline (PC-09/PC-17). Also a DIRECT map for the SHAP/LIME/counterfactual comparison set (PC-18, §II-B pp. 3–5, Table 2 p6). Limitations: no numeric detection results outside table images; attention treated as explanation-bearing (the conflation AEGIS-OT prohibits); HAI-only.

### P02 — LU-IDS (IEEE TII 2023)
IEEE 754 byte-tensor CNN distilled via Grad-CAM into conjunction rules over sensor/actuator conditions; detects 35/35 SWaT and 15/15 WADI attacks with 2.06%/4.29% FPs (p9). **Core value:** the discovered rules are invariant-style physics — e.g., "the two states 'MV101=On' and 'LIT101>H' will never appear simultaneously in normal industrial procedures" (p9) — a data-driven relative of AEGIS-OT's declarative invariants (PC-10, STRONG CONCEPTUAL/HIGH); also a DIRECT SWaT+WADI dataset source with time-ordered 9:1 splits, and a ready baseline set (W-PCA, UAE, 1D-CNN, AADS, DAICS, p7). Limitations: needs historical labeled attacks; CAM-based attribution (attention family); inverted TP/TN convention (p8) makes its numbers non-comparable without conversion.

### P03 — LLM IDS via ATT&CK ICS matrix (ICUFN 2024)
Collects real ICS TTPs (MITRE, GitHub, CISA) organized on the ATT&CK ICS matrix (12 tactics, 81 techniques) and proposes fine-tuning an LLM for analyst Q&A; **no system built, no experiments** (3 pages). **Core value:** STRONG CONCEPTUAL support for MITRE-ICS mapping as LLM/analyst knowledge (PC-19, HIGH) — and a motivating contrast: AEGIS-OT maps incidents via deterministic rules with `basis` citations and never lets the LLM invent technique IDs (R16), whereas P03 would train the LLM on the matrix itself.

### P04 — SCADA NIDS with reject option (IJCNN 2024)
Two-module NIDS: dynamic selection among iptables/Snort/Gaussian-NB, plus a confidence-based Verifier that **rejects unreliable classifications and routes them to a honeypot** (p5). Verifier: 1% error at ~0.5% rejection. **Core value:** the closest corpus analogue to AEGIS-OT's verdict semantics — reject ≈ require_approval/escalate; capability is *reduced* under uncertainty (PC-36 STRONG CONCEPTUAL/HIGH; PC-42 PARTIAL). Also Eq. (3) (p5) is a principled threshold objective (argmin error+rejection), a cousin of AEGIS-OT's τ=p99 rule. Limitations: network-flow domain (not process telemetry); internal inconsistencies (RQ count, split typos); single testbed.

### P05 — Parallel CNN-LSTM + self-attention (EIECS 2023)
CNN (spatial) + LSTM (temporal) with multi-head attention, fused, on byte-embedded UNSW-NB15 with a **random 8:1:1 split**; headline 98.66% acc / 95.91% F1 / FPR 2.28% (p1, p4). **Core value:** ALTERNATIVE/HIGH for PC-15 (the CNN-LSTM detector family) and, methodologically, a **negative example**: non-OT dataset, random splits (leakage risk), naked headline metrics, chart-only baselines — exactly the evaluation practice AEGIS-OT's charter supersedes (PC-13 COMPLEMENTARY).

### P06 — Normalized PPO autonomous defense (ICPADS 2023)
RL defender vs red attackers in CybORG/CAGE; Normalized PPO (advantage/state/reward normalization, Eqs. 7–9, Alg. 1 p4) wins all nine perturbed scenarios (Table II p7); bandit attacker-type allocation: 100% accuracy. **Core value:** the corpus's embodiment of the **autonomous-responder philosophy AEGIS-OT rejects** (PC-01 ALTERNATIVE/HIGH; PC-33 ALTERNATIVE/HIGH — its action space includes autonomous Restore/Remove with no approval path). Also STRONG CONCEPTUAL for simulation-only execution (PC-40: CAGE emulation) and closed action grammar (PC-28). Limitations: 52-bit toy state, 3 fixed attackers, max-of-5-runs reporting without variance.

### P07 — Interpretability-aware AE (IEEE Access 2023)
IAAE embeds a GradCAM-derived interpretability loss (LIA = λµ², Eq. 8 p3) into an SSIM+MSE AE so that attention maps become trustworthy explanations; image-level AUC 0.739 on BTAD. **Core value:** DIRECT/HIGH for PC-18 (attention-analysis XAI exemplar) and a principled **counterpoint** to "attention ≠ explanation" (PC-17): P07 shows attention can be made explanation-like by training it — useful nuance for AEGIS-OT's R18 rule. Normal-only AE paradigm matches PC-05 (STRONG CONCEPTUAL). Limitations: vision domain (not time series); data-dependent thresholds; no robustness tests.

### P08 — ML/DL ICS cybersecurity (ICEMCE 2023)
Supervised DT/KNN/LSTM/CNN/CNN-LSTM two-phase classification **on an automotive CAN dataset despite ICS framing**; contradictory accuracy claims (100% DT/KNN p1; CNN-LSTM 95.55% p5; 97.30% p6). **Core value:** primarily a **rigor counterexample** (PC-48 COMPLEMENTARY-counterexample; PC-01 contrast) — ICS-vs-CAN dataset mismatch, no hyperparameters, mutually inconsistent numbers. Weak ALTERNATIVE for PC-15 (CNN-LSTM appears).

### P09 — Decision-fusion real-time IDS (IEEE TICPS 2024)
Releases a full-hardware ethanol-distillation ICS dataset (117.1 h, 843,321 records, 47 parameters, 7 attack types, open-sourced) and fuses DT/SVM/LSTM/XGBoost via hard/soft voting (Eqs. 1–5 p6); soft voting beats individual classifiers on average by +24.23% precision / +14.37% F1 (p9); deployed live with 0.5 s polling. **Core value:** ALTERNATIVE/HIGH for PC-15 (ensemble/decision-fusion design); COMPLEMENTARY for dataset ecosystem (positions against SWaT/WADI/HAI/EPIC, p2/p5) and for XGBoost/LSTM variant evidence (PC-07). Note the autonomous framing contrast: its alarm module auto-dispatches to the PLC (p7).

### P10 — CGAAD (IEEE IoT-J 2024)
Betweenness-centrality node features + sparse-AE enhancement + GCN classifier; SWaT 946,719 samples / WADI 314,404; **99.91%/99.19% accuracy, FAR 0.04%/0.48%** (p19/p16) — under **random shuffling + 80/10/10 splits** (p11). **Core value:** ALTERNATIVE/HIGH for PC-15 (graph-aware DL); DIRECT/HIGH for PC-02 (SWaT/WADI statistics); and a headline example of the saturated-number phenomenon AEGIS-OT critiques (PC-01): shuffled time-series splits + 99.9% accuracy is precisely what the point-adjustment/stress critique targets. Stated limitation: topology data scarcity; WaDi degradation.

### P11 — TrustAgent (arXiv 2024)
Agent Constitution (rule-based regulations) enforced pre-planning (regulation + hindsight learning), in-planning (top-5 Contriever retrieval of regulations per step), post-planning (GPT-4 safety inspector with revision loops + halt rule). Safety rises for all 5 backbones (GPT-4 avg 2.15→3.43, Table 2 p7) **without hurting helpfulness**; post-planning inspection lifts all models above safety 2 (Table 4 p7). **Core value:** STRONG CONCEPTUAL/HIGH for PC-29 (layered agent-safety defenses) and the corpus's clearest **ALTERNATIVE/HIGH to PC-35**: its gate is a GPT-4 inspector — the exact design AEGIS-OT rejects. Also the strongest corpus evidence that safety and utility need not trade off ("does not come at the cost of reduced helpfulness", p6). Limitations: 70 datapoints, LLM-as-judge metrics, **no adversarial/injection evaluation at all**, no human approval, no hashing.

### P12 — Task Shield (arXiv 2024)
Reframes agent security as **task alignment**: every instruction/tool call must contribute (fuzzy ContributesTo score) to user goals; enforced per message level with privilege hierarchy Ls≻Lu≻La≻Lt. On AgentDojo (GPT-4o): ASR 47.69%→2.07% with utility under attack *rising* 50.08→69.79 (pp. 6–7); baselines: PI Detector collapses utility (21.14), Delimiting fails (ASR 41.65). **Core value:** STRONG CONCEPTUAL/HIGH for C5-analog (tool-call/argument alignment, Fig. 6 p16: "If the arguments are inconsistent or irrelevant, assign a score of 0"), PC-49 DIRECT/HIGH (AgentDojo/InjecAgent coverage — none OT/ICS), and the CU/U/ASR metric design (PC-44) that AEGIS-OT's false-block-rate discipline mirrors. Limitations (p8): same-model LLM shield (susceptible to adaptive attacks), one benchmark/model family, **no human oversight anywhere**, text-only attacks (no F7 analogue), ε threshold undisclosed.

### P13 — IPIGUARD (arXiv 2025)
Models execution as traversal of a pre-planned **Tool Dependency Graph**; planning consumes only trusted inputs; execution permits only Query (read-only) tool expansion; Fake Tool Invocation defuses tool-overlap injections. On AgentDojo: avg ASR 0.69% / UA 58.77% (Table 1 p8), BU 67.01 vs 68.04 no-defense; ~2× token overhead. **Core value:** STRONG CONCEPTUAL/HIGH for C2 (agent "cannot invoke tools not pre-approved in the plan", p2) and for the read/write tool segregation (PC-27: "only Query Tool invocations are allowed during execution", p5) — the corpus's cleanest structural analogue of AEGIS-OT's read-mostly tool surface + allowlist. Also explicitly rejects LLM-as-judge ("remains vulnerable if the LLM-judge itself is compromised", p12). Limitations: text-output IPI out of scope; needs strong planners; no OT/ICS, no approval/hashing; Fake Tool Invocation fabricates tool responses into context — a caution for AEGIS-OT's truthful-audit design.

### P14 — VIGIL (arXiv 2026)
**Verify-before-commit**: Intent Anchor synthesizes query-specific invariants; Perception Sanitizer strips illocutionary force ("If uncertain whether content is factual, err on the side of deletion", p17); Speculative Reasoner explores a hypothetical sandbox; two-stage Grounding Verifier V = V_compliance ∧ V_entailment approves trajectories before commitment. Introduces **SIREN**: 959 tool-stream injection cases across 5 vectors + 949 data-stream cases (Table 1 p4). Results: TS ASR 8.13 (Qwen3-max) / 11.99 (Gemini), UA 27.53 / 18.46; ablation: no-verifier ASR 45.05 (Table 3 p8). **Core value:** STRONG CONCEPTUAL/HIGH for C5 (entailment-of-necessity ≈ AEGIS-OT's params-vs-evidence consistency), C2 (invariant compliance), PC-28 (action grammar/capability enums), PC-43 (SIREN taxonomy ≈ template for F-family fixtures: Explicit Directive ≈ F3; Runtime/Error Hijacking ≈ F1/F2 dynamics). Strongest recent counterpoint making AEGIS-OT's determinism salient: **all verification is LLM-based** (pp. 5–6), with a >24-point benign-utility cost on one backbone (BU 40.82 vs vanilla 65.31). Limitations: LLM-compute overhead; immutable constraints vs open-ended tasks; internal numeric inconsistencies (22% vs 18% ASR reduction).

### P15 — TCAE + Kernel SHAP (IJAAS 2025) — **closest prior for the detection+XAI core**
Dilated causal-convolution AE (3+3 blocks, dilations 1–16, kernel 40, MSE over 12×51 windows) trained normal-only on SWaT; anomalies via KDE+DBSCAN on reconstruction loss; **Kernel SHAP per identified attack window** (flattened 612-d, K=100 K-means background, ~9,400 coalitions, ~40 s/window on an A100). Results: TCAE P 0.9435 / R 0.6136 / F1 0.7436 vs LSTM-AE 0.6740, USAD 0.6627, **Isolation Forest 0.5520** (Table 3 p5); 31/41 attacks detected (p7); attack-6 SHAP: AIT-202 9.565626e-03 top (p8). **Mapping:** PC-05 DIRECT/HIGH (closest prior architecture; AEGIS-OT differs in window 60 vs 12, z-score vs min-max, p99 threshold vs KDE+DBSCAN); PC-18 DIRECT/HIGH (Kernel-SHAP worked precedent incl. cost accounting — directly reusable for AEGIS-OT's XAI-05 stretch); PC-08 ALTERNATIVE/HIGH (SHAP ranking vs residual-ratio decomposition — same output object, different mechanism); PC-04 COMPLEMENTARY (external IF-on-SWaT reference number); PC-09 contrast (P15 equates SHAP attribution with "root causes", p2 — the conflation AEGIS-OT's PC-09 avoids). Limitations: recall 0.6136 with no missed-attack analysis; undisclosed DBSCAN/KDE hyperparameters; Table 5 sums to 36 vs "41 documented"; ~40 s/window incompatible with 1 Hz alerting; no faithfulness metric, no user study, no code.

### P16 — WaXAI (ACM CPSS 2024) — **strongest XAI-faithfulness evidence**
Lightweight per-stage ECOD/DeepSVDD (PyOD) on SWaT (496,800 train / 449,919 test; first 21,600 s removed; min-max train-fit), 95th-percentile GHOST threshold + 100 s persistence; then a **quantitative 4-XAI comparison** (kernel SHAP, SP-LIME, ALE, IG) by top-5/top-10 IOU and accuracy against ground-truth attacked devices (Eqs. 12–13, p8). Results: ECOD 30/36 attacks (83.33%), F1 0.74; SHAP best (Acc 87.77%/82.76%) but **IOU only ~6–7%**; IG fastest (5.33 s); LIME slowest (2,266–3,528 s); **failure case**: for attack 24, "the SHAP identifies MV-201 as the most critical feature … This contradicts the actual attack point" (P-203/P-205) (p11). **Mapping:** PC-18 DIRECT/HIGH (the exact SHAP-vs-LIME-vs-ALE-vs-IG protocol AEGIS-OT's XAI-05 envisions, with a measurement method); PC-17 STRONG CONCEPTUAL/HIGH (published proof that an XAI explanation can mislead — citable justification for AEGIS-OT's "explanation = hypothesis" + corroboration design); PC-08 ALTERNATIVE/HIGH (top-k localization protocol); PC-02 PARTIAL/HIGH (full SWaT statistics). Limitations: TP/TN definitions inverted (p7); threshold tuned on P1 only; SWaT-only; significant false alarms; code released (footnote 2, p5).

### P17 — PbNN hybrid physics+data (IEEE TSMC-S 2022) — **strongest invariant-layer prior**
P&ID-derived invariants (Eq. 1–3 p4: tank-level dynamics x1(t+1) = x1(t) + δ(x2(t) − x3(t))) learned by DCNN surrogates; residuals monitored by two-sided CUSUM (Eqs. 6–7 p5) with windowed alert logic; live-SWaT evaluation on 6 single-point + 4 multipoint stealthy attacks (Tables I–II p6). Results: **100% detection rate, 0% false alarms** (p11), 0% FPR under manual-mode shift (p9), detection time 6.7 s vs DAD 4.1 s. **Mapping:** PC-10 DIRECT/HIGH (the corpus's strongest invariant prior — six invariants over P1–P3, Table III p7; AEGIS-OT's 5 declarative rules are a simplified declarative counterpart, and P17 shows how to learn invariant forms when nonlinear); PC-09 STRONG CONCEPTUAL ("not only detects an anomaly but also localizes it for forensics", p5); PC-06 STRONG CONCEPTUAL (residual+CUSUM alternative to p99 threshold); PC-12 STRONG CONCEPTUAL (mode-shift experiment = real drift stress test, motivating AEGIS-OT's stress protocol). Limitations: empirical UCL/LCL/Tw/Sw tuning needing 2-h live recalibration; live-plant-only test (not reproducible from public data); scope = 5 sensors.

### P18 — LSTM-AE + OCSVM on SWaT (IEEE CARS 2025)
LSTM-AE (20-step windows, 64→16/16→64) on normal SWaT; OCSVM on latent vectors decides anomaly (f(z)<0). Reports 96% across threshold metrics but **AUC 0.8628** (p4). **Mapping:** PC-07 DIRECT/HIGH (exactly the LSTM-AE stretch-ablation variant, with specs reusable); PC-15 DIRECT/HIGH (OCSVM-hybrid recipe, Eqs. 8–11 + Alg. 1); PC-13 STRONG CONCEPTUAL/MEDIUM (the 96%-vs-0.8628 gap is a concrete instance of why AEGIS-OT reports point-wise F1 + PA%K instead of naked thresholded metrics). Limitations: split hygiene unclear (normal-only claim vs mixed split); OCSVM kernel/ν unreported; narrow baselines (authors admit).

### P19 — Causal-Bayesian risk (IEEE ICM 2025)
NOTEARS causal DAG from nominal SWaT-Dec2019 (t, t−1 lags, 102 nodes); chi-square-aggregated causal-break detection + Bayesian engine with isotonic calibration → risk probabilities; AUROC 0.971, F1 92.6% vs CNN 0.943 / AE 0.925 (Table 1 p3); root-parent identified "in approximately 92% of cases" (p4). **Mapping:** PC-09 DIRECT/HIGH **as the contrast case** — P19 claims automated root-cause identification, precisely the stronger claim AEGIS-OT's "attribution ≠ root cause" discipline declines to make (R19); PC-10 STRONG CONCEPTUAL (learned DAG = data-driven generalization of declarative invariants); PC-34 COMPLEMENTARY (propagation-ordering reasoning ≈ C5's invariant-direction consistency); PC-06 STRONG CONCEPTUAL (per-sensor normalized residual + validation-tuned threshold). Limitations: dominant-single-parent assumption; labeled-threshold tuning vs nominal-only training tension; 13,201-sample slice of SWaT.

### P20 — Spatio-temporal AE (IJCNN 2023)
Per-element LSTM + encoder attention + GCN over a complete graph, normal-only training; per-sensor dynamic thresholds D_nt = μ+zσ (Eq. 13 p5) with an M-count rule suppressing pump on/off alarms; F 0.851 / R 0.757 / P 0.973 (Table III p7); LIT-301 residual heatmap localization (Fig. 5 p7). **Mapping:** PC-15 DIRECT/HIGH (the named spatio-temporal-AE alternative); PC-06 STRONG CONCEPTUAL (per-sensor thresholds vs AEGIS-OT's global τ); PC-08 PARTIAL (residual heatmap but no contribution normalization/top-k); PC-09 contrast ("can pinpoint the anomaly root cause", p7 — the conflation again). Limitations: z/M unreported; no per-attack results or point-adjustment disclosure; single run.

### P21 — Transparent ICS AE (MIUCC 2024)
Attention-enhanced CNN-AE and LSTM-AE on SWaT (RFE to 17 features, 80/20 normal split, quantile thresholding from *training* errors); post-hoc SHAP + counterfactuals validated by **remove-one-feature-and-retrain probes** (Figs. 2–5): attack detection degrades sharply, normal detection mostly stable; CNN-AE best at F1 0.824 (Table I p4). **Mapping:** PC-18 DIRECT/HIGH (closest published analogue of the planned SHAP cross-check, with a faithfulness probe design AEGIS-OT can adopt for XAI-05); PC-17 PARTIAL/MEDIUM (the probe is a consistency precedent, yet P21 also brands attention as interpretability — the conflation AEGIS-OT prohibits); PC-06 STRONG CONCEPTUAL (quantile threshold family — training-quantile vs AEGIS-OT's validation-quantile); PC-14 COMPLEMENTARY (RFE channel reduction as statistical alternative to fuzzy-rough). Limitations: attention-recall claim contradicts its own Table I; no hyperparameters/quantile value; XAI protocol covers only CNN-AE.

---

## 5. Project Concept Inventory (mapping target)

Full definitions in `analysis/PROJECT_COMPONENTS.md`. Summary of the 50 atomic components:

| ID | Component | ID | Component |
|----|-----------|----|-----------|
| PC-01 | Problem framing: OT decision support, not autonomous control; SWaT-saturation critique | PC-26 | Grounding contract: cite evidence; "insufficient data"; hallucination probe |
| PC-02 | Datasets: SWaT primary / WUSTL secondary / WADI stretch; sha256 registry | PC-27 | Tool surface: query_latest/history, search_kb, check_invariant, propose_action |
| PC-03 | Preprocessing: z-score train-fit, W=60/S=1, causal cleaning | PC-28 | Structured action grammar {action, target, params}; no free text |
| PC-04 | Isolation Forest baseline | PC-29 | Literature agent defenses: instruction hierarchy, tool graphs, verify-before-commit |
| PC-05 | TCN-AE primary detector (dilated causal conv, normal-only) | PC-30 | C1 Provenance (exact-ID binding; hostile-only ⇒ block) |
| PC-06 | Scoring: per-sensor residuals, window mean, τ = p99 validation | PC-31 | C2 Allowlist (strict registry; unknown fields rejected) |
| PC-07 | AE variants/ablations (LSTM-AE, Transformer-AE, XGBoost, ANFIS — stretch) | PC-32 | C3 Injection-pattern filter (NFKC, zero-width, ≤3-layer decode) |
| PC-08 | Attribution: residual share r_i/Σr_j → top-3; not attention | PC-33 | C4 Risk classes read/write/control/forbidden |
| PC-09 | Root-cause discipline: attribution ≠ root cause | PC-34 | C5 Consistency (evidence entailment + invariant-direction; persistent ⇒ escalate) |
| PC-10 | 5 physics invariants (pump⇒flow, level range, …) | PC-35 | Determinism contract: no LLM in C1–C4; pure verdict function |
| PC-11 | Incident grouping (gap ≤ 60 s), severity | PC-36 | Verdicts allow/require_approval/block/escalate; trusted-citation floor |
| PC-12 | Stress protocol: noise/zeroing/drift, test-only | PC-37 | Human approval: all-or-nothing, distinct approver, 24 h expiry → escalate |
| PC-13 | PA%K + point-wise F1 metric discipline | PC-38 | SHA-256 content binding validator↔approval↔execution |
| PC-14 | Fuzzy-rough channel reduction | PC-39 | Naive-agent lockout (INV-010) |
| PC-15 | Alternative detectors (CNN-LSTM, fusion, graph DL, ST-AE, OCSVM…) | PC-40 | Sandbox: 6-stage simulator, only executor, SIMULATED labels |
| PC-16 | Explanation objects (NL hypothesis + evidence + citations) | PC-41 | Append-only audit, same transaction |
| PC-17 | XAI discipline: attention ≠ explanation; consistency scoring | PC-42 | Fail-closed defaults; INV-001..016 |
| PC-18 | Post-hoc XAI methods (SHAP/LIME/ALE/IG/CAM); SHAP cross-check stretch | PC-43 | Attack suite F1–F7 (32 cases) |
| PC-19 | MITRE ATT&CK for ICS mapping (rules + basis) | PC-44 | Safety metrics: ASR, unsafe/block/false-block/refusal rates |
| PC-20 | Team response playbooks (≥10) | PC-45 | Agent ladder naive→grounded→validated (EXP-05/06/07) |
| PC-21 | Tiered RAG (trusted/public/hostile) | PC-46 | EXP-09 gate-bypass battery |
| PC-22 | Retrieval citations {chunk_id, source, section, tier} | PC-47 | Human pilot EVAL-08 (RQ2) |
| PC-23 | Trust firewall: hostile hard-excluded in production | PC-48 | Reproducibility discipline (configs, pins, charter) |
| PC-24 | RAG evaluation (hit-rate/nDCG; citation correctness) | PC-49 | Prior injection benchmarks (InjecAgent/AgentDojo; none OT) |
| PC-25 | Single ReAct agent, analyst-invoked, ≤12 steps | PC-50 | External anchors: Kim et al. 2022; log-injection preprints; CISA 2025 |

---

## 6. Project → Literature Mapping (forward matrix)

Match types: DIRECT / STRONG CONCEPTUAL (SC) / PARTIAL / COMPLEMENTARY (COMP) / EXTENSION / ALTERNATIVE (ALT) / INSPIRATION (INSP) / NONE. "Best" = preferred citation source under §10 criteria. Full per-paper evidence in §4 and the dossiers.

| PC | Papers (match, strength) | Best source | Why best |
|----|--------------------------|-------------|----------|
| PC-01 framing/decision-support | P04 SC-HIGH; P16 SC-MED; P01 SC-MED; P02 SC-MED; P09 COMP; P05/P08 COMP-contrast; P06 ALT-HIGH (contrast) | P04 | Explicit operator-in-the-loop reliability framing ("operator unaware of unreliable outputs", p2) |
| PC-02 datasets | P02 DIRECT-HIGH; P10 DIRECT-HIGH; P15 PARTIAL-HIGH; P16 PARTIAL-HIGH; P20 DIRECT-HIGH; P09 COMP | P16 | Most complete SWaT statistics + preprocessing conventions (21,600 s trim, split counts) |
| PC-03 preprocessing | P16 PARTIAL; P20 PARTIAL; P18 PARTIAL; P01 PARTIAL(temporal-split rationale); P17 PARTIAL | P16 | Train-fit scaling + transient-trim precedent explicitly reasoned |
| PC-04 IF baseline | P15 COMP-HIGH (external IF numbers on SWaT); P16 COMP; P09 COMP | P15 | Only paper reporting Isolation-Forest metrics on SWaT (F1 0.5520) |
| PC-05 TCN-AE | P15 DIRECT-HIGH; P07 SC-HIGH; P20 SC-MED; P21 SC-MED; P18 ALT-MED | P15 | Same architecture family (dilated causal-conv AE, normal-only, SWaT) |
| PC-06 scoring/threshold | P04 SC-MED-HIGH; P16 ALT-MED; P18 PARTIAL; P20 SC-MED; P21 SC-MED; P17 SC-MED; P19 SC-MED | P16 | Detailed percentile+GHOST+persistence thresholding with miss analysis |
| PC-07 AE ablations | P18 DIRECT-HIGH; P21 SC-MED; P09 COMP (XGBoost/LSTM evidence); P08 PARTIAL | P18 | Published LSTM-AE(+OCSVM) specs and numbers on SWaT |
| PC-08 attribution | P15 ALT-HIGH; P16 ALT-HIGH; P02 ALT-MED-HIGH; P19 SC-MED; P01 PARTIAL-MED; P20 PARTIAL-MED; P07 SC-HIGH | P16 | Only corpus source that *measures* attribution faithfulness vs ground truth (IOU/Acc) |
| PC-09 attribution ≠ root cause | P01 SC-HIGH; P16 SC-HIGH; P17 SC-MED; P19 DIRECT-HIGH (contrast); P15 PARTIAL (contrast); P20 COMP (contrast) | P16 | Empirical failure case (SHAP contradicts GT, p11) grounds the humility rule |
| PC-10 physics invariants | P17 DIRECT-HIGH; P02 SC-HIGH; P19 SC-MED; P16 COMP; P20 INSP | P17 | Strongest invariant machinery + live-SWaT validation (100% Dr/0% Fr) |
| PC-11 incident grouping | P15 PARTIAL (attack-window mapping, Fig. 3 p6); P16 COMP (100 s persistence) | P16 | Explicit detection-persistence/grouping logic with documented trade-offs |
| PC-12 stress robustness | P17 SC-MED; P06 INSP-MED; P16 COMP (miss-mode taxonomy) | P17 | Only corpus paper with a genuine drift/mode-shift stress evaluation |
| PC-13 PA%K / metric discipline | P18 SC-MED (96% vs AUC 0.8628); P05 COMP; P10 COMP; P08 COMP-counterexample; P02 COMP (metric-inversion caution); P09 COMP (3-rep avg) | P18 | Sharpest in-corpus demonstration that thresholded metrics mislead |
| PC-14 channel reduction | P21 COMP (RFE 51→17); P20 COMP (KS-test selection); P10 COMP (centrality features) | P21 | Feature-elimination experiment with retraining probes |
| PC-15 alternative detectors | P05 ALT-HIGH; P09 ALT-HIGH; P10 ALT-HIGH; P20 DIRECT-HIGH; P18 DIRECT-HIGH; P15 COMP; P08 ALT | P10 | Broadest baseline+ablation discipline on the same datasets (albeit shuffled splits) |
| PC-16 explanation objects | P16 SC-MED; P15 SC-MED; P01 PARTIAL-MED; P19 SC-MED; P21 SC-MED | P16 | Evidence-style explanation + future "human-interpretable reason" agenda |
| PC-17 XAI discipline | P01 SC-HIGH; P16 SC-HIGH; P07 PARTIAL (counterpoint); P21 PARTIAL | P16 | Shows explanations actively misleading → validates hypothesis-only rule |
| PC-18 post-hoc XAI methods | P15 DIRECT-HIGH; P16 DIRECT-HIGH; P21 DIRECT-HIGH; P01 DIRECT-HIGH; P07 DIRECT-HIGH; P02 SC | P16 | Comparative method study with cost + faithfulness numbers |
| PC-19 MITRE-ICS mapping | P03 SC-HIGH; (others NONE) | P03 | Only corpus paper engaging ATT&CK ICS knowledge organization |
| PC-20 playbooks KB | P03 COMP (curated TTP corpus); P16 COMP (future safety-score agenda) | P03 | Demonstrates curated-knowledge-for-LLM pattern |
| PC-21 tiered RAG | P12 SC-MED (privilege hierarchy); P11 INSP (top-5 regulation retrieval) | P12 | Formal privilege ordering Ls≻Lu≻La≻Lt closest to tiered trust |

| PC-22 citations on retrieval | P12 PARTIAL-MED (source attribution); P11 INSP-LOW | P12 | Tags untrusted instructions with their tool/argument source before checking |
| PC-23 trust firewall | P12 SC-MED (tool-level distrust); P14 ALT-MED (sanitize-and-use doctrine) | P12 | Privilege-graded distrust is the same principle at message level |
| PC-24 RAG evaluation | NONE in corpus (P16's XAI-accuracy protocol is the nearest methodological template) | — | No corpus counterpart exists |
| PC-25 single ReAct agent | P11 INSP-LOW; P13 ALT-MED; P14 ALT-MED | P14 | Uses vanilla ReAct explicitly as the defended substrate |
| PC-26 grounding contract | P14 SC-MED; P12 PARTIAL-LOW; P11 COMP-LOW | P14 | Intent-grounded verification, incl. ablation evidence |
| PC-27 tools / read-only split | P13 SC-HIGH; P06 SC-MED | P13 | "only Query Tool invocations are allowed during execution" (p5) |
| PC-28 structured grammar | P14 SC-HIGH; P13 SC-MED; P06 SC-MED | P14 | Capability enums + per-action metadata are the richest schema |
| PC-29 agent-defense landscape | P14 DIRECT-HIGH; P12 DIRECT-HIGH; P13 DIRECT-HIGH; P11 SC-HIGH | P14 | Latest + broadest taxonomy with 7-baseline comparison |
| PC-30 C1 provenance | P13 SC-MED; P12 PARTIAL-MED | P13 | Structural trusted-input planning phase |
| PC-31 C2 allowlist | P13 SC-HIGH; P14 SC-HIGH | P13 | Plan-level tool allowlist with measured ASR ≤1% |
| PC-32 C3 pattern filter | P12 ALT/COMP-MED; P13 COMP-MED | P12 | Empirically positions the pattern-defense family (incl. failure) |
| PC-33 C4 risk classes | P13 SC-MED; P06 ALT-HIGH; P19 PARTIAL-MED | P13 | Query/Command segregation precedes AEGIS-OT's four-tier classes |
| PC-34 C5 consistency | P14 SC-HIGH; P12 SC-HIGH; P13 SC-MED; P19 COMP-MED | P14 | Two-stage compliance∧entailment is the closest published mechanism |
| PC-35 determinism (no LLM judge) | P13 ALT/PARTIAL-MED; P12 ALT-HIGH; P11 ALT-HIGH | P13 | Explicit published argument that an LLM-judge is compromisable |
| PC-36 verdict tiers | P04 SC-HIGH; P14 PARTIAL-MED; P12 PARTIAL-LOW | P04 | Reject-option theory + honeypot routing ≈ require_approval/escalate |
| PC-37 human approval | NONE operational (P11 PARTIAL-LOW: governance-level oversight only) | — | No corpus paper has a runtime human approval gate |
| PC-38 SHA-256 content binding | NONE (nearest: FATH authentication tags, cited only in P12 related work, p8) | — | Absent from the corpus |
| PC-39 naive lockout | NONE | — | Absent |
| PC-40 sandbox execution | P06 SC-HIGH; P11 COMP-MED; P14 COMP-MED | P06 | Simulation-only execution philosophy, fully embodied |
| PC-41 append-only audit | P15 COMP-LOW; P13 cautionary-LOW | P15 | Only corpus mention of immutable audit logs in an AD pipeline |
| PC-42 fail-closed defaults | P14 INSP-MED; P04 PARTIAL; P12 PARTIAL-LOW; P13 INSP-LOW | P14 | "err on the side of deletion" is explicit fail-closed logic |
| PC-43 attack suite F1–F7 | P14 COMP-HIGH; P12 SC-HIGH; P13 COMP-MED; P11 NONE | P14 | SIREN's 5-vector taxonomy is the structural template; F7 absent corpus-wide |
| PC-44 safety metrics | P13 COMP-MED-HIGH; P14 COMP-MED-HIGH; P12 DIRECT-MED; P11 PARTIAL-MED | P13 | Cleanest BU/UA/ASR operational definitions |
| PC-45 agent ladder | P14 COMP-MED; P12 COMP-MED; P06 INSP-LOW | P14 | Verifier on/off ablation (ASR 8.13→45.05) is the validator-effect template |
| PC-46 gate-bypass battery | NONE | — | Absent |
| PC-47 human pilot | P15 COMP-LOW; P16 COMP-LOW; P01 INSP-LOW; P04 PARTIAL-LOW | P15 | Controlled user studies explicitly deferred = open question |
| PC-48 reproducibility | P16 COMP-MED; P13 PARTIAL-LOW; P10 COMP-LOW; P08 counterexample | P16 | Code release + model-selection transparency |
| PC-49 injection-benchmark gap | P12 DIRECT-HIGH; P13 DIRECT-HIGH; P14 DIRECT-HIGH | P13 | "97 tasks … Workspace, Slack, Travel, and Banking" — explicit domain statement |
| PC-50 external anchors | NOT IN CORPUS (verified: P15's Kim et al. is a 2023 Transformer paper, not the AAAI-2022 critique) | — | Cite externally; never cite the corpus for these |

### 6.1 Where the corpus gives AEGIS-OT nothing

PC-24 (RAG retrieval evaluation), PC-37 (human approval gate), PC-38 (content binding), PC-39 (naive lockout), PC-46 (gate-bypass battery), and F7 (numeric spoofing) have **no material support anywhere in the 21 papers**. These are precisely AEGIS-OT's safety-engineering core — which is good news for the contribution narrative and bad news for literature support: they must be defended on first principles and external literature, not the corpus.

---

## 7. Literature → Project Mapping (reverse matrix)

| Paper | Informs (PCs) | Role for AEGIS-OT | Overlaps with | Preferred for |
|-------|---------------|-------------------|---------------|---------------|
| P01 | 17, 18, 08, 01, 47, 03, 02(HAI) | Conceptual support for attribution discipline; XAI comparison set | P15/P16/P21 (XAI cluster) | "Feature importance ≠ cause" citation |
| P02 | 02, 10, 08, 15, 01, 13, 18 | Data-mined invariant precedent; SWaT/WADI numbers; baseline set | P17 (invariants), P15/P16/P20/P21 (SWaT detectors) | Learned physics-like rules; invariant motivation |
| P03 | 19, 20, 15, 16, 25, 26 | LLM+ATT&CK-ICS alternative to deterministic mapping | — (standalone) | ATT&CK-ICS-as-LLM-knowledge citation |
| P04 | 36, 06, 01, 13, 42, 47, 15, 02 | Reject-option precedent for verdict tiers | — (conceptually P11–P14 verdicts) | Reject/route-to-safety semantics |
| P05 | 15, 13, 01, 17, 03, 02, 05 | CNN-LSTM alternative; evaluation counterexample | P08 (CNN-LSTM family) | Detector-family diversity; anti-pattern citation |
| P06 | 01, 33, 40, 28, 25, 08, 12, 44, 45 | Autonomous-RL contrast case; simulation-only precedent | — (standalone) | "Why not autonomous responders" argument |
| P07 | 18, 05, 08, 16, 17, 15, 13 | Attention-XAI exemplar + counterpoint to attention skepticism | P01/P21 (attention-as-XAI) | Interpretability-by-training nuance |
| P08 | 15, 01, 48, 07, 13, 02 | Rigor counterexample (dataset mismatch, inconsistent numbers) | P05 | Anti-pattern citation |
| P09 | 15, 02, 04, 07, 05, 06, 03, 01, 13, 43, 40 | Decision-fusion alternative; new EDS dataset; runtime numbers | P10 (benchmark family) | Ensemble design + testbed-to-dataset release model |
| P10 | 15, 02, 05, 07, 13, 48, 01, 08, 10, 03 | Graph-DL alternative; SWaT/WADI stats; saturation example | P09, P15/P16 (datasets) | Graph-family baseline; shuffled-split counterexample |
| P11 | 29, 35, 40, 21, 22, 44, 42, 28, 26, 37, 16, 43, 25 | Constitution+inspection defense; LLM-judge contrast | P12/P13/P14 (defense cluster) | Layered agent-safety taxonomy; safety-utility synergy |
| P12 | 49, 29, 43, 34, 35, 32, 30, 31, 44, 45, 21, 23, 42, 36, 26 | Task-alignment defense; benchmark-gap evidence; metric design | P13/P14 (AgentDojo canon); P11 (LLM-check family) | C5-analog tool-arg alignment; CU/U/ASR design |
| P13 | 29, 31, 27, 33, 28, 34, 30, 35, 25, 49, 44, 43, 42, 41, 48 | Structural allowlist defense; anti-LLM-judge argument | P14 (static-vs-dynamic disagreement); P12 (canon) | C2-analog; read-only execution segregation |
| P14 | 29, 34, 31, 28, 35, 36, 25, 26, 43, 49, 44, 45, 23, 42, 10, 41, 22 | Verify-before-commit; SIREN taxonomy; verifier ablation | P13 (critiques its family); P12 (canon) | C5-analog entailment; attack-vector taxonomy template |
| P15 | 05, 18, 16, 08, 04, 15, 02, 03, 06, 01, 09, 41, 47, 13, 48 | Closest detector+XAI prior; IF-on-SWaT reference; SHAP cost model | P16 (mutual-citation pair), P20/P21/P18 (AE family) | TCN-AE + SHAP combined mechanism |
| P16 | 18, 17, 02, 08, 06, 15, 01, 12, 13, 48, 03, 10, 44, 03 | XAI-faithfulness measurement; SWaT conventions; failure case | P15 (mutual), P21 (SHAP studies) | IOU/Acc XAI protocol; explanation-failure citation |
| P17 | 10, 09, 06, 05, 07, 03, 12, 01, 13, 42, 08 | Strongest invariant machinery; drift-stress evidence | P02 (invariants), P19 (physics/causal) | Primary physics-invariant citation |
| P18 | 07, 15, 05, 06, 03, 13, 02 | LSTM-AE+OCSVM variant specs/numbers; metric-gap example | P21/P15 (AE family) | PC-07 ablation reference numbers |
| P19 | 09, 08, 10, 06, 34, 12, 02, 03, 05, 07, 15, 16 | Causal root-cause contrast case; learned-DAG invariants | P17 (physics/causal) | "Why we don't claim root cause" contrast |
| P20 | 15, 02, 05, 06, 08, 09, 03, 14, 13, 12, 17, 10 | ST-AE alternative; per-sensor thresholding; localization heatmap | P15/P18/P21 (AE family) | Per-sensor threshold alternative; localization display |
| P21 | 18, 02, 16, 17, 06, 15, 07, 05, 03, 14, 10, 04 | SHAP+CF with retraining probes; AE variant numbers; RFE reduction | P16/P15 (SHAP studies); P18 (variants) | XAI validation-probe design for XAI-05 |

---

## 8. Paper-to-Paper Overlap Analysis

### 8.1 Relationship graph (textual)

```
CLUSTER A — SWaT/WADI detection & XAI
  P02 (LU-IDS rules) ──invariant-lineage── P17 (PbNN physics) ──physics/causal── P19 (causal DAG)
        │                                       │
        └── SWaT detector family ── P15 (TCAE+SHAP) ⇄ P16 (WaXAI 4-XAI)   [P15 cites P16 as [34]]
                                    │   \____ P21 (SHAP+CF probes)         [P16 ⇒ P15 not cited: P15 is later]
                                    ├────── P18 (LSTM-AE+OCSVM)
                                    └────── P20 (ST-AE)
  P01 (shapelet XAI) ── surveys/relates-to ── P15/P16/P21 (its §II-B cites FedeX, WaXAI, E-SFD)
  P09 (fusion, EDS) ── benchmark family ── P10 (CGAAD, SWaT/WADI)
  P05 (CNN-LSTM, UNSW-NB15) ── architecture family ── P08 (CNN-LSTM, CAN)

CLUSTER B — LLM agent security
  P11 (TrustAgent: constitution + GPT-4 inspector)
     └─ shared premise: action-level (not verbal) safety
  P12 (Task Shield: LLM task-alignment shield)  ── AgentDojo/InjecAgent canon ── P13 (IPIGUARD: structural TDG)
     └─ P12 vs P13: semantic-LLM defense vs structural-plan defense
  P14 (VIGIL: verify-before-commit) ── critiques the static plan-then-execute family that P13 embodies
     └─ P14 introduces SIREN; all four cite/engage AgentDojo (Debenedetti et al. 2024)

CLUSTER C — network/classifier IDS: P03 (LLM+ATT&CK), P04 (reject option), P05, P08
CLUSTER D — autonomous RL defense: P06 (CAGE/CybORG)
```

### 8.2 Key pairwise relationships

- **P15 ⇄ P16 (mutual-citation pair).** P15's Table 1 (p3) lists WaXAI as reference [34], the only surveyed work deriving LIME/ALE/SHAP/IG scores for ICS; P16 (Apr 2024) predates P15 (Dec 2025) and does not cite it. They bracket the same SWaT+XAI niche from detector-heavy (P15) and evaluation-heavy (P16) sides. For AEGIS-OT, P15 is the primary citation for the TCN-AE+SHAP combination; P16 is primary for XAI-faithfulness measurement.
- **P13 ↔ P14 (documented disagreement).** P14 explicitly criticizes static plan-then-execute isolation (the family P13 instantiates): rigid plans "sever the feedback loop required for adaptive recovery" and collapse utility under fabricated errors (P14 pp. 2–3, 7: static defenses' TS UA < 12%, CaMeL ASR 44.83 on Explicit Directive), while P13 reports BU cost of only ~1 point (67.01 vs 68.04) with ASR ≤ 1%. Both are AgentDojo results; the contradiction is resolved by differences in attack vectors (P14's tool-stream fabrication) and the strict UA definition. **AEGIS-OT must not cite either result as a universal claim about structural constraints.**
- **P11 vs P12/P13/P14 (defense-mechanism axis).** P11's post-planning inspector is an LLM (GPT-4); P12's shield is the agent's own model; P14's verifiers are role-specialized LLMs; P13 alone argues structural constraints beat LLM-mediated checking ("remains vulnerable if the LLM-judge itself is compromised", p12). This axis is the literature backing for AEGIS-OT's PC-35.
- **P02 ↔ P17 (invariant lineage).** Both engage Adepu & Mathur's invariant-based detection (P02 pp. 2–3 ref [3]; P17 uses DAD [7] as its ceiling baseline and matches it with learned surrogates). P02's discovered rule "MV101=On ∧ LIT101>H never co-occur normally" (p9) is the empirical shadow of AEGIS-OT's R1/R2 rules.
- **P15/P18/P20/P21 (AE family on SWaT).** Four published variants (TCN/LSTM/spatio-temporal/CNN±attention) with numbers AEGIS-OT can reuse for its detector table; P21 additionally provides the remove-one-feature XAI probe; P20 the per-sensor threshold alternative; P18 the OCSVM hybrid and the metrics-gap caution.
- **P01 ↔ P15/P16/P21 (XAI survey hub).** P01's §II-B catalogues SHAP/LIME/counterfactual deployments on SWaT/HAI (FedeX, WaXAI, E-SFD) and supplies the "three values" framework (global explanation, feature importance, anomaly cause, p5).
- **P09 ↔ P10 (benchmark-family neighbors).** Both evaluate on SWaT/WADI-class data with SOTA tables; P09 adds a new open dataset (EDS) and runtime numbers; P10 adds graph features — both useful for AEGIS-OT's related-work breadth.
- **P05 ↔ P08 (architecture family, shared weakness).** Both are CNN-LSTM classifiers on non-OT data with evaluation weaknesses (random splits; contradictory numbers) — citable as the pattern AEGIS-OT's protocol corrects.
- **P12/P13/P14 (shared canon).** All three use AgentDojo, Important Instructions/InjecAgent attack strings, Spotlighting, and Tool-Filter baselines; P14 adds CaMeL, MELON, DRIFT. This common substrate makes their numbers roughly comparable to each other — and makes the absence of any OT/ICS setting unambiguous.
- **Standalone papers.** P03 (no experiments), P04 (network domain), P06 (RL domain) connect to AEGIS-OT conceptually (ATT&CK knowledge, reject semantics, simulation-only autonomy) but not to other corpus papers.

---

## 9. Research Lineage

```
SWaT dataset (Goh et al. 2016/2017 — cited by P02, P15, P16, P17, P18, P20, P21, P10)
   └→ Kravchik & Shabtai CNN/AE line (cited by P02, P17)
        └→ AE variants: P02 baselines (UAE) · P18 LSTM-AE+OCSVM · P20 ST-AE · P21 CNN/LSTM-AE
             └→ P15 TCAE (dilated causal conv) ──→ AEGIS-OT TCN-AE (family continuation; different window/scoring/attribution)

Invariants: Adepu & Mathur DAD (via P02 ref[3], P17 baseline)
   ├→ P02: data-mined invariant-style rules (CAM distillation)
   ├→ P17: P&ID invariants + learned DCNN surrogates + CUSUM (live-SWaT validated)
   └→ P19: learned causal DAG as generalized invariants
        └→ AEGIS-OT: 5 declarative rules + direction rules wired into C5 + agent tool (simpler, integrated)

XAI-for-AD: SHAP/LIME (Lundberg/Ribeiro) → FedeX, WaXAI(P16), E-SFD (surveyed in P01 §II-B and P15 Table 1)
   ├→ P15: per-attack Kernel SHAP on AE detections (cost: ~40 s/window)
   ├→ P16: 4-method comparison with IOU/Accuracy faithfulness (and a failure case)
   ├→ P21: SHAP+counterfactual with remove-one-feature probes
   └→ AEGIS-OT: residual-share attribution (primary) + SHAP cross-check (stretch, precedented by P15/P16/P21)

Agent safety: Constitutional AI → P11 TrustAgent (constitution + inspector; ToolEmu evaluation)
   → P12 Task Shield (semantic task alignment, LLM shield)   \
   → P13 IPIGUARD (structural tool-dependency graph)          | all evaluate on AgentDojo (2024)
   → P14 VIGIL (verify-before-commit + SIREN)                /
   → AEGIS-OT: deterministic C1–C5 + hash-bound human approval + sandbox (LLM-free gate; OT domain)

Point-adjustment critique: Kim et al. AAAI-2022 (external, NOT in corpus) → AEGIS-OT PA%K charter
   (no corpus paper engages PA; P15/P16/P18/P20/P21 report plain or percentile-thresholded metrics)
```

Lineage note (accuracy): P15's reference "Kim et al." is a 2023 stacked-Transformer paper, **not** the AAAI-2022 point-adjustment critique — verified in P15's reference list (dossier §Overlap Notes). Do not cite P15 as evidence for the PA critique.

---

## 10. Strongest-Source Selection

For each important AEGIS-OT claim/component, ranked sources:

| Claim / component | PRIMARY | SECONDARY | COMPLEMENTARY | Reason primary wins |
|---|---|---|---|---|
| TCN-AE detector design | P15 (§3.2.2 p4, Table 2 p5) | P20, P18 | P07 | Same family, same dataset, full hyperparameters |
| Isolation-Forest baseline viability | P15 (Table 3 p5: F1 0.5520) | P16 | P09 | Only in-corpus IF-on-SWaT numbers |
| Residual-share attribution | P15's DAEMON description ([30], Table 1 p3: "top-k dimensions exhibiting the highest reconstruction error") | P20 (residual heatmap) | P19 | Establishes reconstruction-error top-k as a recognized mechanism; AEGIS-OT normalizes it |
| XAI method choice / faithfulness | P16 (Table 6 p10; §6.4 p11) | P21, P01 | P15 | Only measured comparison incl. failure case |
| Attribution ≠ root cause | P16 (p11 contradiction) | P01 (p2/p15 thesis) | P15/P20/P19 as contrast | Empirical, not merely rhetorical |
| Physics invariants | P17 (Eqs. 1–3, Table III, live eval) | P02 (Rule-ID 1) | P19 | Strongest machinery + live validation |
| Stress/drift robustness motivation | P17 (manual-mode experiment, Table V/Fig. 5) | P16 (miss taxonomy) | P06 | Real-plant drift evidence |
| Metric discipline (thresholded metrics mislead) | P18 (96% vs AUC 0.8628) | P08 (contradictions), P10 (shuffled 99.9%) | P02 (metric inversion) | Sharpest single demonstration |
| Verdict tiers incl. reject/escalate | P04 (Eqs. 1–3, honeypot) | P14 (forbid/approve) | P12 | Only corpus source with explicit reject-to-safer-path semantics |
| Agent safety architecture landscape | P14 (taxonomy + 7 baselines) | P13, P12 | P11 | Most recent, broadest, ablation-complete |
| C2 allowlist precedent | P13 (pp. 2, 4–5) | P14 (§4.2) | P06 | Direct structural equivalence + measured ASR |
| C5 consistency precedent | P14 (V = compliance ∧ entailment, p5–6) | P12 (Fig. 6 p16) | P13 | Closest mechanism + ablation (ASR 45.05 without verifier) |
| Determinism vs LLM-judge | P13 (p2, p12) | P12 (p8 limitations) | P11 (as contrast) | Explicit argument, not inference |
| Injection benchmark gap (no OT) | P13 (§4.1 p6 domain statement) + P12 (§5.1 p5) + P14 (§3 pp. 3–4) | — | — | Triangulated across three papers |
| SIREN-style attack taxonomy | P14 (Table 1 p4; Tables 4–5 p14) | P12 (attack suite) | P13 | Largest structured corpus of injection vectors |
| MITRE-ICS as knowledge source | P03 (§III-A/B, Table II p2) | — | — | Only corpus engagement with ATT&CK ICS |
| Simulation-only execution | P06 (CAGE, p1/p5) | P11 (ToolEmu emulation) | P14 | Fully embodied philosophy |
| Explainability for operator trust | P16 (pp. 1–2) | P01 | P15 | Explicit decision-support framing |
| Human-in-the-loop as open gap | P15 (user studies deferred, p11) + P16 (future work) + P01 (comprehensibility unmeasured) | — | P04 | Triangulated deferral of user evaluation |

---

## 11. Overlap Resolution (X vs. X+Y cases)

The master-prompt case: Paper A has X; Paper B has X+Y; the project has X+Y. Resolved instances:

1. **TCN-AE detection (X) vs TCN-AE + SHAP (X+Y).** P15 contains both the dilated causal-conv AE *and* per-attack SHAP. Because AEGIS-OT's detection layer is TCN-AE and its XAI cross-check is SHAP-shaped, **P15 is the stronger direct source for the detection+explanation pairing** than any paper holding only one half (P20/P18 for AE alone; P16/P21 for XAI alone). P15 remains an earlier-independent source for neither — it is the single combined source. AEGIS-OT's actual attribution (residual share) is NOT in P15 (P15 uses SHAP), so the attribution mechanism itself is sourced to the reconstruction-error top-k idea P15 attributes to DAEMON [30] — meaning even here the corpus contains the concept, just via a secondhand mention.
2. **Invariants (X) vs invariants + learned models + live validation (X+Y+Z).** P17 subsumes what AEGIS-OT's invariant layer does (declarative relations) *plus* learning the relations and validating live. **P17 is the primary invariant citation; AEGIS-OT's 5 rules must be presented as a lightweight declarative subset wired into the agent/validator loop — an integration choice, not a physics contribution.** P02's mined rules (X′) are the data-driven alternative and secondary citation.
3. **Injection defense (X) vs defense + benchmark (X+Y).** P14 contains both a defense (verify-before-commit) and a benchmark (SIREN, 959 cases); P12 contains defense + AgentDojo evaluation. For any AEGIS-OT sentence of the form "agent defenses are evaluated on injection benchmarks," P14/P12 are the complete sources; P13 is defense-only (AgentDojo reused).
4. **Allowlist (X) vs allowlist + risk classes + measured ASR (X+Y+Z).** P13's structural constraint ("no tools not pre-approved in the plan", p2) plus its Query/Command split plus BU/ASR measurement makes it the strongest single source for C2-analog claims; P14's compliance stage is the second complete instantiation.
5. **Reject semantics (X) vs reject + threshold objective + deployment (X+Y+Z).** P04 is the only corpus paper with a full reject-option mechanism; AEGIS-OT's require_approval/escalate verdicts cite P04 as the conceptual precedent, then differentiate (reject-to-human vs reject-to-honeypot; content-bound approval).
6. **MITRE-ICS knowledge (X) vs MITRE-ICS + LLM interface (X+Y).** P03 holds the pairing. AEGIS-OT's deterministic rule table is an alternative interface to the same knowledge source — cite P03 for the knowledge-organization precedent, not for any validation result (it has none).

---

## 12. Combination Opportunities

Corpus-documented components that combine into AEGIS-OT's pipeline — none of the 21 papers performs the integration:

- **P15 contributes** the detector mechanism (TCN-AE, normal-only) and the SHAP-explanation cost model.
- **P16 contributes** the attribution-faithfulness measurement protocol and the decision-support framing.
- **P17 contributes** the physics-invariant layer and drift-stress motivation.
- **P04 contributes** the reject/escalate verdict semantics.
- **P03 contributes** the ATT&CK-ICS knowledge-organization pattern.
- **P13+P14 contribute** the allowlist + verify-before-commit defense mechanisms (as LLM-mediated versions).
- **P12 contributes** the attack-metric design (CU/U/ASR) and the benchmark-gap statement.
- **P06 contributes** the simulation-only execution doctrine (as the philosophy AEGIS-OT shares while rejecting its autonomy).
- **AEGIS-OT integrates all of the above** into one pipeline where the detector feeds attribution feeds an agent whose drafts pass a deterministic validator, a hash-bound human gate, and a sandbox. **No corpus paper connects detection to any agent/validator/approval machinery** — the corpus's two halves (Clusters A and B) never touch. This is the system-level integration contribution; it is *potential*, not proven, novelty (§25, §26).

---

## 13. Code-to-Literature Mapping

Implementation facts from `analysis/CODE_INVENTORY.md` (all paths relative to `aegis-ot/`). Where code and claims diverge, the divergence is stated — these matter for the final paper's honesty.

| Code artifact (file · function/class) | Behavior as coded | Closest literature | Location | Similarity | Difference | Confidence |
|---|---|---|---|---|---|---|
| `pipeline/detect/tcn_ae.py` `_build()` | Causal Conv1d, k=3, dilations [1,2,4] enc / [4,2,1] dec, channels →32→32→latent 8, MSE, Adam 1e-3, 30 epochs | P15 TCAE | P15 §3.2.2 p4, Table 2 p5 | Same family: dilated causal-conv AE, normal-only, reconstruction | Window 60 vs 12; z-score vs min-max; latent 8 vs 40 filters/1×1 compression; τ=p99 vs KDE+DBSCAN; P15 uses kernel 40, dilations to 16 | HIGH |
| `pipeline/detect/scoring.py` `threshold_from_validation()` | τ = p99 of validation GT-normal residuals | P16 95th-percentile + GHOST; P21 quantile thresholding; P18 95th-pct RMSE | P16 §5.2.2 p7; P21 §III-B p3 | Percentile-of-normal-errors family | AEGIS-OT: validation-only fit, no GHOST/persistence layer | HIGH |
| `pipeline/detect/scoring.py` `contributions()` | share_i = r_i/(Σr+1e-12); Σ<1e-9 ⇒ uniform + low_confidence; top-3 | P15's DAEMON description ("top-k dimensions exhibiting the highest reconstruction error", Table 1 p3); P20 residual heatmap | P15 Table 1 p3; P20 §IV-E p7 | Reconstruction-error decomposition → ranked sensors | AEGIS-OT normalizes shares and floors low-confidence; not SHAP/attention | HIGH (concept), MEDIUM (novelty of normalization) |
| `pipeline/detect/invariances.py` + `configs/invariants.yaml` | 5 rules: R1 tank level ∈ [0,100]; R2 pump⇒flow>0.5; R3 valve-closed⇒flow<0.1; R4 \|Δlevel\|≤2.0; R5 flow ∈ [0,15]; + R0 score-finite | P17 Eqs. 1–3 + Table III; P02 Rule-ID 1 | P17 p4, Table III p7; P02 p9 | Same declarative-physics concept (pump/valve/level/flow) | AEGIS-OT rules are fixed simple thresholds; P17 learns nonlinear forms + CUSUM; P02 mines rules from attacks | HIGH |
| `configs/invariants.yaml` `direction_rules` | Failed R2 forbids set_pump_speed; failed R3 forbids valve actions (C5 input) | P19 propagation ordering; P14 invariant compliance | P19 p4; P14 §4.5 p5–6 | Direction-consistency reasoning | AEGIS-OT encodes it declaratively for action vetting | MEDIUM |
| `pipeline/tintel/mitre_ics.py` + `configs/tintel_rules.yaml` | 4 rules (YAML) → T0862/T0846/T0875/T0838 with confidence + basis{matched_rule, top_sensors, failed_invariants} | P03 ATT&CK-ICS organization | P03 §III-A/B p2, Table II p2 | Same knowledge source | P03 trains an LLM on the matrix; AEGIS-OT uses deterministic rules with recorded basis | HIGH |
| `pipeline/rag/retriever.py` `retrieve()` | Mode allowlist: production=(trusted,public); hostile hard-excluded even if requested; TIER_DENIED flagged even on failure; citations carry {evidence_id, chunk_id, doc_id, source, section, tier, score} | P12 privilege hierarchy; P11 top-5 regulation retrieval | P12 §2 p2, Fig. 5 p15; P11 §3.3 p4 | Graded-trust retrieval | P11/P12 inject retrieved rules into prompts; AEGIS-OT excludes hostile at the retriever and returns typed citations | HIGH |
| `pipeline/rag/chunking.py` `chunk_document()` | heading-aware, 300-word target, 32-word overlap (**words, not tokens** — docs claim tokens) | (no corpus counterpart) | — | — | — | — |
| `pipeline/agent/runner.py` `run_agent()` | ReAct loop, max 12 steps, lease 300 s / heartbeat 100 s, forced finalize + STEP_LIMIT_REACHED; naive ⇒ draft_only | P14 (ReAct as substrate); P11 (planning loop) | P14 §5.1 p6; P11 §3.1 p3 | Single planner + tool loop | AEGIS-OT adds lease/reaper, step cap, forced finalize, analyst invocation | HIGH |
| `pipeline/agent/llm.py` | OllamaClient qwen2.5:7b-instruct, temperature 0/top_p 1/seed 0; ScriptedClient "scripted-offline" labeled | P13 (temperature pinned 0, models pinned); P12 (temp 0.0 shield) | P13 App. C p12; P12 App. C p13 | Reproducibility discipline | AEGIS-OT's deterministic scripted backend is a measurement-honesty device absent in corpus | HIGH |
| `pipeline/validator/provenance.py` `check_provenance()` | Exact-ID binding vs EvidenceIndex; hostile-only ⇒ block; no-citations ⇒ flag; public-only ⇒ flag | P13 trusted planning inputs; P12 source attribution | P13 §3.1 p4; P12 §4.2 p5 | Provenance separation | AEGIS-OT binds per-claim by exact ID and records tier; corpus uses structural or string-level separation | HIGH |
| `pipeline/validator/policy.py` `check_allowlist()` | Strict registry lookup; unknown fields/keys rejected; types strict; ranges enforced; 8 actions in `configs/policy/actions.yaml` | P13 plan allowlist; P14 invariants/capability enums | P13 pp. 2, 4; P14 §4.2 p4, Fig. 5 p16 | Allowlist semantics | AEGIS-OT validates at plan-revision time against a versioned YAML registry, not a planned graph | HIGH |
| `pipeline/validator/pattern.py` `normalize()/_decode_layer()` | NFKC → casefold → zero-width strip; base64/% iterative decode ≤3 layers; 17 markers | P12's baseline family (Delimiting/PI Detector) | P12 §5.1 p6 | Pattern-defense family | AEGIS-OT demotes patterns to one of five checks (corpus shows pattern-only defenses fail) | HIGH |
| `pipeline/validator/consistency.py` `check_consistency()` | Field entailment tol 1e-6 vs trusted evidence; invariant-direction conflict; persistent category ⇒ escalate | P14 V_entailment; P12 arg-consistency | P14 §4.5 pp. 5–6; P12 Fig. 6 p16 | Params-vs-evidence consistency | AEGIS-OT is rule-based/deterministic; P14/P12 use LLM scoring | HIGH |
| `pipeline/validator/verdict.py` `step_verdict()/plan_verdict()` | Single pure lattice allow(0) < require_approval(1) < escalate(2) < block(3); no-trusted-citation floor (R9) except `citation_free_read` whitelist (snapshot_plant_state); empty plan ⇒ escalate | P04 reject-option (reject ≈ withhold + route); P14 forbid/approve | P04 §IV-B p4, Eqs. 1–2 p5; P14 Fig. 2 p5 | Tiered verdicts | AEGIS-OT has 4 tiers incl. escalate + human gate; corpus max is reject/forbid/approve | HIGH |
| `app/core/canonical.py` `steps_hash()` + `app/db/immutability.py` + migrations 0002/0003 | JCS-canonical SHA-256; ORM listener + PG trigger immutability; validator/approval/execution triple binding; EXEC_HASH_MISMATCH; amendment ⇒ new revision + fresh validation | **NONE in corpus** (nearest: FATH hash tags, cited only in P12 related work p8) | P12 p8 | — | AEGIS-OT's content binding has no corpus precedent | HIGH (absence verified by dossier greps) |
| `app/services/approval_service.py` | Conditional-update state machine; 24 h expiry ⇒ escalated (worker sweep + API guards); distinct-approver for control; atomic pending→approved replay guard | **NONE** (P11: governance-level oversight only, p3) | P11 p3 | — | No corpus paper has a runtime human approval gate | HIGH |
| `pipeline/sandbox/simulator.py` + `plant_model.py` | 6-stage surrogate; 7 applicable actions; SIMULATED labels; 600 s execution lease; idempotent per-(plan,step) resume; hash re-verification before applying | P06 CAGE; P11 ToolEmu emulation; P14 hypothetical sandbox | P06 p1/p5; P11 §3.1 p3; P14 §4.4 p5 | Simulation as execution substrate | AEGIS-OT's sandbox is deterministic physics-lite, the only executor, hash-gated | HIGH |
| `app/services/audit.py` + migration 0002 | Same-transaction append; PG `REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC` (no-op on SQLite) | P15 "immutable audit logs" (p6) | P15 §3.5 p6 | Immutable-audit aspiration | P15 states it as deployment context; AEGIS-OT enforces it (PG-scoped) | HIGH |
| `eval/attack_suite/fixtures.py` | 32 fixtures: F1×6, F2×6, F3×5, F4×5, F5×5, F6×3, F7×2 with GT-unsafe predicates | P14 SIREN (5 vectors, 959 cases); P12 attack suite | P14 Table 1 p4; P12 §5.2 p7 | Injection taxonomy | AEGIS-OT adds F6 hallucination probes and F7 numeric spoofing (no corpus analogue); corpus corpora are 8–30× larger | HIGH |
| `eval/metrics/charter.py` | 17 pure metric functions incl. PA%K (event credited iff coverage ≥K%), ASR, block/false-block/refusal, hallucination, F7 MRR@3 | P13 BU/UA/ASR; P12 CU/U/ASR; P14 strict UA | P13 §4.1 p6; P12 §5.1 p6; P14 §5.1 p6 | Same safety-metric family | AEGIS-OT adds block/false-block/refusal decomposition + charter discipline; PA%K sourced externally (Kim et al., not in corpus) | HIGH |
| `eval/bypass_battery.py` | 6 bypass attempts, all must be rejected | **NONE** | — | — | Absent from corpus | HIGH |
| `eval/stress.py` + `configs/stress.yaml` | Test-only noise/zeroing/drift grid, seeds 1–3, median | P17 manual-mode drift; P16 miss taxonomy | P17 pp. 8–9; P16 pp. 9–10 | Stress motivation | Corpus has no augmentation protocol; AEGIS-OT's is systematic | HIGH |
| `eval/channel_reduction.py` | Triangular fuzzy membership + lower approximation + dependency degree γ; mask fit on train only | P21 RFE; P20 KS-test; P10 centrality features | P21 §III-D p4; P20 §IV-B p6 | Channel-reduction family | AEGIS-OT's fuzzy-rough method is a distinct (soft-computing) variant; corpus alternatives are statistical/wrapper | MEDIUM |

### 13.1 Code-vs-claims deviations (provenance-relevant)

1. **Production attribution is degenerate for IF anomalies:** `app/services/pipeline_service.py::run_detection` computes contributions from `np.abs(np.tile(scores[i], n_sensors))` — equal shares, alphabetical top-3. The real `contributions()` exists but is not consumed by the wired pipeline. **Do not publish attribution results from the IF path.**
2. **EXP-01/02 fit and threshold on the same validation windows** — the committed offline experiments do not exercise the train→validation separation the specs claim.
3. **`check_invariant` agent tool passes empty sensor scopes** ⇒ physics rules trivially pass; invariant corroboration inside agent runs is structural, not physical, until fixed.
4. **EXP-09 unreachable from CLI/API** (tests only); `/eval/run` accepts only EXP-08; `f7_mrr3`, `false_block_rate`, `approval_rate`, `execution_unsafe_rate` not wired into runners.
5. **F7 has 2 text fixtures + the synthetic zeroing segment + stress zeroing** — thinner than "numeric spoofing suite" implies; no dedicated attribution-spoofing harness with GT sensors.
6. **EXP-04 "no explanation" ablation is mislabeled** — both EXP-03/04 arms strip trusted KB context; nothing detaches the explanation object specifically.
7. Chunker counts words; default embedder is the pinned char-3-gram hashing backend (MiniLM optional); `citation_free_read` whitelist softens the zero-citation floor; verdict R1 exception path has no producer; MITRE YAML (4 rules) ≠ in-code fallback (3 rules); PC-07 ablation detectors not in code.

---

## 14. Claim-Level Verification

| # | Project claim | Verdict | Evidence |
|---|---|---|---|
| C-1 | "SWaT benchmark F1 ~0.98 is point-adjusted and overstates performance" | **PARTIALLY SUPPORTED by corpus behavior; the critique itself is NOT in the corpus** | Corpus papers report plain/percentile metrics (P15 Table 3 p5; P16 Eqs. 8–11 p7; P18 96% vs AUC 0.8628 p4) and high headline numbers under weak protocols (P10 99.91% under shuffled splits p11/p19) — consistent with the critique's motivation. But Kim et al. AAAI-2022 must be cited externally; P15's "Kim et al." is a different 2023 paper (dossier-verified) |
| C-2 | "Detection quality is not the bottleneck; robustness/attribution is" | **SUPPORTED** | Corpus detectors span F1 0.55–0.99 with wildly varying protocols (P15 0.7436; P10 99.91% shuffled; P02 35/35) — protocol, not architecture, drives rankings; P16 shows thresholding causes misses (pp. 9–10); P17 shows drift breaks data-centric detectors (p9) |
| C-3 | "Sensor attribution helps analysts" | **INDIRECTLY SUPPORTED / UNSUPPORTED as a measured claim** | P16 measures attribution faithfulness (Table 6 p10) and P01 argues cause-vs-likelihood (p2/p15), but **no corpus paper measures analyst decision improvement**; P15/P16 explicitly defer user studies (P15 p11; P16 p11). AEGIS-OT's EVAL-08 pilot addresses a corpus-acknowledged gap — keep it exploratory |
| C-4 | "XAI explanations can mislead" | **SUPPORTED** | P16 attack-24 failure: SHAP top feature MV-201 "contradicts the actual attack point" (p11); P01: feature importance "not the cause" (p2, p15) |
| C-5 | "LLM agents can be manipulated via content they read" | **SUPPORTED** | P12 (ASR 47.69% no-defense on AgentDojo, Table 1 p6); P13 (no-defense ASR 13.16%, Table 1 p8); P14 (SIREN: vanilla ReAct TS ASR 73.83, Table 2 p7). All IT-domain — cite as analogy for OT, per R8 |
| C-6 | "Deterministic checks beat LLM-judged checks" | **PARTIALLY SUPPORTED (argument, not measurement)** | P13: LLM-judge "remains vulnerable if the LLM-judge itself is compromised" (p12); P12: same-model shield has "susceptibility to adaptive attacks" (p8). No corpus paper runs the deterministic-vs-LLM-judge experiment — AEGIS-OT's EXP-05→07 ladder is positioned to contribute here |
| C-7 | "No OT/ICS agent-safety benchmark exists" | **SUPPORTED (within corpus)** | P12 §5.1 p5 + P13 §4.1 p6 + P14 §3 pp. 3–4: AgentDojo = Workspace/Slack/Travel/Banking; SIREN = AgentDojo reconstruction; InjecAgent = email/finance. No ICS content anywhere in P11–P14 (dossier greps) |
| C-8 | "Human approval + content binding is required for control-class actions" | **UNSUPPORTED BY PROVIDED PAPERS (gap, not contradiction)** | No corpus paper implements approval gates or hashing (P11–P14 verified; P04's reject routes to honeypot, not humans). This is AEGIS-OT's strongest differentiator and must be argued from safety principles + NIST SP 800-82/CISA guidance (external) |
| C-9 | "Physics invariants catch impossible readings" | **SUPPORTED** | P17: 100% Dr / 0% Fr with invariant+learned models on live SWaT (p11); P02's mined rule encodes the same physics (p9); P19 learns causal analogs (p3–4) |
| C-10 | "TCN-AE is a competitive ICS detector" | **SUPPORTED (moderate numbers)** | P15 TCAE F1 0.7436 with P 0.9435 but R 0.6136 (Table 3 p5) — best in its comparison yet modest recall; AEGIS-OT must not promise P15-level precision without its own runs |
| C-11 | "Fuzzy-rough channel reduction preserves robustness" | **UNSUPPORTED (hypothesis)** | No corpus paper uses fuzzy-rough sets; nearest are P21's RFE (51→17) and P20's KS-test. Keep ROB-01/02 framed as hypothesis with measured reduction % (matches R30) |
| C-12 | "Naive agents comply with injections; hardening fixes it" | **SUPPORTED directionally** | P12/P13/P14 all report large no-defense vs defended ASR gaps (47.69→2.07; 13.16→0.69; 73.83→8.13). AEGIS-OT's naive-vs-hardened ladder mirrors this design |
| C-13 | "Log/telemetry content is attacker-controlled (0–86% ASR)" | **NOT IN CORPUS** | The LogJack/LogInject/Poisoning-the-Watchtower/NetInjectBench preprints cited in the specs are not among the 21 papers. Cite externally; do not attribute to corpus |
| C-14 | "Mitigations must be structured actions, not free text" | **SUPPORTED conceptually** | P13's typed JSON DAG (App. A p10); P14's capability enums + metadata (Figs. 5/7 pp. 16/18); P06's closed action set (p5) |

---

## 15. Contradictory Evidence (corpus-internal tensions AEGIS-OT must navigate)

1. **Structural constraints: cheap or costly?** P13 reports benign-utility cost ~1 point (BU 67.01 vs 68.04, p7); P14 reports static-isolation UA collapse (<12%) and its own Gemini BU drop 40.82 vs vanilla 65.31 (Table 2 p7). Resolution: attack vectors and strictness differ; AEGIS-OT should report its own false-block rate rather than inherit either number.
2. **Do strong models help or hurt security?** P12 documents the Inverse Scaling Law (GPT-4o no-defense ASR 47.69 vs GPT-4o-mini 27.19, p8); P14 names it "Alignment-Driven Vulnerability" (strong models obey injected tool rules, pp. 1–2); P13 finds Qwen2.5-7B usable as executor with a strong planner (Table 5 p13). For AEGIS-OT: model choice is a safety variable — report per-backbone results (Qwen2.5-7B + cross-model stretch).
3. **Labeled vs normal-only training.** P02/P09/P10 use supervised/labeled attack data; P15/P16/P17/P18/P20/P21 train normal-only. AEGIS-OT's normal-only choice aligns with the larger cluster; P02's supervised rules must be cited as a different setting, not a competing number.
4. **Attribution semantics.** P15 ("SHAP … pinpoint[s] root causes", p2), P20 ("pinpoint the anomaly root cause", p7), and P19 (~92% root-cause identification, p4) all equate attribution with root cause; P16's failure case (p11) and P01's thesis (p2/p15) refute the equivalence. AEGIS-OT sides with the refuters — and should say so explicitly, citing both sides.
5. **Do safety measures cost utility?** P11: no ("synergistic", p6); P12: utility under attack rises (50.08→69.79); P14: costs 24 points of BU on one backbone; P12's PI Detector collapses utility (21.14). AEGIS-OT's false-block-rate metric is the correct instrument for this tension — report it as core, not incidental.
6. **Headline numbers vs protocol quality** (P08: 100%/97.30%/95.55% inconsistent claims; P10: 99.91% under shuffle; P05: 98.66% random split) vs careful mid-range numbers (P15: 0.7436 disclosed; P16: 0.74 with misses analyzed). The corpus itself demonstrates that saturation claims track protocol laxity — usable as in-corpus support for AEGIS-OT's PC-01/PC-13.

---

## 16. Experimental Methodology Comparison

| Methodological element | Corpus practice | AEGIS-OT practice | Assessment |
|---|---|---|---|
| Split discipline | Random/shuffled common (P05 8:1:1 random p2; P10 shuffle+80/10/10 p11; P18 unclear; P08 70/30 random) vs temporal (P02 time-ordered 9:1 pp. 9–10; P01 temporal-continuity 2.3:7.2 p14; P04 attack-ordered chronological p6) | Contiguous 60/20/20, no shuffle, windows never straddle | AEGIS-OT matches the careful minority; cite P01/P04 as precedent |
| Point adjustment / PA%K | Absent from all 21 papers (verified per-dossier) | Point-wise F1 + PA%K charter (external: Kim et al.) | AEGIS-OT exceeds corpus practice; must cite externally |
| Threshold selection | p95+GHOST+persistence (P16 p7); quantile on training errors (P21 p3); KDE+DBSCAN undisclosed (P15 p5); dynamic μ+zσ (P20 p5); argmin error+rejection (P04 p5) | τ = p99 of **validation** GT-normal residuals, frozen before test | Comparable family; AEGIS-OT's validation-only fit is the distinctive discipline |
| Variance reporting | Rare: P09 averages 3 repetitions (p9); P06 max-of-5-runs without variance; single runs elsewhere | Median over 3 seeds for stress; per-seed values + std required | AEGIS-OT stricter than whole corpus |
| Attribution evaluation | P16 IOU/Accuracy vs GT attacked devices (Eqs. 12–13 p8) — unique; P21 remove-one-feature probes; P15 visual agreement only | Charter `attribution_consistency` + F7 MRR@3; XAI-05 SHAP cross-check stretch | Adopt P16's IOU/Accuracy protocol for the SHAP cross-check; it is the corpus's only GT-based method |
| Defense evaluation | AgentDojo with BU/UA/ASR (P13 §4.1; P12 §5.1; P14 §5.1 strict-UA) | EXP-05→07 ladder + EXP-08 with ASR/unsafe/block/false-block/refusal | AEGIS-OT adds the false-block decomposition corpus metrics lack |
| Ablation isolation | P14's module ablations (Table 3 p8); P13's FTI/NE ablation (Table 3 p8); P15 none | One capability varied per rung (grounding vs validator) | Corpus-consistent design |
| Baseline reproduction | P02 reproduces 5 baselines with full settings (p7); P10 6 baselines + 16 SOTA (mostly imported numbers); P15 provenance of baseline numbers unstated | IF baseline + detector family from corpus numbers | Reuse P02's reproduction discipline |
| Overhead accounting | P13 token/time table (Table 2 p8); P14 scalability analysis (Fig. 4 p8); P15 SHAP ~40 s/window (p6); P16 XAI runtimes (Table 6 p10) | Validator is deterministic/cheap; latency stats in charter | Report validator overhead like P13's Table 2 for comparability |

**Evidence-based experimental design recommendations (grounded):**
1. Report BU/UA/ASR with P13's operational definitions and add AEGIS-OT's block/false-block/refusal rates (P12's PI-detector utility collapse shows why false-block must be core).
2. For the SHAP cross-check, adopt P16's IOU-top-5/top-10 + accuracy protocol verbatim (with per-stage scope as P16 recommends, p11).
3. For detector comparisons, reuse P15 Table 3 / P21 Table I / P18 Tables II–III as published reference rows rather than re-running their models.
4. Follow P02's practice of reproducing baselines with disclosed settings (p7) — the corpus's best reproducibility pattern.
5. Treat P14's verifier ablation (ASR 8.13→45.05 without verifier, Table 3 p8) as the design template for EXP-06 vs EXP-07's validator effect.
6. Report validator overhead (tokens/time) as P13 does (Table 2 p8) to preempt cost objections.

---

## 17. Dataset / Benchmark Comparison

| Dataset | Corpus usage | AEGIS-OT usage | Notes |
|---|---|---|---|
| **SWaT** | P02 (35 attacks), P15 (51 vars, 1 Hz, 41 attacks, 496,800/449,919 windows p4/p7), P16 (946,722 records, 5.77% attack, 41/36 attacks, first 21,600 s removed p5), P17 (historical + live), P18 (496,800 normal + 449,919 attack, 80/20), P20 (27 actuators/24 sensors), P21 (51 features, RFE→17), P10 (946,719 samples, FDI 5.8%) | Primary; sha256-pinned registry; temporal splits | Corpus conventions worth adopting: P16's 21,600 s transient trim; P15's window counts as sanity anchors; P16 Table 5 as per-attack ground-truth inventory for evaluation fixtures |
| **WADI** | P02 (15 attacks), P10 (314,404 samples, FDI 25.4%) | Stretch (DATA-03) | Corpus confirms WADI is harder (P10 notes degradation p19; P02 15/15 but different protocol) |
| **WUSTL-IIoT-2021** | Not used by any corpus paper | Secondary domain validation | No corpus comparability — AEGIS-OT results there will be novel territory |
| HAI 23.05 | P01 (boiler process, 48 attacks, window 20) | Not used | Candidate third dataset for the registry (P01 Tables 4–5 give file-level metadata) |
| EDS (ethanol distillation) | P09 (843,321 records, 47 parameters, open-sourced p5) | Not used | Open alternative with hardware-testbed provenance |
| UNSW-NB15 | P05 | Not used | IT-network domain; useful only as contrast |
| CAN/CAV | P08 | Not used | Off-domain (its own flaw) |
| AgentDojo | P12 (Travel/Workspace/Banking/Slack), P13 (97 tasks/629 cases p6), P14 (reconstructed + 949 data-stream cases) | Not used (no OT content) | The injection-benchmark canon — cite for the gap statement (PC-49) |
| SIREN | P14 (959 tool-stream cases, 5 vectors) | Not used | Structural template for F1–F5 fixture design |
| SWaT-Dec2019 | P19 (13,201 samples) | Not used | A small alternative SWaT slice |
| AEGIS-OT synthetic mini-fixture | — | Offline reproducibility substrate | Clearly labeled; not a benchmark claim |

---

## 18. Baseline Comparison

Candidate baselines for AEGIS-OT's evaluation, drawn from the corpus:

| Baseline | Source | Strength | Weakness | Appropriate? | Metric used there |
|---|---|---|---|---|---|
| Isolation Forest (window stats) | AEGIS-OT PC-04; P15 Table 3 p5 (F1 0.5520 on SWaT); P16 ECOD/DeepSVDD as lightweight references | Cheap, robust, in-code | Weak on temporal structure | Yes (MVP baseline) | P/F1 |
| LSTM-AE (+OCSVM) | P18 (specs Table II p5, results 96%/AUC 0.8628) | Published SWaT numbers; PC-07 ablation target | Threshold-sensitive; OCSVM params undisclosed | Yes (stretch ablation DET-06) | Acc/P/R/F1/AUC |
| Spatio-temporal AE | P20 (F 0.851/R 0.757/P 0.973 Table III p7) | Strong recall; per-sensor thresholds | z/M unreported; single run | Optional literature row | P/R/F |
| CNN-AE / LSTM-AE ± attention | P21 (Table I p4: CNN-AE F1 0.824 + 12 imported baselines) | Ready comparison table | Heterogeneous imported numbers | Optional literature row | P/R/F1 |
| TCAE (P15's own) | P15 (F1 0.7436, Table 3 p5) | The closest-architecture reference point | P15's own run; not AEGIS-OT's implementation | Reference row only | P/R/F1 |
| Graph/centrality DL (CGAAD) | P10 (99.91%/99.19%, shuffled splits p11/p19) | Shows family exists | Protocol unreliable — cite with caveat | Contrast row only | Acc/F1/MCC |
| Decision fusion (DT/SVM/LSTM/XGB) | P09 (soft-voting gains p9) | Ensemble alternative; runtime numbers | Different dataset (EDS) | Related-work row | P/R/F1/runtime |
| Reject-option NIDS | P04 (1% error @ 0.5% rejection p7) | Conceptual precedent for verdicts | Network-flow domain | Conceptual citation only | Error+rejection |
| Data-mined invariant rules | P02 (35/35 SWaT, 2.06% FP p9) | Physics-adjacent; strong numbers | Supervised, needs labeled attacks | Related-work row (different setting) | Attack coverage/FAR |
| Physics hybrids (PbNN/DAD) | P17 (100%/0% live p11) | Strongest detection claims in corpus | Live-plant eval, not reproducible from public data | Motivation row | Dr/Fr/CiF |
| Naive agent (no grounding/validator) | AEGIS-OT EXP-05; corpus analog: no-defense arms of P12/P13/P14 | The essential internal baseline | — | Yes (RQ3 ladder) | ASR/unsafe rate |
| Grounded-but-unvalidated agent | AEGIS-OT EXP-06; analog: P14's Unverified ablation (ASR 45.05 Table 3 p8) | Isolates validator effect | — | Yes | ASR |
| LLM-judge defense | P11 (GPT-4 inspector), P12 (same-model shield) | The alternative defense family | LLM-mediated, adaptive-attack susceptible (both concede) | Related-work comparison, not a baseline to reimplement | Safety score / ASR |

Recommendation: the academically strongest evaluation pairs (a) the internal ladder (EXP-05→07) with (b) published literature rows (P15/P18/P21 detector tables) and (c) P16's IOU/Accuracy protocol for the XAI cross-check — all three grounded in the corpus, none invented.

---

## 19. Literature Limitations (and whether AEGIS-OT addresses them)

| Paper | Key limitations (located) | Addressed by AEGIS-OT? |
|---|---|---|
| P01 | Needs labeled normal data (p17); no numeric results in prose; attention-as-explanation (p9); HAI-only | Partially: normal-only discipline; attention prohibition (R18); different datasets |
| P02 | Needs historical labeled attacks; low rule versatility; per-plant retraining (pp. 10–11) | Partially: declarative invariants need no attack history; but AEGIS-OT's rules are also plant-specific |
| P03 | No system, no evaluation (whole paper) | AEGIS-OT operationalizes MITRE-ICS mapping deterministically (TINTEL-01) |
| P04 | Flow-only 15 s windows; pool-dependent selection; internal inconsistencies (§IV–VI) | Domain-different; verdict-semantics borrowed, not limitations |
| P05 | Non-OT dataset; random split; chart-only baselines (pp. 2–4) | Yes: OT data + temporal splits + charter metrics |
| P06 | Toy state; 3 fixed attackers; no variance (pp. 5–7) | Yes: measured attack suite; median-over-seeds |
| P07 | Vision-only; data-dependent thresholds; no robustness tests (p9) | Domain-different; XAI-by-training cited as nuance |
| P08 | Dataset mismatch (CAN vs ICS); contradictory numbers (pp. 1, 5, 6) | Contrast case only |
| P09 | Static voting weights; auto-dispatched PLC alarms (p7); 3-rep averaging | Partially: human gate replaces auto-dispatch; median-over-seeds |
| P10 | Topology scarcity (p19); shuffled splits; FDI-only; no localization/stress | Yes: temporal splits, stress protocol, attribution layer |
| P11 | 70 datapoints; LLM-as-judge; no adversarial eval; no human gate (pp. 6–9) | Yes: adversarial suite; deterministic metrics; human approval |
| P12 | Same-model shield; adaptive-attack susceptibility; single benchmark; no human oversight; text-only (p8) | Yes: independent deterministic validator; OT-domain text+numeric attacks; human gate |
| P13 | Text-output IPI out of scope; scale limits; needs strong planners; no OT (p9) | Partially: OT domain + small local model (Qwen2.5-7B) targets exactly the weak-planner regime |
| P14 | LLM-verifier overhead; immutable constraints vs open-ended tasks; BU cost on Gemini (p9, Table 2 p7) | Yes: deterministic validator is cheap; sandbox bounds the cost of conservatism |
| P15 | Low recall (0.6136); undisclosed DBSCAN/KDE params; SHAP ~40 s/window; no faithfulness metric; no user study (pp. 5–11) | Yes: p99 threshold disclosed; residual attribution is O(n); consistency scoring; pilot study |
| P16 | Inverted TP/TN (p7); threshold tuned on P1 only; SWaT-only; significant FPs (p11) | Partially: charter fixes metric definitions; multi-dataset (WUSTL) planned |
| P17 | Empirical UCL/LCL tuning; 2-h live recalibration; live-plant-only eval; 5-sensor scope (pp. 8–11) | Partially: declarative rules avoid CUSUM tuning; public-dataset eval; but AEGIS-OT's rule scope is likewise narrow |
| P18 | Split hygiene unclear; OCSVM params unreported; narrow baselines (p6) | Contrast for charter discipline |
| P19 | Single-parent assumption; Gaussian residuals; threshold tuning on labeled attacks; inconsistencies (pp. 2–4) | Contrast case for root-cause humility |
| P20 | z/M unreported; no per-attack results; single run; root-cause conflation (pp. 5–7) | Partially: charter + per-attack reporting |
| P21 | Attention-recall claim contradicts Table I; no hyperparameters; XAI protocol covers one model (pp. 4–5) | Contrast for consistency scoring |

**Narrative use:** AEGIS-OT's limitation section can honestly state that it addresses the *evaluation-discipline* limitations of the corpus (splits, metrics, variance, faithfulness) and the *safety-mechanism* gaps of the agent-security cluster (determinism, human gate, binding), while inheriting the corpus's unresolved *domain-transfer* limitation (testbed-to-plant).

---

## 20. Research Gaps (corpus-grounded)

| # | Gap | Classification | Evidence |
|---|---|---|---|
| G-1 | No OT/ICS agent-safety benchmark (F1–F7-like corpus) | **Missing from corpus** | P12/P13/P14 benchmarks are Workspace/Slack/Travel/Banking (§17) |
| G-2 | No deterministic (LLM-free) safety gate for agent actions | Missing | All corpus defenses are LLM-mediated (P11 §3.4; P12 §5.1; P14 §4.5) or structural-only (P13) |
| G-3 | No human approval / content binding in agent pipelines | Missing | Zero approval/hashing mechanisms in P11–P14 (dossier greps) |
| G-4 | Numeric (non-textual) attack channel against agents | Missing | Every corpus attack is text-borne (P14 Table 1 p4; P12 §5.2) |
| G-5 | Attribution-faithfulness measurement beyond P16 | Underexplored | Only P16 measures vs GT; P21 probes; P15 asserts visually |
| G-6 | Analyst decision-quality evaluation (does XAI help?) | Underexplored | Deferred by P15 (p11), P16 (p11), P01 (unmeasured) |
| G-7 | Stress/drift robustness protocols for ICS detectors | Underexplored | Only P17 has a real drift experiment; no augmentation grids |
| G-8 | Point-adjustment-corrected evaluation in ICS literature | Contradictory/absent | No corpus paper uses or critiques PA; AEGIS-OT's PA%K is externally anchored |
| G-9 | RAG trust-tiering / provenance-citation retrieval | Underexplored | P12's privilege hierarchy + P11's regulation retrieval are the nearest; no tiers/citation objects |
| G-10 | Integration of detection→attribution→agent→gate on one OT pipeline | Missing (system level) | Corpus clusters never connect (§8) |

---

## 21. What Already Exists (EXISTING IDEA — described in prior literature)

| AEGIS-OT element | Status | Evidence |
|---|---|---|
| Dilated causal-conv autoencoder on SWaT, normal-only | Existing (P15) | P15 §3.2.2 p4, Table 2 p5 |
| Reconstruction-error-based top-k sensor attribution | Existing as a recognized mechanism (P15's description of DAEMON [30]; P20 heatmap) | P15 Table 1 p3; P20 §IV-E p7 |
| Physics invariants for ICS detection | Existing, stronger (P17; P02 mined rules) | P17 p4/Table III p7; P02 p9 |
| Isolation-Forest baseline on SWaT | Existing with numbers (P15 Table 3 p5) | F1 0.5520 |
| Quantile/percentile thresholds on normal residuals | Existing family (P16 p95+GHOST; P18 p95; P21 quantile) | P16 §5.2.2 p7; P18 p4; P21 p3 |
| XAI-for-ICS (SHAP/LIME/ALE/IG/CAM) | Existing, well developed (P15/P16/P21/P01/P02/P07) | §4 entries |
| LLM + ATT&CK-ICS knowledge organization | Existing (P03) | P03 §III p2 |
| Injected-context attacks on LLM agents | Existing, well characterized (P12/P13/P14; P11 absent) | §4 entries |
| Task/argument alignment checking (C5-analog) | Existing as LLM mechanism (P12 Fig. 6 p16; P14 §4.5) | — |
| Plan/tool allowlisting (C2-analog) | Existing as structural mechanism (P13 pp. 2, 4–5; P14 §4.2) | — |
| Read-only tool segregation (C4-analog) | Existing (P13 p5 Query/Command split) | — |
| Simulation-only execution doctrine | Existing (P06 CAGE; P11 ToolEmu) | P06 p1/p5; P11 p3 |
| Tiered trust of untrusted content | Existing as privilege hierarchy (P12 §2 p2) | — |
| Reject/withhold-under-uncertainty semantics | Existing (P04) | P04 §IV-B p4 |
| Immutable audit logs (as aspiration) | Existing mention (P15 §3.5 p6) | — |
| Pattern-based injection markers as one defense layer | Existing (baseline family in P12/P13) | P12 §5.1 p6 |
| Benign-vs-attack utility metrics (BU/UA/ASR) | Existing (P13 §4.1 p6; P12 §5.1 p6; P14 §5.1 p6) | — |

## 22. What We Implement (IMPLEMENTATION OF EXISTING IDEA)

TCN-AE pipeline (P15 family) with AEGIS-OT's own windowing/scoring choices (W=60, z-score train-fit, τ=p99 validation) — implementation, not contribution. Isolation-Forest baseline (standard sklearn; P15 numbers as reference). Declarative invariants R1–R5 (simplified P17/P02-style relations). Residual-share attribution (normalized/floored variant of the reconstruction-error top-k mechanism). MITRE-ICS rule table (deterministic P03-alternative). Tiered RAG with heading-aware chunking + pinned embedder (P12/P11-informed design, own implementation). ReAct runner with lease/reaper (P14-substrate choice). Pattern filter C3 (baseline-family implementation). Charter metrics (P13/P12/P14 metric family + extensions). Attack-fixture design (SIREN/P12-informed families).

## 23. What We Modify (MODIFICATION)

1. **Attribution semantics**: corpus conflates attribution with root cause (P15 p2; P20 p7; P19 p4); AEGIS-OT renames it hypothesis-support and binds explanations to a "HYPOTHESIS (not a verdict)" label (R19) — a discipline modification with P16's failure case as motivation.
2. **Threshold discipline**: percentile thresholds exist (P16/P18/P21) but are fit on training errors or with undisclosed procedures; AEGIS-OT's modification is validation-only fitting, frozen before test, charter-recorded.
3. **Reject semantics**: P04 rejects to a honeypot; AEGIS-OT modifies the destination to a human approval flow with expiry-escalation.
4. **Allowlist enforcement point**: P13 allowlists at plan level (agent-internal); AEGIS-OT modifies to an external, deterministic post-hoc validator against a versioned YAML registry — enabling independent audit.
5. **Entailment mechanism**: P14's V_entailment is an LLM call; AEGIS-OT modifies to rule-based field-entailment (tol 1e-6) + invariant-direction conflict + persistent-failure escalation.
6. **Injection markers**: corpus treats pattern defense as primary-or-baseline; AEGIS-OT demotes it to C3 of C1–C5 after normalization/decoding — a scoped modification.
7. **Attack-taxonomy extension**: SIREN's 5 vectors are re-targeted to OT semantics (propose_action/sandbox) with two new families (F6, F7).

## 24. What We Integrate (ENGINEERING INTEGRATION / NEW COMBINATION)

The end-to-end chain — detection (P15-family) → attribution (P16-informed evaluation) → invariants (P17/P02-style) → MITRE-ICS (P03-knowledge) → tiered RAG (P12-informed) → single grounded agent (P14-substrate) → deterministic validator (C1≈P13, C2≈P13/P14, C3≈pattern-family, C4≈P13, C5≈P14/P12) → human approval (none in corpus) → sandbox (P06-doctrine) → audit — is a combination **not described in any of the 21 papers**, whose two halves (detection/XAI cluster and agent-security cluster) never connect. Per master-prompt §18 logic: the literature contains the parts; the provided literature does not contain the integration. This is a **system-level integration contribution** claim — defensible against this corpus, to be phrased cautiously (§26).

## 25. Potential Novel Contributions (candidate-by-candidate, stress-tested)

### C-01 — Deterministic, LLM-free validator as an independent safety layer (C1–C5)
- **Project approach:** five ordered code checks; single pure verdict lattice; no LLM anywhere in the gate.
- **Closest literature:** P14 (verify-before-commit; two-stage LLM verifier), P13 (structural constraints; anti-LLM-judge argument), P12 (LLM alignment shield), P11 (GPT-4 inspector).
- **Similarities:** C2≈P13's plan allowlist; C5≈P14's entailment + P12's argument checking; layering≈P11's pre/in/post.
- **Differences:** all four enforce via LLMs or agent-internal structure; none is deterministic code, none externalizes the gate, none records per-check results with a determinism flag, none has a golden-tested pure verdict function.
- **Interpretation:** potential novel contribution (mechanism class absent from corpus); not global novelty (CaMeL — cited by P14 but not in the corpus — is externally adjacent and must be checked; see §26).
- **Evidence:** P13 p2/p12; P12 p8/p13; P14 pp. 5–6; P11 §3.4 p5.
- **Confidence:** MEDIUM-HIGH (corpus-level); LOW-MEDIUM (global, pending external check).

### C-02 — SHA-256 content binding of validator verdict ↔ human approval ↔ execution
- **Closest literature:** none in corpus implements hashing/approval/immutable revisions; nearest mention is FATH's authentication tags (cited only in P12's related work, p8).
- **Interpretation:** potential novel contribution at corpus level; mechanism is safety engineering, so novelty is in the *demonstrated, measured* binding (EXP-09 battery), not the cryptography.
- **Confidence:** HIGH (corpus-level absence verified); MEDIUM (global — FATH and audit-blockchain literature exist externally).

### C-03 — OT/ICS agent-safety benchmark (F1–F7, 32 cases) incl. F7 numeric spoofing
- **Closest literature:** P14's SIREN (959 cases, 5 text vectors); P12's AgentDojo attack set; P13's four attacks.
- **Differences:** all corpus attacks are text; none touches OT telemetry; F7 (numeric-only sensor spoofing targeting attribution) has no analogue anywhere; F6 (hallucination probe) likewise absent.
- **Interpretation:** potential novel contribution; must be phrased as "first OT/ICS agent benchmark **to our knowledge within the examined corpus**" — SIREN dwarfs it in size and InjecAgent/AgentDojo are established, so the claim is domain-gap-filling, not scale.
- **Confidence:** HIGH for the F7/OT gap; MEDIUM overall (team-authored corpus is small; scope-limited claim mandatory).

### C-04 — Deterministic (code-only) evaluation of a safety gate via bypass battery (EXP-09)
- **Closest literature:** none (P14's ablation measures ASR effect, not gate integrity under tamper/expiry/replay).
- **Interpretation:** potential methodological contribution (verification-of-the-gate as an experiment class).
- **Confidence:** MEDIUM (corpus-level absence verified; security-testing literature exists externally).

### C-05 — Naive→grounded→validated ladder isolating the validator effect on OT data
- **Closest literature:** P14's module ablation (verifier off: ASR 45.05, Table 3 p8); P12's defense-vs-no-defense design.
- **Differences:** corpus varies defense components inside one architecture; AEGIS-OT's ladder crosses capability tiers (no grounding / grounding / grounding+gate) on OT fixtures with false-block as a first-class metric.
- **Interpretation:** modification+extension of an established design pattern; contribution is the OT-domain measurement, not the design.
- **Confidence:** MEDIUM.

### C-06 — Tiered RAG (trusted/public/hostile) with production hard-exclusion of hostile content
- **Closest literature:** P12's privilege hierarchy (Ls≻Lu≻La≻Lt) and "tool-level may still not be trustworthy"; P11's regulation retrieval; P14's sanitize-and-use doctrine.
- **Differences:** corpus has no document-tier firewall, no `TIER_DENIED`/`RETRIEVAL_UNAVAILABLE`/`NO_EVIDENCE` semantics, no typed citation objects carrying tiers.
- **Interpretation:** extension of the privilege/trust principle into retrieval infrastructure; likely a strong *engineering* contribution, moderate *research* novelty.
- **Confidence:** MEDIUM.

### C-07 — Fuzzy-rough channel reduction under a stress protocol
- **Closest literature:** none uses fuzzy-rough sets; alternatives are P21 RFE, P20 KS-test, P10 centrality.
- **Interpretation:** method-application novelty only if the experiment shows robustness preservation; keep as hypothesis (R25/R30).
- **Confidence:** LOW-MEDIUM (depends on results; method itself is classical soft computing).

### C-08 — PA%K + stress + charter evaluation discipline for ICS detection
- **Closest literature:** corpus has none of these; externally anchored to Kim et al. AAAI-2022.
- **Interpretation:** not a new metric (external), but a corpus-first *application* with charter enforcement; frame as evaluation contribution.
- **Confidence:** MEDIUM-HIGH (application-level).

### C-09 — Attribution-with-humility pipeline (residual shares + invariants + "HYPOTHESIS" labeling + consistency score)
- **Closest literature:** P16 (faithfulness measurement + failure case), P01 (cause-vs-likelihood), P20 (heatmap), P19 (causal decomposition).
- **Differences:** no corpus paper couples attribution to physics-invariant corroboration and to an agent's grounding contract, or labels explanations as non-verdicts.
- **Interpretation:** modification/integration; the *combination* is the contribution.
- **Confidence:** MEDIUM.

### C-10 — Physics invariants wired into action validation (C5 invariant-direction consistency)
- **Closest literature:** P19's propagation ordering (conceptual); P14's invariant compliance (task-level, not physical).
- **Differences:** corpus uses invariants for detection (P17/P02) or task constraints (P14); none routes invariant failures into mitigation vetting.
- **Interpretation:** new-combination; small but clean.
- **Confidence:** MEDIUM.

## 26. Novelty Risk Assessment

| Risk | Detail | Mitigation |
|---|---|---|
| **R-1 CaMeL (external)** | P14 cites Debenedetti et al. 2025 "Defeating prompt injections by design" — a capabilities/control-flow design that is *externally* adjacent to deterministic gating (it is in P14's baseline set with TS ASR 44.83). Not in the corpus; C-01 must be checked against it before any "novel" phrasing. | External literature check; if CaMeL covers the mechanism, rephrase C-01 as "deterministic validator **independent of the agent**, with verdict tiers + human approval, on OT data" |
| R-2 FATH (external) | Hash-based authentication tags for tool responses (P12 p8 related work) — adjacent to C-02 | Cite FATH; differentiate: FATH authenticates tool responses; AEGIS-OT binds the *plan revision* across validation/approval/execution |
| R-3 InjecAgent/AgentDojo expansion into OT | Any 2026 work could port injection benchmarks to ICS; corpus cannot exclude this | Scope claims "to our knowledge"; search before submission |
| R-4 P15 follow-ups | P15 is Dec 2025 and defers online deployment/user studies (p11); anyone may publish TCAE+SHAP+user-study next | AEGIS-OT's detection claims must stay protocol/robustness-focused, not architecture-focused |
| R-5 Point-adjustment literature | Kim et al. AAAI-2022 + follow-ups already own the metric critique | Cite; frame PA%K application as corpus-first, not field-first |
| R-6 "Everything is integration" critique | Reviewers may call the pipeline "just integration" | Pre-empt: the measurable gate-integrity results (EXP-09), the F7 numeric channel, and the false-block decomposition are components no corpus paper has; lead with those |
| R-7 Corpus-bounded novelty | All novelty conclusions are relative to 21 papers | State the corpus boundary explicitly in any novelty sentence (master-prompt §20 requirement) |
| R-8 Internal implementation gaps | §13.1 deviations (degenerate attribution path; EXP-01/02 split collapse; vacuous check_invariant) could invalidate published claims if unfixed | Fix before running headline experiments; the report generator only consumes charter functions (INV-018) |

---

## 27. Citation Recommendation Map

For planned paper statements — best source + secondary + provenance. (Quotes available in `analysis/notes/PXX.md` §Verbatim Quote Bank; all are machine-verified substrings.)

| Planned claim in AEGIS-OT paper | Best source (provenance) | Secondary | Reason |
|---|---|---|---|
| "Feature-attribution XAI predicts likelihood, not cause" | P01 p2 + p15 (verbatim) | P16 p11 | Independent articulations; P16 adds the empirical failure |
| "SHAP explanations can contradict ground truth" | P16 §6.4 p11 ("This contradicts the actual attack point") | P21 | The corpus's only measured failure case |
| "TCN-based AEs are competitive on SWaT" | P15 Table 3 p5 (F1 0.7436; IF 0.5520) | P18, P21, P20 | Direct architecture precedent + baseline numbers |
| "Kernel-SHAP explanations of AE detections cost ~40 s/window on an A100" | P15 §3.4 p6 (verbatim) | P16 Table 6 p10 (SHAP 1,369 s on ECOD) | Cost accounting for the XAI-05 stretch |
| "Physics invariants yield 100% detection / 0% FP incl. drift" | P17 p11 + p9 (verbatim) | P02 p9 | Strongest invariant evidence; live plant |
| "Invariant-style relations can be mined from data" | P02 p9 (Rule-ID 1; 35/35) | P17 | Data-driven variant |
| "SWaT conventions: 496,800 train / 449,919 test; trim first 21,600 s; 41 attacks (36 physical)" | P16 §4–5 pp. 4–5 | P15 §4.1 p7; P18 p4 | Most complete dataset reporting |
| "Thresholded metrics can mislead (96% metrics vs AUC 0.8628)" | P18 p4 (verbatim) | P08 (contradictions), P10 (shuffled 99.91%) | In-corpus demonstration |
| "Rejecting uncertain outputs and routing them to safety is established" | P04 §IV-B p4 + Eqs. 1–2 p5 | P14 (forbid/approve) | Reject-option theory precedent |
| "Indirect prompt injection hijacks tool-using agents (ASR up to ~48–74% undefended)" | P12 Table 1 p6 (47.69%); P14 Table 2 p7 (vanilla 73.83 TS) | P13 Table 1 p8 (13.16%) | Measured baselines |
| "Structural tool allowlists cut ASR to ≤1%" | P13 p7 (verbatim "never exceeding 1%") + Table 1 p8 | P12 (2.07% via alignment) | Strongest structural result |
| "Verify-before-commit with entailment checking is the current frontier" | P14 §4.5 pp. 5–6 + Table 3 p8 (ablation) | P12 | Latest mechanism + ablation evidence |
| "LLM-judged defenses are compromisable" | P13 p12 (verbatim) + P12 p8 (limitations) | P11 (as the LLM-judge design) | Direct support for PC-35 |
| "Agent-injection benchmarks cover Workspace/Slack/Travel/Banking — none covers OT/ICS" | P13 §4.1 p6 + P12 §5.1 p5 + P14 §3 pp. 3–4 | — | Triangulated gap statement |
| "SIREN defines 5 tool-stream injection vectors (959 cases)" | P14 Table 1 p4 + Tables 4–5 p14 | — | Taxonomy source for F-family design |
| "Safety enforcement need not reduce utility" | P11 p6 (verbatim "synergistic") + P12 pp. 6–7 (utility rises) | — | Counter to the obvious objection |
| "LLM-organized ATT&CK-ICS knowledge is proposed for analyst Q&A" | P03 §III-A/B p2, Table II p2 | — | Only corpus ATT&CK-ICS work |
| "Autonomous RL responders act without approval gates in simulation" | P06 p1/p5 (action space) | — | Contrast case for the human gate |
| "Attribution ≠ root cause; P15/P19/P20 conflate them" | P15 p2; P19 p4; P20 p7 (as contrast) + P16 p11; P01 p2 (as support) | — | Both sides citable |
| "Point-adjustment overstates detector performance" | **Kim et al., AAAI 2022 — EXTERNAL, not in corpus** | P10/P05 as in-corpus examples of protocol laxity | Never cite corpus papers for the PA critique |
| "Log/telemetry injection studies show 0–86% command execution" | **External preprints (LogJack etc.) — not in corpus** | P12/P13/P14 as IT-domain agent analogs | Keep the corpus/external distinction explicit |

---

## 28. Proposed Related-Work Narrative (theme-organized, not paper-by-paper)

**Theme A — ICS anomaly detection on SWaT-class testbeds.** Reconstruction-based semi-supervised detectors dominate the corpus: autoencoder variants (P15 TCAE, P18 LSTM-AE, P20 spatio-temporal AE, P21 CNN/LSTM-AE) and classifier/ensemble/graph designs (P09 fusion, P10 graph-aware GCN, P05/P08 CNN-LSTM). Reported performance ranges from F1 0.55–0.74 under disclosed protocols (P15, P16, P21) to 99%+ under shuffled splits (P10) — the spread itself evidencing that protocol quality, not architecture, separates the literature. *Connect to project:* AEGIS-OT inherits the normal-only AE paradigm (P15) but contributes protocol discipline (PA%K, stress, seeds) and positions detection as a substrate, not a contribution.

**Theme B — Explainability and attribution for ICS detection.** Post-hoc methods (SHAP, LIME, ALE, IG — P16's measured comparison; P15's per-attack SHAP; P21's validated SHAP/counterfactuals), activation-based localization (P02 CAM-distilled rules; P07's interpretability-trained attention), and distance/shapelet explanations (P01). Two findings recur: explanations are not measured against ground truth except by P16, and when they are, they can fail (P16's attack-24 contradiction); and feature importance ≠ cause (P01). *Connect:* AEGIS-OT's residual-share attribution is the mechanistic (non-post-hoc) alternative; the SHAP cross-check (XAI-05) adopts P16's IOU/accuracy protocol; the "HYPOTHESIS (not a verdict)" labeling is the direct response to Theme B's failure evidence.

**Theme C — Physics-aware and causal modeling.** P17's P&ID invariants + learned surrogates (live-plant validated), P02's mined control-logic rules, P19's causal DAG + calibrated risk. Invariant/causal structure buys drift robustness that purely data-centric models lack (P17's manual-mode experiment). *Connect:* AEGIS-OT's five declarative invariants are a deliberately lightweight member of this family, distinguished by being wired into both explanations and action validation (C5), not just detection.

**Theme D — LLM-agent security under indirect prompt injection.** Four defense paradigms: constitution + LLM inspection (P11), semantic task alignment (P12), structural plan constraints (P13), and verify-before-commit with LLM entailment (P14). All evaluate on general-domain benchmarks (AgentDojo/SIREN), all enforce via LLMs or agent-internal structure, none uses deterministic external gates, human approval, or content binding — and their own limitations sections concede LLM-judge fragility (P13 p12; P12 p8). *Connect:* AEGIS-OT's C1–C5 deterministic validator + hash-bound human approval is the corpus's missing fifth paradigm, evaluated on the corpus's missing domain (OT).

**Theme E — Autonomous response and its rejection.** P06's RL defenders act autonomously in simulation; P09's alarm module auto-dispatches to PLCs. AEGIS-OT's design thesis — measure the agent, gate the action, keep the human — is argued *against* this theme, using P06 as the embodied alternative.

**Theme F — Reliability-aware verdicts.** P04's classification-with-reject-option routes uncertain cases to a honeypot — the corpus's only verdict-withholding mechanism. AEGIS-OT generalizes reject into a four-tier verdict lattice tied to human approval.

---

## 29. Proposed Methodology Narrative

1. **Detection & attribution.** Train TCN-AE on normal-only windows (P15-parity architecture; AEGIS-OT window/scoring choices), score per-sensor normalized residuals, threshold at τ = p99 of validation residuals, attribute via contribution_i = r_i/Σr_j with ε-floor. Evaluate point-wise P/R/F1 + PA%K under the stress grid (noise/zeroing/drift; median over seeds). *Cite:* P15, P16 (protocol), P18 (metric caution), Kim et al. (external, PA critique), P17 (stress motivation).
2. **Explainability & invariants.** Build explanation objects = hypothesis NL + top-3 sensors + invariant results + citations; five declarative invariants corroborate/contradict; consistency score across anomaly families. *Cite:* P16 (faithfulness + failure case), P01 (importance ≠ cause), P17/P02 (invariants).
3. **Threat mapping & knowledge.** Rule-based MITRE ATT&CK for ICS mapping with recorded basis; tiered RAG over trusted/public/hostile corpora with typed citations and production hostile-exclusion. *Cite:* P03 (ATT&CK-ICS organization), P12 (privilege-trust principle).
4. **Agent & grounding.** Single analyst-invoked ReAct planner, 5 tools, 12-step cap, evidence-or-"insufficient data" contract. *Cite:* P14 (ReAct substrate), P11 (layered safety premise).
5. **Deterministic gate & approval.** C1 provenance (exact-ID), C2 grammar allowlist, C3 normalized pattern filter, C4 risk classes, C5 evidence-entailment + invariant-direction consistency; verdict lattice; immutable revisions with SHA-256 triple binding; all-or-nothing human approval, 24 h expiry → escalation; sandbox-only execution; append-only audit. *Cite:* P13 (allowlist; anti-LLM-judge), P14 (entailment; ablation), P12 (argument checking; metrics), P04 (reject semantics), P06 (simulation doctrine), FATH (external, hash-tag adjacency).
6. **Adversarial evaluation.** 32 fixtures, 7 families; naive→grounded→validated ladder; metrics ASR/unsafe/block/false-block/refusal via charter; EXP-09 bypass battery. *Cite:* P14 (SIREN taxonomy), P12/P13 (metric definitions), P11 (safety-utility synergy).
7. **Human pilot.** Small-N exploratory decision study. *Cite:* P15/P16 (user-study deferral as the gap).

---

## 30. Proposed Research Paper Structure (adapted to AEGIS-OT)

| Section | Content | Cite | Established vs. ours |
|---|---|---|---|
| 1. Abstract | Measurable safety architecture + gate results + F7 gap | — | ours |
| 2. Introduction | Saturated detection ≠ safe response; log-as-attack-surface; no OT agent benchmark | P10/P05 (saturation examples); P12–P14 (injection); external (CISA 2025, Kim 2022) | established problem + our gap |
| 3. Background & Related Work | Themes A–F (§28) | all clusters | established |
| 4. System Overview | Pipeline + non-goals (never real hardware) | P06 (simulation doctrine) | ours |
| 5. Detection, Attribution, Explanation | TCN-AE, residual attribution, invariants, HYPOTHESIS labeling | P15, P16, P17, P02, P01 | established mechanisms + our discipline |
| 6. Threat Mapping & Knowledge Layer | TINTEL-01 rules + tiered RAG + trust firewall | P03, P12 | ours (integration) |
| 7. Validator & Approval Architecture | C1–C5, verdict lattice, SHA-256 binding, approval state machine, sandbox | P13, P14, P12, P04, P11 (contrasts) | **core contribution** |
| 8. Adversarial Evaluation Suite | F1–F7 taxonomy + ladder + bypass battery + charter metrics | P14 (SIREN), P12/P13 (metrics) | **core contribution** |
| 9. Experimental Setup | SWaT/WUSTL registry, splits, stress protocol, baselines | P16 (dataset conventions), P02 (baseline reproduction), P15/P18/P21 (reference rows) | established + ours |
| 10. Results | Detector table; ladder effects; attack-suite outcomes; gate integrity (EXP-09); XAI cross-check; pilot (exploratory) | — | ours (all measured) |
| 11. Discussion | False-block trade-off; determinism vs LLM-judge; corpus contradictions navigated | P13 vs P14 (utility disagreement); P11/P12 (safety-utility) | ours |
| 12. Limitations | Testbed fidelity; sandbox simplicity; scripted-LLM offline metrics; small attack corpus; attribution ≠ root cause | — | ours (honest) |
| 13. Conclusion | — | — | ours |

Claim-discipline (from Rules R24/R25): no "novel"/"first" without the corpus-bounded qualifier; hypotheses labeled; negative results reported; every number charter-derived.

---

## 31. Evidence Table (top provenance anchors)

| # | Finding used by the paper | Paper · page · location | Quote/number (verbatim where quoted) |
|---|---|---|---|
| E1 | TCAE on SWaT: P 0.9435 / R 0.6136 / F1 0.7436; IF F1 0.5520 | P15 Table 3, p5 | numbers as listed |
| E2 | SHAP cost: ~9,400 evaluations, ~40 s/window (A100) | P15 §3.4, p6 | "computing SHAP values for one window takes approximately 40 seconds." |
| E3 | SHAP top feature contradicts true attack point (attack 24) | P16 §6.4, p11 | "This contradicts the" (…actual attack point…) |
| E4 | 4-XAI comparison: SHAP Acc 87.77/82.76; IOU ~6–7% | P16 Table 6, p10 | numbers as listed |
| E5 | PbNN live-SWaT: 100% Dr / 0% Fr | P17 p11 | "found to be 100% and false alarm rate was 0%" |
| E6 | Invariant physics: MV101=On ∧ LIT101>H impossible normally | P02 p9 | "will never appear simultaneously in normal industrial procedures." |
| E7 | LU-IDS rules: 35/35 SWaT, 15/15 WADI, FP 2.06%/4.29% | P02 p9 | "detect 35/35 attacks on the SWaT dataset and 15/15 attacks" |
| E8 | Thresholded metrics mislead: 96% metrics vs AUC 0.8628 | P18 p4 | "achieves 96% across all threshold-dependent metrics," (…AUC 0.8628…) |
| E9 | Reject option: withhold + route to honeypot | P04 §IV-B p4, §V-A p5 | mechanism + Eqs. 1–2 |
| E10 | Structural allowlist: ASR ≤1%, avg 0.69% | P13 p7 + Table 1 p8 | "never exceeding 1%." |
| E11 | Anti-LLM-judge argument | P13 App. B p12 | "this method remains vulnerable if the LLM-judge" (…itself is compromised.) |
| E12 | Task-alignment defense: ASR 47.69→2.07, utility rises | P12 Tables 1–2 pp. 6–7 | "reduces the ASR to 2.07%" (…utility at 69.79%.) |
| E13 | Same-model shield: adaptive-attack susceptibility (own limitation) | P12 p8 | "susceptibility to adaptive attacks." |
| E14 | Verify-before-commit: V = compliance ∧ entailment; no-verifier ASR 45.05 | P14 §4.5 pp. 5–6 + Table 3 p8 | "V (τi, C, q) = Vcompliance(Mτi, C)∧Ventailment(τi, q)" |
| E15 | SIREN: 959 cases, 5 vectors, AgentDojo-derived; no OT | P14 Table 1 p4; §3 pp. 3–4 | "959 tool stream injection" (…cases…) |
| E16 | TrustAgent: GPT-4 inspector; safety 2.15→3.43; LLM-judge metrics | P11 §3.4 p5; Table 2 p7 | numbers as listed |
| E17 | AgentDojo domains: Workspace/Slack/Travel/Banking (no ICS) | P13 §4.1 p6; P12 §5.1 p5 | "Workspace, Slack, Travel, and Banking" |
| E18 | Feature importance ≠ cause | P01 p2 + p15 | "feature importance alone cannot fully explain the causes of anomalies" |
| E19 | Shuffled splits produce saturated headlines: 99.91% acc SWaT | P10 p11 (protocol) + p19 (result) | "shufﬂing was performed to randomly rearrange all samples," |
| E20 | CAGE autonomous defense, no approval path | P06 p1/p5 | action space incl. autonomous Restore/Remove |
| E21 | ATT&CK-ICS knowledge organization for LLM IDS (no experiments) | P03 §III p2, Table II p2 | "structured learning format based on the ATT&CK ICS matrix." |
| E22 | Attribution-as-root-cause conflations (contrast set) | P15 p2; P19 p4; P20 p7 | "pinpoint[s] root causes"; "~92% of cases"; "pinpoint the anomaly root cause" |

---

## 32. Final Completeness Audit

- [x] Every provided paper inspected — 21/21 (P01–P21), zero skipped; text read in full with page markers.
- [x] Every paper has an analysis record — `analysis/notes/P01..P21.md`, uniform 15-section format.
- [x] Major sections of every relevant paper examined — section maps + page-by-page relevance logs in every dossier.
- [x] Figures considered — captions + in-text discussion + text-layer labels for all; **visual inspection impossible in this runtime (disclosed at top and in every dossier's Uncertainties)**; two dossiers supplemented with OCR crops (P17; P20/P21 partial).
- [x] Tables considered — text-layer values extracted and quoted; raster-only values explicitly marked unreadable rather than guessed (e.g., P01 Tables 7–9; P02 Tables II–VIII).
- [x] Equations considered — numbered equations transcribed/verified where the text layer allows (P15 Eq. 1–2; P16 Eq. 1–13; P02 Eq. 1–10; P17 Eq. 1–13; P13 Eq. 1–4; P12 Eq. 1 + Algorithm 1; P20 Eq. 13; P11 Eq. 1–2); ambiguous glyphs flagged as UNCERTAIN (e.g., P15 Eq. 2 subset symbol; P16 Eq. 4 rendering; P01 Eq. 7 superscript).
- [x] Citation lineage considered — §9; P15⇄P16 mutual-citation pair; P13/P14 disagreement; P15's "Kim et al." disambiguation.
- [x] Project decomposed into atomic components — PC-01..PC-50 (§5).
- [x] Every major component mapped against all papers — §6 forward matrix (all 50 rows) + §7 reverse matrix (all 21 papers).
- [x] Overlapping papers compared — §8 (relationship graph + 10 pairwise analyses).
- [x] Stronger sources identified — §10 (18 claim rows with primary/secondary/complementary).
- [x] Complementary sources identified — same table.
- [x] Novelty claims stress-tested — §25 (10 candidates with evidence + confidence) + §26 (8 risk rows incl. external adjacencies CaMeL/FATH).
- [x] Existing vs modified vs integrated vs potentially novel separated — §21–24.
- [x] Contradictory evidence investigated — §15 (6 corpus-internal tensions).
- [x] Experimental methodology compared — §16 (9-element comparison + 6 recommendations).
- [x] Baselines identified — §18 (14-row table with suitability).
- [x] Dataset/benchmark information extracted — §17 (11 datasets incl. corpus usage details).
- [x] Limitations extracted and mapped — §19 (21-row table: limitation → addressed?).
- [x] Research gaps identified — §20 (10 gaps, classified).
- [x] Code-to-paper mappings performed — §13 (24-row table with file/function-level anchors) + §13.1 (14 deviations).
- [x] Exact provenance recorded — §31 evidence table; per-claim page/section/table/figure locations throughout.
- [x] Unsupported assumptions flagged — §14 (C-8, C-11, C-13 external/absent); §6.1 (no-corpus components); §26 (external-risk rows).
- [x] No fabricated citations/page numbers/line numbers — all page numbers from extraction markers; quotes machine-verified as substrings; unknowns marked UNCERTAIN (notably: raster-only table values, figure-internal visual details).

**Three-pass record.** Pass 1 (extraction): 21 dossiers + verified quote banks. Pass 2 (cross-paper): §8 overlap graph, §15 contradictions, §10 best-source selection, P15⇄P16/P13↔P14 lineage resolution. Pass 3 (project validation): every PC-01..50 received a corpus search (§6); every headline claim received a verification verdict (§14); novelty candidates each have closest-literature + difference + confidence (§25); no important paper overlooked (all 21 appear in ≥1 matrix row; P03/P04/P06/P08 — the least relevant — are still mapped and cited where their niches apply).

## 33. Uncertainties / Open Questions

1. **Figure-level visual content** across all 21 papers is caption/text-derived; visual-only details (diagram wiring, chart shapes, raster table cells) remain unverified — marked per-dossier. If a claim ever hinges on a figure-internal value, re-check against the PDF visually before submission.
2. **Raster-only numeric values** (P01 Tables 6–9; P02 Tables I–VIII cell values; P17 Table V–VII cells beyond text-confirmed ones; P09 Tables II–III) were not extracted and are never quoted in this report.
3. **Venues for P11–P14**: arXiv preprints, no venue stated in text; cited as arXiv with IDs. P13/P14's ACL-style formatting suggests ACL-family submissions — inference only.
4. **P14 internal inconsistencies** (22% vs 18% ASR-reduction claim; appendix table numbering) and **P15's** (Table 5 sums 36 vs "41 documented"; attack 22-vs-23 numbering) are recorded; neither resolved from text.
5. **P16 TP/TN inversion** (p7) makes its precision/recall semantics ambiguous — treat its P/R numbers with care; its IOU/Accuracy XAI numbers are unaffected.
6. **P02 metric convention inversion** (p8) — its FP/FAR numbers are not directly comparable to standard FAR definitions.
7. **P15 baseline provenance** (re-implemented vs cited numbers in Table 3) unstated — do not treat its baseline rows as harmonized.
8. **External-adjacency checks pending**: CaMeL (Debenedetti et al. 2025) and FATH (Wang et al. 2024) must be read before finalizing novelty phrasing for C-01/C-02 (§26 R-1/R-2); Kim et al. AAAI-2022 and the 2025–26 log-injection preprints are cited from the project's own literature, not the corpus.
9. **Corpus-bounded novelty**: all §25 conclusions hold against these 21 papers only; a global novelty claim requires a search beyond the corpus (explicitly out of scope here).
10. **Implementation gaps** (§13.1) must be resolved before headline experimental numbers are generated; until then, offline EXP results measure the harness, not the system.
11. **Licensed SWaT/WUSTL runs** remain pending in the project (documented manual step); all corpus-derived reference numbers are the appropriate placeholders in the interim.
12. **P19's SWaT-Dec2019 slice** (13,201 samples) is much smaller than the full SWaT releases used elsewhere — avoid cross-dataset numeric comparisons with P19.

---

*End of dossier. Supporting artifacts: `analysis/extracted/P01..P21.txt` (page-marked full text), `analysis/pages/PXX/page-NN.png` (234 rendered pages), `analysis/notes/P01..P21.md` (forensic dossiers with verified quotes), `analysis/PROJECT_COMPONENTS.md` (PC inventory), `analysis/CODE_INVENTORY.md` (implementation facts), `analysis/extract_all.py` / `analysis/render_pages.py` (reproducible extraction).*
