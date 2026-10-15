# Security Policy

## Project Safety Boundary (read this first)

AEGIS-OT is a **research instrument, not a production product**.

- It **never** connects to, reads from, or controls real SCADA/PLC/plant
  infrastructure. The pipeline's terminal executor is a pure-Python **sandbox
  simulator**; every simulated action is labeled `SIMULATED`.
- Deploy it only in isolated research/lab environments. Never point it at
  operational technology networks.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

1. Use GitHub's **Private vulnerability reporting**
   ([Security → Report a vulnerability](https://github.com/abhinav-phi/aegis-ot/security/advisories/new)),
   or
2. Email the maintainer directly: **abhinav-phi@users.noreply.github.com**
   (PGP-encrypted mail preferred if you have a key).

Please include:

- A description of the issue and its suspected impact.
- Steps to reproduce (PoC script, request trace, or config).
- Affected component (`app/api`, `app/core`, `app/services`, `pipeline`, `eval`, `frontend`).
- Any logs or evidence, with secrets/keys redacted.

### What to expect

| Stage                    | Target                        |
| ------------------------ | ----------------------------- |
| Acknowledgement          | within 72 hours               |
| Triage & severity rating | within 7 days                 |
| Fix or mitigation plan   | within 30 days (critical: 7)  |
| Coordinated disclosure   | mutually agreed on disclosure date |

We follow coordinated disclosure: we ask that you do not publish details until
a fix is released and a disclosure date is agreed.

## Scope

### In scope

- Authentication / authorization flaws in the FastAPI backend (`app/api`, `app/core`).
- Bypasses of the C1–C5 validator chain, approval workflow, plan-hash triple
  binding, or sandbox-only execution guarantees.
- RAG tier-escape (hostile-tier content reachable from the production retriever).
- Audit-trail integrity (append-only violations, missing audit entries on
  security mutations).
- Secrets handling, dependency vulnerabilities, Docker/Compose misconfigurations.

### Out of scope

- Attacks requiring physical access to a researcher's machine.
- Social engineering.
- Denial-of-service against the sandbox/local environment (resource exhaustion
  in a local dev deployment).
- Findings that depend on deliberately disabling documented safety controls
  (e.g., editing validator rules to allow everything) — these are research
  arms, not vulnerabilities.

## Security Controls Reference

The safety chain is the research core; its invariants are documented in
[docs/8. Rules.md](docs/8.%20Rules.md) and implemented under `app/core/`
(validator, approvals, hash binding) and `app/services/` (sandbox executor,
tiered retriever). Changes to these components are expected to preserve:

- **INV-010/R44** — naive-variant plans terminate at `draft_only`.
- **INV-012** — hostile-tier collections are unreachable in production RAG.
- The SHA-256 triple binding between executed, validated, and approved content.
- Append-only audit logging in the same transaction as every security mutation.
