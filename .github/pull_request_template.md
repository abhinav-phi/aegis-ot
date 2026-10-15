<!--
Safety reminder: AEGIS-OT is sandbox-only research software. PRs must not
introduce any path that touches real OT/ICS infrastructure.
-->

## Summary

<!-- What does this PR do, in 1–3 sentences? Link related issues
(Fixes #N / Refs #N) and experiments (e.g. EXP-03) where relevant. -->

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that changes existing behaviour)
- [ ] 🔬 Evaluation / research contribution (attack suite, experiments, detectors)
- [ ] 📝 Documentation
- [ ] 🔧 Tooling / infrastructure
- [ ] ♻️ Refactor (no behaviour change)

## Area(s) Touched

- [ ] Backend API (`app/api`)
- [ ] Core safety chain — validator / approvals / hash binding (`app/core`)
- [ ] Services — sandbox executor / tiered RAG / audit (`app/services`)
- [ ] Pipeline — detection / attribution / invariants (`pipeline`)
- [ ] Evaluation — experiments / attack suite (`eval`)
- [ ] Frontend dashboard (`frontend`)
- [ ] Migrations / DB (`app/db`)
- [ ] Configs (`configs/*.yaml` — load-bearing, hash-keyed)
- [ ] Docs / CI

## Safety Impact Declaration

<!-- Required. The safety chain is the research core of this project. -->

- [ ] **No safety-chain interaction** — this PR touches none of the components below.
- [ ] **Interacts with the safety chain** — Safety Impact section below.

<!-- If you checked the second box, complete this section: -->

**Invariants affected and how they remain enforced:**

- [ ] C1–C5 validator — C1–C4 remain fully deterministic; per-check
      `deterministic` flag recorded
- [ ] Approval workflow — distinct-approver for control class; 24 h expiry
      escalates, never silently denies
- [ ] Plan hash binding — `steps_hash` immutable; executed ≡ validated ≡
      approved (SHA-256 triple binding)
- [ ] Sandbox-only execution — no real-IO path; actions labeled `SIMULATED`;
      lease recovery escalates rather than resuming half-applied plans
- [ ] Tiered RAG — hostile tier unreachable in production (INV-012);
      `TIER_DENIED` recorded on denial paths
- [ ] Naive-variant gate — `variant='naive'` terminal at `draft_only`
      (INV-010/R44)

**Explanation:**

<!-- 2–4 sentences: what changed, why the invariants still hold, and which
tests cover that. -->

## How Has This Been Tested?

<!-- Describe your verification. Mark the boxes for what you actually ran. -->

- [ ] `make test` (pytest) — all green
      Test count: <!-- e.g. 78 passed -->
- [ ] `make lint` (ruff) — clean
- [ ] `make typecheck` (mypy) — no new errors
- [ ] `cd frontend && npm run build` (tsc + vite) — clean
- [ ] New tests added:

  - Regression test for the fixed behaviour: <!-- test path -->
  - Coverage for new functionality: <!-- test path -->

- [ ] Alembic migration included and tested (if DB state changed)

## Config Changes

<!-- Configs are load-bearing: detector bounds, invariant bounds, and
experiment definitions are keyed by committed hashes. -->

- [ ] No config changes
- [ ] Config changes included (`configs/*.yaml`)

  Files: <!-- e.g. configs/invariants.yaml -->
  Intent documented: <!-- why the bounds/definitions changed; affected experiments -->

## Checklist

- [ ] I have read the [Contributing guide](CONTRIBUTING.md)
- [ ] My code follows the project style guidelines (ruff, line length 100)
- [ ] I have performed a self-review of my code
- [ ] I have commented safety-chain logic with the invariant it enforces
- [ ] Documentation updated (README / docs/ / MANUAL_SETUP.md where needed)
- [ ] [CHANGELOG.md](../CHANGELOG.md) updated under **[Unreleased]**
- [ ] No real OT/ICS connectivity introduced anywhere in this change
