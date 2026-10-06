# Red Team Operations Platform

A self-hosted web platform for a professional red team to **manage, document, and report** security vulnerabilities and assessment operations. It is an internal management tool for ~20 operators — not an offensive/attack tool.

**Intended stack (per spec):** Python (FastAPI) · PostgreSQL · MinIO (local S3) · Vue SPA · Tailwind CSS · Docker · Azure Communication Services (email).

## Repository layout

```
docs/
  specs/                        Canonical, current specifications
    SPEC.md                     Backend/system spec (entity model, lifecycles, dispatcher, API)
    FRONTEND_SPEC.md            Frontend spec (routes, pages, visual system, API contract)
    vulnerability_hub_escopo_priorizacao.md   Scope & prioritization notes (PT-BR)
  DECISIONS.md                  Resolved edge-case design decisions (D1–D8) + rationale
  DEPLOYMENT.md                 Deployment & networking plan + IT-request checklist
  archive/                      Superseded earlier spec versions (kept for history)

prototypes/
  operations_hub.html           Operations Hub (main post-login workspace) prototype
  vulnerability_creation.html   Create Vulnerability page prototype (latest iteration)
  archive/                      Earlier prototype iterations
```

## Which file is "the" spec?

- `docs/specs/SPEC.md` — latest system spec (was `SPEC 2.md`; adds the `source` field over the prior version).
- `docs/specs/FRONTEND_SPEC.md` — latest frontend spec (was `FRONTEND_SPEC (2).md`; most complete, includes the change log and Actions section).

Earlier numbered duplicates are preserved under the respective `archive/` folders and are not authoritative.

## Core concepts (from the spec)

- **Vulnerability** — a finding; standalone (`report_id = NULL`) or owned by a report.
- **Report** — a collection of vulnerabilities, dispatched as a unit.
- **Dispatch** — outbound delivery via the decoupled **Dispatcher** service (email today, ServiceNow-ready).
- **RVS** — the blue team's own tracking record ID, entered after dispatch to move a vuln to `acknowledged`.
- **Operator** — a platform user assigned to vulnerabilities/reports.
