# Red Team Operations Platform — System Specification

> **Current as of 2026-11-24.** This document describes the system as built. The reasoning behind
> each rule is in [DECISIONS.md](../DECISIONS.md) (D1–D18), referenced inline; the integration API
> is detailed in [API.md](../API.md), the screens in [FRONTEND_SPEC.md](FRONTEND_SPEC.md) and the
> dashboards' query language in [DASHBOARDS.md](DASHBOARDS.md). Keep this file in step with the
> code: a change to a rule here belongs in the same commit as the code that implements it.

## Overview

A self-hosted web platform for a red team (~20 operators) to manage, document and report security
vulnerabilities and assessment operations, and for the defense team to receive and track them. A
modular monolith.

**Stack:** Python 3.12 (FastAPI, SQLAlchemy 2, Alembic) · PostgreSQL 16 · Vue 3 (Vite, Pinia) ·
nginx · Docker Compose · ReportLab / python-docx / openpyxl for documents · SMTP for delivery ·
attachments on a local volume or any S3-compatible store.

---

## 0. Glossary

| Term | Definition |
|---|---|
| **RVS** | *Reporte de Vulnerabilidade de Segurança* — the defense team's own tracking record for a vulnerability. After a finding is sent, the defense team registers it in their system and records its RVS ID on the portal. |
| **Defense team** (blue team) | Receives sent vulnerabilities and reports and runs remediation. Has its own accounts and pages in the portal (§17). |
| **Send** (*Enviar*) | Delivering a vuln or report through the dispatcher (§12); moves it to `sent`. |
| **Dispatcher** | The single egress module (§12). SMTP today (or a stub that only logs); callers know nothing of the transport. |
| **Standalone vuln** | A vulnerability with `report_id = NULL`: managed and sent on its own. |
| **Report vuln** | A vulnerability inside a report (`report_id` set). While the report is a draft it is edited under the report's lock and is sent only with the report; afterwards it lives on its own. |
| **Operator** | A user assigned to a vulnerability or report. |
| **Batch** | Vulns grouped under one `BATCH-0001` id: created together by an integration-API run (§11), or put in it by hand while draft or ready (§4). |
| **Import** | A past vulnerability brought in through the integration API with its status, dates and number (§11). |

**Flow:** the red team writes a finding → completes it (`ready`, gets `VULN-xxxx`) → sends it,
alone or in a report (`sent`) → the defense team accepts it and records the RVS ID (`fixing`), or
assumes the risk (`risk_accepted`) → when the fix is done, a retest (`retesting`) → `fixed`.

---

## Table of Contents

- [§1 Entity Model](#1-entity-model)
- [§2 Lifecycles](#2-lifecycles)
- [§3 Write Locking](#3-write-locking)
- [§4 Field-Level Edit Permissions](#4-field-level-edit-permissions)
- [§5 Vulnerability Fields](#5-vulnerability-fields)
- [§6 Report Fields](#6-report-fields)
- [§7 Report Editor](#7-report-editor)
- [§8 Operations Hub](#8-operations-hub)
- [§9 Sending a Report](#9-sending-a-report)
- [§10 Users, Access and Audit](#10-users-access-and-audit)
- [§11 Integration API](#11-integration-api)
- [§12 Dispatcher and Documents](#12-dispatcher-and-documents)
- [§13 Infrastructure & Deployment](#13-infrastructure--deployment)
- [§14 Not Yet / Post-MVP](#14-not-yet--post-mvp)
- [§15 Data Model](#15-data-model)
- [§16 Technical Decisions](#16-technical-decisions)
- [§17 Defense Team](#17-defense-team)
- [§18 Dashboards](#18-dashboards)
- [§19 Report Templates](#19-report-templates)

---

## 1. Entity Model

### Two Vulnerability Types

| Type | `report_id` | Lock | Lifecycle |
|---|---|---|---|
| **Standalone** | `NULL` | None; optimistic concurrency (D5) | Full lifecycle (§2.1) |
| **Report vuln** | Set (exclusive) | The report's lock (§3) | `draft` inside the report; on its own once the report is sent (§2.3) |

A vulnerability belongs to **at most one report**. While a report is a draft, standalone vulns
that were not sent yet (`draft`, `ready`) can be **linked** into it — a `ready` one goes back to
`draft` and keeps its number — and a report vuln can be **taken out**, becoming a standalone draft
again. A sent vuln never changes report.

### One Table Per Entity

No separate draft tables: one `vulnerabilities` table and one `reports` table; the `status`
column carries the lifecycle. Deletes are soft (`deleted_at`).

---

## 2. Lifecycles

Statuses and their names on screen (D14, D17):

| Vulnerability | Code | Moves on by |
|---|---|---|
| Rascunho | `draft` | *Concluir* (`POST /vulnerabilities/{id}/complete`): needs identifier, description and finding detail; assigns `VULN-xxxx` |
| Pronta | `ready` | *Enviar* (`POST /vulnerabilities/{id}/send`) |
| Enviada | `sent` | the defense team accepts it and records the RVS ID → `fixing`; or assumes the risk → `risk_accepted` |
| Em correção | `fixing` | *Solicitar reteste* → `retesting`; or the defense team's *Marcar como corrigida* → `fixed` |
| Em reteste | `retesting` | *Aprovar reteste* → `fixed`; *Reprovar reteste* → `fixing` |
| Corrigida | `fixed` | end |
| Risco assumido | `risk_accepted` | end (the defense team may undo it → `sent`) |

### 2.1 Standalone Vulnerability

```
draft ──[Concluir]──────────► ready        (VULN-xxxx assigned, ready_at)
ready ──[Enviar]────────────► sent         (delivered through the dispatcher, sent_at)
sent  ──[Aceitar]───────────► sent         (accepted_at / accepted_by; a field, not a status)
sent  ──[RVS ID]────────────► fixing       (rvs_id, fixing_at; implies acceptance if none yet)
sent  ──[Assumir risco]─────► risk_accepted (risk_accepted_at / _by, risk_reason ≥ 5 chars)
risk_accepted ──[Desfazer]──► sent
fixing ──[Solicitar reteste]► retesting    (retesting_at)
fixing ──[Marcar corrigida]─► fixed        (defense team; retest skipped)
retesting ──[Reprovar]──────► fixing       (retesting_at cleared)
retesting ──[Aprovar]───────► fixed        (fixed_at)
```

A standalone send renders that vuln's package and delivers it; a delivery failure leaves it
`ready`.

### 2.2 Report

```
draft ──[Enviar]──► sent
```

Two statuses only. A send in progress or failed is the `reports.sending` flag, not a status (D14):
from phase 1 until delivery the report is frozen; a failed delivery shows *Rascunho* + *Falha no
envio* + *Tentar novamente*, and a retry never re-issues numbers (§9). Report **progress** is
computed, never stored: `closed_count` (fixed or risk accepted) of `vulnerability_count`;
*Concluído* when all are closed.

### 2.3 Report Vulnerability

```
draft   (inside the report; edited under the report lock)
  │
  └── report sent (one transaction with the report)
           ▼
         sent ──► fixing ⇄ retesting ──► fixed
           └────► risk_accepted
```

When the report is sent, all its vulns move to `sent` together and are delivered in one package
(§9). From then on each one follows §2.1 on its own; the report keeps listing them and shows their
progress.

### 2.4 Admin Correction (D6)

An admin may move a vuln back to an earlier status (*Ajustar status*, `POST
/vulnerabilities/{id}/correction`, reason ≥ 5 chars). The dates of the undone stages are cleared;
going back before `fixing` also removes the RVS ID (the vuln waits for one again); going back
before `sent` clears the acceptance; undoing a risk acceptance clears its reason. Always audited as
`correction` with the reason.

---

## 3. Write Locking

**This section is the canonical lock definition.**

- The **report** is the only entity with a write lock. Holding it grants write access to the
  report and to every vulnerability inside it.
- The lock frees itself after **10 minutes without writes** (checked lazily on the next acquire; no
  background job). The editor keeps it alive with a heartbeat while open.
- **Force-release (D4):** an admin may release a lock held by someone else; the UI shows the holder
  and since when; audited as `lock_override`.
- While a report is `sending` (§9) nothing in it can be edited.
- Once a report is `sent`, the lock is not used: only its internal notes stay editable.
- **Standalone vulnerabilities** have no lock. Every write carries the `version` last read; a stale
  one is refused with `409` and the client reloads (D5).

---

## 4. Field-Level Edit Permissions

### Vulnerabilities

| Status | Editable |
|---|---|
| `draft`, `ready` | All content fields (identifier, CWE, creation date, CVSS, description, finding detail, mitigation, references, source, internal notes), the batch, operators and *Compartilhado com*. The identifier may be blank in `draft`; it is required to complete (D3) |
| `sent` and after | Internal notes, operators and *Compartilhado com* only |

- A report vuln is edited only by the holder of the report's lock, and only while the report is a
  draft and not sending.
- **What goes into the documents** (the *No documento* toggle on description, finding detail,
  mitigation and references; `export_hidden`) is not content: any writer may change it in any
  status, saved at once, without the lock or a new version.
- Attachments follow the content lock (draft / ready).
- The **creation date** may be set by hand (a finding recorded later): never in the future, never
  after `ready_at`.
- The **batch** may be set, changed or cleared (`null`) in `draft` and `ready`, on the form or on
  create. Only an existing batch is accepted (`422` otherwise; new batches come from
  `POST /v1/batches`), in any case. It is fixed once the vuln is sent; the audit entry records
  `{from, to}`.

### Reports

| Status | Editable |
|---|---|
| `draft` (not sending) | All fields, under the lock |
| `sent` | Internal notes only |

The report's *No documento* toggles (executive summary, introduction, report data, and each extra
section's `exported`) follow the same rule as the vuln's: changeable at any time.

---

## 5. Vulnerability Fields

| Field | Type | Notes |
|---|---|---|
| **Identifier** | Text | CVE or free-text name; what lists and titles show (D15) |
| **Internal ID** | `VULN-xxxx` | Assigned on *Concluir* (standalone) or when its report is sent; never changes. An import may bring its original number (§11) |
| **RVS ID** | Text, nullable | The defense team's id; recorded after sending; unique across live vulns (case-insensitive) |
| **CWE** | Text | Normalised to `CWE-79` |
| **Description** | Markdown | |
| **Finding Detail** | Markdown | Technical write-up |
| **Mitigation / Solution** | Markdown | May stay blank |
| **References** | List of http(s) URLs | Up to 50 |
| **CVSS v3.1 Score** | 0.0–10.0 | Typed, or from the built-in calculator |
| **CVSS v3.1 Vector** | Text | Typed, or from the calculator |
| **Source** | Text, nullable | Where it came from (`nuclei`, `burp`, …); several values on the form |
| **Operators** | Users | Who works on it; the creator is the default |
| **Shared with** (*Compartilhado com*) | Users | Read access for restricted roles (D10) |
| **Creation date** | Timestamp | Now by default; may be set by hand on the form or through the API (§4) |
| **Batch** | `BATCH-xxxx`, nullable | The integration-API run it was created in (§11), or set by hand in draft / ready (§4) |
| **Imported at** | Timestamp, nullable | Set when brought in with its history (§11); its dates are another system's |
| **Acceptance** | Timestamp + user | When and by whom the defense team accepted it (D17) |
| **Risk acceptance** | Timestamp + user + reason | When the defense team assumed the risk, and why (D17) |
| **Extra Metadata** | JSON | Free data from the tool that created it (§11) |
| **Internal Notes** | Markdown | Red team only; never exported, never sent, not in the integration API |
| **No documento** | List | Sections left out of its documents (`export_hidden`) |
| **Attachments** | Files | §5.1 |
| **Status** + dates | Enum + timestamps | §2; `ready_at`, `sent_at`, `fixing_at`, `retesting_at`, `fixed_at` |

### 5.1 Attachments

- Stored through the storage interface (local volume by default, or S3 — D9). Never exposed
  directly: every read is proxied by the API, so access rules and read auditing apply.
- Validated by extension allowlist and file content (magic bytes); the client's Content-Type is
  ignored; SVG is refused; **50 MB** per file.
- **Images** pasted or dropped into a Markdown field are stored as attachments and referenced
  inline; they render in the editor and the documents.
- **Other files** are downloadable, and go with the vuln (or its report) when it is sent.
- Upload: drag-and-drop, paste, file picker.

---

## 6. Report Fields

| Field | Type | Notes |
|---|---|---|
| **Name** | Text | Its identifier on screen (D15) |
| **Internal ID** | `OP-xxxx` | Assigned when the report is sent (a retry keeps it); drafts have none |
| **Client Name** | Text | On the cover |
| **Operators** / **Shared with** | Users | As on vulns |
| **Start / End Date** | Dates | Execution window |
| **Status** | `draft` / `sent` | Plus the `sending` flag and the last `send_error` (§9) |
| **Content** | §7 | Executive summary, introduction, report data, extra sections, vulns |
| **Evidence** | Files | The report's own attachments; images can be embedded in its sections |
| **Template** | Reference | The template it started from, if any (§19) |
| **Internal Notes** | Markdown | Editable after sending; never exported |
| **Lock** | §3 | One lock for the report and its vulns |

---

## 7. Report Editor

### Structure

Documents render in this fixed order:

| # | Section | Storage | Editable | Notes |
|---|---|---|---|---|
| 1 | **Cover** | From the report fields | No | Name, client, dates, operators |
| 2 | **Executive Summary** | `reports.executive_summary_md` | Yes | Starts with an outline, or the template's text |
| 3 | **Table of contents** | Generated | No | |
| 4 | **Introduction** | `reports.introduction_md` | Yes | |
| 5 | **Report Data** | Columns on `reports` | Yes | Test type, demand origin, environment, scope, test model (free text) |
| 6 | **Extra sections** | `report_sections` | Yes | Any number, in the author's order |
| 7 | **Vulnerabilities** | `vulnerabilities` with the report's id | Through the vuln editor | CVSS descending |

Each of 2, 4, 5 and every extra section has a *No documento* toggle (§4).

### Editing

- Vulnerability content is edited in the vulnerability editor, under the report's lock.
- The report editor handles the metadata, the sections, linking/unlinking and creating vulns, and
  the evidence.
- *Salvar como Template* saves the section texts as a template (§19).

### Export

| Document | Contents | Formats |
|---|---|---|
| Vulnerability | One vuln: all fields shown in documents | PDF, Word |
| Report | Sections in order · its vulns (CVSS desc) · evidence list | PDF, Word, Excel (the vulns) |
| Batch (Hub) | Selected vulns or reports | ZIP of PDFs; Excel |

Internal notes and sections switched off with *No documento* never appear in documents.

---

## 8. Operations Hub

The Hub (*Operações*) lists vulnerabilities and reports in two tabs, filtered to what the user may
read (§10.2).

- Vulnerabilities inside a draft report are listed too, each row naming its report.
- One-line **filter language** (`frontend/src/filterQuery.js`): free text on the identifier;
  `status:a,b`, `cvss:x` (≥), `report:` (`none`), `operator:`, `batch:` (`none`), `source:`, and
  date keys `created`, `updated`, `sent`, `accepted`, `fixing`, `retesting`, `fixed`, `risk` with
  relative (`7d`, `3m`, `1y`) or calendar periods (`d1.d2.d3`, months, years, semesters, quarters);
  `-key:value` negates; quoted values hold spaces; terms are ANDed. `?q=` opens the Hub with a
  filter.
- A details drawer with the timeline; row and batch actions (export, send, delete), skipping and
  reporting the items an action does not apply to; pagination.

---

## 9. Sending a Report

*Enviar* on a draft report (`POST /reports/{id}/send`), by a writer holding the lock. In two phases
so a failure never reads as sent (D2, D14, D16):

**Before freezing:** every vuln must have identifier, description and finding detail (D3); the
package is built first, so content that cannot be rendered is refused and the report stays an
editable draft.

**Phase 1 — one DB transaction:** `sending` set (the report is frozen), `OP-xxxx` and the vulns'
`VULN-xxxx` assigned (kept from a previous try), commit.

**Phase 2 — deliver:** the dispatcher sends the report PDF, the Excel of its vulns and every
non-image file of the report and its vulns.
- **Success:** report → `sent` (`sent_at`), its vulns → `sent` (`sent_at`), `sending` cleared.
- **Failure:** the report stays a frozen draft with `send_error`; *Tentar novamente* retries without
  new numbers.

---

## 10. Users, Access and Audit

### 10.1 Authentication

- Username + password (bcrypt). Users have a **full name** (documents) and a **display name** (on
  screen), apart from the login.
- **Sessions live on the server** (`auth_sessions`, D16): at most 1 hour from login, ended sooner
  by 15 minutes without activity (D12). Access tokens last 5 minutes; a refresh token works once.
  Signing out or changing the password ends sessions.
- **Login limits (D16):** 5 failures per account and 30 per IP in 15 minutes answer `429`; failures
  are audited (`login_failed`).
- **First run:** if no user exists, an `admin` is created with `FIRST_ADMIN_PASSWORD` or a random
  password printed once to the API log. New and reset users must change their password at first
  login.
- **API keys** (§11): created by admins, carry scopes and an optional expiry; 32+ random bytes,
  stored as a SHA-256 hash (D7); shown once.
- The auth layer is pluggable so SSO (Azure Entra ID) can be added later.

### 10.2 Roles (D10, D17, D18)

| Role | Sees | Changes |
|---|---|---|
| `admin` | everything | everything; users, API keys, template approval, corrections, lock release |
| `write_all` | everything | every vuln and report |
| `read_all` | everything | nothing |
| `auditor` | everything | nothing; plus the audit log |
| `write_restricted` | what it created, operates or was shared | creates; edits what it created or operates; deletes what it created |
| `read_restricted` | what it created, operates or was shared | nothing |
| `defense` | sent vulns only, without red-team-only fields (§17) | accepts, records RVS IDs, assumes risk, ends the fix |
| `dashboard` | dashboards (aggregates of every finding) and TV links (§18) | dashboards |

- Enforcement lives in `backend/app/access.py`; lists filter in SQL. A record the user may not read
  answers **404**; a readable one they may not change, **403**. The UI mirrors the rules
  (`frontend/src/access.js`) but the server never trusts it.
- A report's vulns follow the report's access. The creator always keeps access.
- `defense` and `dashboard` accounts are refused by every other route (`get_current_user`).

### 10.3 Audit Log

Captured for: login, failed login, logout · create, read, update, delete · status change, send,
accept · export · API key create/revoke and every key's writes, exports and downloads · permission
change · lock override · correction. Imports are a `create` with `"import": true`.

- **Reads are logged on purpose (D8):** who read what, when. A list logs the listing, not each row.
- Each entry: actor (user **or** API key; only a failed login may have none) · action · entity type
  and id · detail · IP · time. Append-only.
- The *Logs de Auditoria* page (auditor, admin) uses the Hub's filter bar, filtered on the server
  (`POST /audit-logs/search`).

---

## 11. Integration API

Other systems use `/api/v1` with **scoped API keys** (D13); full reference in
[API.md](../API.md).

| Scope | Allows |
|---|---|
| `vulns:read` | read vulnerabilities and their evidence |
| `vulns:write` | create vulnerabilities and batches |
| `vulns:import` | with `vulns:write`: create past vulnerabilities with their history |
| `rvs:write` | the RVS queue and recording RVS IDs |
| `reports:read` | read reports and their evidence |
| `exports` | PDF / Word / Excel downloads |

- Keys work only on `/v1/*`, read every record their scope allows (per-user access is for people),
  and have their own response schemas: no internal notes, viewers or locks. Lists are
  keyset-paginated by `updated_at` with `updated_since` for syncing. Records are addressed by UUID
  or number.
- **Create** (`POST /v1/vulnerabilities`): content fields, operators (usernames), `status` `draft`
  or `ready` (which needs the required fields and assigns the number), `metadata`; unknown fields
  are kept in the metadata. Records belong to the admin who issued the key.
- **Batches:** `POST /v1/batches` returns a portal-made `BATCH-0001`; the tool sends it as
  `batch_id` with each vuln of the run (an unknown id is a `422`). Set on creation; the portal can change it while draft / ready (§4); the Hub
  filters `batch:`, the API `?batch=`.
- **Imports** (`vulns:import`): the same endpoint and body may carry any status, each step's date,
  the original `VULN-` number (the counter moves past it), the RVS ID, who accepted and the risk
  reason. Each status needs the dates leading to it and none after, in lifecycle order, none in
  the future; `updated_at` defaults to the last of them. Nothing is delivered and no history is
  invented: one audit `create` with `"import": true`, and the record keeps `imported_at`. Without
  the scope these fields are a `403`. Imports are standalone vulns.
- **Not through the API:** sending (it emails people; a human decision), deletes, admin actions.

---

## 12. Dispatcher and Documents

The dispatcher (`backend/app/dispatcher.py`) is the single egress point: callers hand it a payload
(subject, body, files) and know nothing of the transport.

| `DISPATCH_TRANSPORT` | Behaviour |
|---|---|
| `stub` (default) | Logs what would be sent; nothing leaves |
| `smtp` | Email to `DISPATCH_TO` through `SMTP_*`, with the PDF, Excel and non-image files attached |

Azure Communication Services and ServiceNow are possible later transports; adding one does not
touch the callers.

**Rendering** (`backend/app/render.py`) is separate from the transport and produces bytes:

| Format | Scope |
|---|---|
| PDF | One vuln, or a full report |
| Word | One vuln, or a full report |
| Excel | A list of vulns, all fields as columns |

---

## 13. Infrastructure & Deployment

| Concern | Solution |
|---|---|
| Deployment | Docker Compose, self-hosted; `docs/INSTALL.md`, `docs/RUNBOOK.md` |
| Proxy | nginx: the only published port; `/api/*` → API, the rest → frontend; TLS and a strict CSP in production |
| Database | PostgreSQL 16; migrations with Alembic (`backend/migrations`) |
| Files | Local volume (`STORAGE_BACKEND=local`, default) or S3-compatible (`s3`) (D9) |
| Backend | FastAPI; several workers, non-root, in production |
| Frontend | Vue 3 SPA (Vite); built and served by nginx in production |
| Delivery | SMTP (§12) |
| Backups | `scripts/backup.sh` / `restore.sh`: database and attachments, optionally encrypted |
| Scale | ~20 concurrent operators — modular monolith |

The API refuses to start in production with the development `JWT_SECRET`.

---

## 14. Not Yet / Post-MVP

- SSO (Azure Entra ID).
- Azure Communication Services or ServiceNow delivery; status changes driven by ServiceNow.
- Permission constraints still to decide (who may delete, send or reassign what): today, any
  writer of the record (`docs/BACKLOG.md`).
- Integration API: de-duplication (`external_id`), updates and lifecycle actions, evidence upload,
  webhooks.
- Imports of reports, and imports through a file upload.
- Dashboards: SLA deadlines, frozen report blocks, period comparisons, backlog over time (D18).
- Templates: duplicate, create from scratch (D11).

---

## 15. Data Model

**Stack:** PostgreSQL · SQLAlchemy 2 · Alembic. Files live in the storage backend; the database
keeps their keys and metadata. Timestamps are stored in UTC without a zone.

### 15.1 Enums

| Enum | Values |
|---|---|
| `user_role` | `admin` · `write_all` · `read_all` · `auditor` · `write_restricted` · `read_restricted` · `defense` · `dashboard` |
| `vuln_status` | `draft` · `ready` · `sent` · `fixing` · `retesting` · `fixed` · `risk_accepted` |
| `report_status` | `draft` · `sent` |
| `audit_action` | `login` · `login_failed` · `logout` · `create` · `read` · `update` · `delete` · `status_change` · `export` · `send` · `api_key_create` · `api_key_revoke` · `permission_change` · `lock_override` · `correction` · `accept` |
| `share_status` (templates) | `private` · `pending` · `shared` · `unshared` |

Old status names in past audit entries are kept as they were written (D14).

### 15.2 Sequences

| Sequence | Format | Assigned when |
|---|---|---|
| `report_seq` | `OP-%04d` | The report is sent (phase 1; a retry keeps it) |
| `vuln_seq` | `VULN-%04d` | Standalone: *Concluir*. Report vuln: the report is sent (phase 1), unless it already had one. An import with its own number moves the counter past it |
| `vuln_batch_seq` | `BATCH-%04d` | `POST /v1/batches` |

### 15.3 Table: `users`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `username` | text | UNIQUE NOT NULL | the login |
| `full_name` | text | NULL | used in documents |
| `display_name` | text | NULL | shown on screen (else full name, else login) |
| `password_hash` | text | NULL | bcrypt; NULL reserved for SSO-only accounts |
| `role` | user_role | NOT NULL | |
| `must_change_password` | bool | NOT NULL | first-run admin, new and reset users |
| `is_active` | bool | NOT NULL | deactivate instead of delete |
| `created_at`, `updated_at` | timestamp | NOT NULL | |

### 15.3.1 Table: `auth_sessions`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | carried in the tokens |
| `user_id` | uuid | FK users, indexed | |
| `refresh_jti` / `previous_jti` | text | | the current refresh token, and the previous one during a short race window |
| `rotated_at` | timestamp | NULL | |
| `expires_at` | timestamp | NOT NULL | 1 h after login |
| `revoked_at` | timestamp | NULL | sign-out, password change, token reuse |

### 15.4 Table: `api_keys`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `label` | text | NOT NULL | |
| `key_prefix` | text | NOT NULL | first 8 characters, shown on screen |
| `key_hash` | text | UNIQUE NOT NULL | SHA-256 (D7) |
| `scopes` | text[] | NOT NULL | §11 |
| `created_by` | uuid | FK users NOT NULL | the admin who issued it; owns what it creates |
| `expires_at` | timestamp | NULL | |
| `revoked_at` | timestamp | NULL | |
| `last_used_at` | timestamp | NULL | |
| `created_at` | timestamp | NOT NULL | |

### 15.5 Table: `reports`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `internal_id` | text | UNIQUE NULL | `OP-0007`; on send |
| `name` | text | NOT NULL | |
| `client_name` | text | NULL | |
| `start_date`, `end_date` | date | NULL | |
| `status` | report_status | NOT NULL default `draft` | |
| `sending` | bool | NOT NULL default false | frozen from phase 1 until delivery (§9) |
| `send_error` | text | NULL | last delivery failure |
| `executive_summary_md`, `introduction_md` | text | NULL | |
| `test_type`, `demand_origin`, `environment`, `scope`, `test_model` | text | NULL | report data |
| `internal_notes` | text | NULL | editable after sending; never exported |
| `export_hidden` | jsonb | NOT NULL | sections left out of its documents |
| `sent_at` | timestamp | NULL | |
| `lock_user_id` | uuid | FK users NULL | lock holder (§3) |
| `lock_acquired_at`, `lock_last_activity_at` | timestamp | NULL | idle release at 10 min |
| `template_id` | uuid | FK report_templates ON DELETE SET NULL | §19 |
| `created_by` | uuid | FK users NOT NULL | |
| `created_at`, `updated_at` | timestamp | NOT NULL | |
| `deleted_at` | timestamp | NULL | soft delete; only drafts can be deleted, with their vulns (D1) |

### 15.6 Table: `report_sections`

Extra sections only; the typed ones are columns on `reports`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `report_id` | uuid | FK reports ON DELETE CASCADE NOT NULL | |
| `position` | int | NOT NULL | 1-based; UNIQUE with `report_id` |
| `title` | text | NOT NULL | |
| `content_markdown` | text | NULL | |
| `exported` | bool | NOT NULL default true | *No documento* |
| `created_at`, `updated_at` | timestamp | NOT NULL | |

### 15.7 Tables: `report_operators`, `report_viewers`

`(report_id, user_id)`, both FKs, composite PK; the report's operators and *Compartilhado com*.

### 15.8 Table: `vulnerabilities`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `internal_id` | text | UNIQUE NULL | `VULN-0042` |
| `report_id` | uuid | FK reports ON DELETE CASCADE NULL | NULL = standalone; cascade only reaches draft reports' vulns (D1) |
| `status` | vuln_status | NOT NULL default `draft` | |
| `version` | int | NOT NULL default 1 | optimistic concurrency (D5) |
| `rvs_id` | text | NULL; UNIQUE on `lower(btrim(rvs_id))` | |
| `identifier`, `cwe` | text | NULL | |
| `description`, `finding_detail`, `mitigation` | text | NULL | Markdown |
| `references` | jsonb | NOT NULL default `[]` | URLs |
| `cvss_score` | numeric(3,1) | NULL | |
| `cvss_vector`, `source` | text | NULL | |
| `internal_notes` | text | NULL | never exported or sent |
| `export_hidden` | jsonb | NOT NULL default `[]` | sections left out of its documents |
| `extra_metadata` | jsonb | NOT NULL default `{}` | from the integration API |
| `ready_at`, `sent_at`, `fixing_at`, `retesting_at`, `fixed_at` | timestamp | NULL | lifecycle (§2) |
| `accepted_at` / `accepted_by` | timestamp / FK users | NULL | D17 |
| `risk_accepted_at` / `risk_accepted_by` / `risk_reason` | timestamp / FK users / text | NULL | D17 |
| `batch_id` | text | FK vuln_batches(internal_id) NULL, indexed | §11 |
| `imported_at` | timestamp | NULL | §11 |
| `created_by` | uuid | FK users NOT NULL | |
| `created_at` | timestamp | NOT NULL | default now; may be set by hand or by an import |
| `updated_at` | timestamp | NOT NULL | |
| `deleted_at` | timestamp | NULL | soft delete |

### 15.8.1 Table: `vuln_batches`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `internal_id` | text | UNIQUE NOT NULL | `BATCH-0001`; what `vulnerabilities.batch_id` holds |
| `api_key_id` | uuid | FK api_keys NULL | the key that asked for it |
| `created_at` | timestamp | NOT NULL | |

### 15.9 Tables: `vulnerability_operators`, `vulnerability_viewers`

`(vulnerability_id, user_id)`, FK vulnerabilities ON DELETE CASCADE and FK users, composite PK.

### 15.10 Table: `attachments`

Vuln files and report evidence; exactly one owner (CHECK).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `vulnerability_id` | uuid | FK vulnerabilities ON DELETE CASCADE NULL | |
| `report_id` | uuid | FK reports ON DELETE CASCADE NULL | |
| `s3_key` | text | NOT NULL | storage key (either backend) |
| `original_filename` | text | NOT NULL | |
| `display_name` | text | NULL | |
| `mime_type` | text | NOT NULL | detected from the content |
| `size_bytes` | bigint | NOT NULL | ≤ 50 MB |
| `is_image` | bool | NOT NULL | inline vs. sent as a file |
| `uploaded_by` | uuid | FK users NOT NULL | |
| `created_at` | timestamp | NOT NULL | |

### 15.11 Table: `audit_logs`

Append-only.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | bigserial | PK | |
| `user_id` | uuid | FK users NULL | human actor |
| `api_key_id` | uuid | FK api_keys NULL | machine actor |
| `action` | audit_action | NOT NULL | |
| `entity_type` | text | NULL | `vulnerability`, `report`, `user`, `api_key`, `report_template`, `dashboard`, `vuln_batch`, … |
| `entity_id` | uuid | NULL | |
| `detail` | jsonb | NULL | e.g. `{"from": "sent", "to": "fixing", "rvs_id": "RVS-2026-0001"}` |
| `ip_address` | inet | NULL | |
| `created_at` | timestamp | NOT NULL default now() | |

CHECK `ck_audit_actor`: exactly one actor (`user_id` or `api_key_id`), except a `login_failed`
entry, which may have no user and never a key (D16).

### 15.12 Other tables

- `report_templates` (§19): `name`, `owner_id`, `share_status`, `share_requested_at`,
  `share_decided_at` / `_by`, `executive_summary_md`, `introduction_md`, `sections` (jsonb),
  `version`.
- `dashboards` (§18): `name`, `description`, `variables` and `screens` (jsonb), `refresh_seconds`,
  `rotate_seconds`, `created_by`, `updated_by`.
- `dashboard_links`: TV links — `dashboard_id`, `label`, `token_hash` (UNIQUE, SHA-256),
  `created_by`, `revoked_at`, `last_used_at`.

### 15.13 Indexes

| Table | Index | Rationale |
|---|---|---|
| `vulnerabilities` | `(report_id)` | a report's vulns |
| `vulnerabilities` | `(status)`, `(status, sent_at)` | lists; the RVS queue |
| `vulnerabilities` | `(cvss_score DESC)` | document ordering |
| `vulnerabilities` | `(deleted_at)` | soft-delete filter |
| `vulnerabilities` | `(batch_id)` | a batch's vulns |
| `vulnerabilities` | UNIQUE `lower(btrim(rvs_id))` | one RVS ID per vuln |
| `reports` | `(status)`, `(lock_last_activity_at)` | lists; idle locks |
| `audit_logs` | `(entity_type, entity_id)`, `(created_at)`, `(action, created_at)` | history; time ranges; login limits |
| `attachments` | `(vulnerability_id)`, `(report_id)` | a record's files |
| `auth_sessions` | `(user_id)` | a user's sessions |
| `report_templates` | `(owner_id)`, `(share_status)` | lists; the approval queue |
| `dashboard_links` | `(dashboard_id)` | a dashboard's links |

### 15.14 Entity Relationships

```
users ──── creates / operates / is shared ──► vulnerabilities ──► attachments
  │                                              │   │
  │                                   report_id ─┘   └─ batch_id ──► vuln_batches ──► api_keys
  ├──── creates / operates / is shared ──► reports ──► report_sections
  │                                          │    └──► attachments (evidence)
  │                                          └── template_id ──► report_templates
  ├── auth_sessions
  ├── api_keys
  └── dashboards ──► dashboard_links

audit_logs ◄── (user_id or api_key_id) + entity reference
```

---

## 16. Technical Decisions

- **PDF: ReportLab** (`render.py`), with a small Markdown-to-flowables converter written for the
  portal (headings, lists, quotes, code blocks, inline images from attachments). No system libraries or
  browser binaries in the image.
- **Word: python-docx**; **Excel: openpyxl**.
- **Markdown in the browser:** the portal's own editor (preview, line gutter, image paste/drop) and
  a safe renderer (no raw HTML).
- **CVSS v3.1:** typed, or computed by the built-in calculator from the eight base metrics, as in
  FIRST's calculator.
- **Storage:** an interface with local and S3 backends (D9).
- **Charts:** a one-line query language computed in the API, aggregates only (D18).

---

## 17. Defense Team

Role `defense` (D17), with its own API (`/defense/*`) and pages:

- Sees only sent vulnerabilities (`sent`, `fixing`, `retesting`, `fixed`, `risk_accepted`) and only
  what the red team sends: no internal notes, operators, sharing or creator, and of the report only
  its name. Report files are not shown, only the vuln's own.
- Pages per section: *Novas*, *Aguardando RVS*, *Em andamento*, *Corrigidas*, *Risco assumido*,
  each with the Hub's filter bar (status, cvss, id, report keys), pagination and the batch actions
  that section allows.
- Actions: **accept** a sent vuln; **record the RVS ID** (→ `fixing`); **assume the risk** with a
  reason (→ `risk_accepted`), and undo it; on a vuln being fixed, **request a retest** or **mark it
  fixed** without one. The retest's outcome stays with the red team.
- Only the defense team (or a defense tool through an `rvs:write` key) records RVS IDs.
- A defense account cannot be an operator or be shared with.

---

## 18. Dashboards

Role `dashboard` and admins (D18; language in [DASHBOARDS.md](DASHBOARDS.md)):

- A dashboard is up to 10 screens of charts (24 in all), each chart one line:
  `<measure> [by …] [over …] [where <Hub filter>] [top N] [as …] [title "…"]`, computed in the API.
  Results are counts and durations only — no identifier, description or host leaves a chart.
- `$name = value` variables, replaced before parsing; viewers may change them for their own view.
- A chart that cannot run is not saved; each query previews as it is typed.
- `refresh_seconds` (30 s – 1 h) and `rotate_seconds` (5 s – 10 min).
- **TV links:** read-only, no sign-in, token shown once and kept hashed, revocable, audited; only
  status, severity and source groupings; computed with the creator's access, which stops when that
  account is deactivated or loses the role.
- No user-written code runs on the server.

---

## 19. Report Templates

D11. A template is the text of a report's sections (executive summary, introduction, extra
sections). Anyone who can create reports may save one (*Salvar como Template*) and start a report
from one; the report gets a **copy** and remembers its source (`template_id`).

| State | Who uses it | Owner may | Admin may |
|---|---|---|---|
| `private` | its owner | edit, delete, request sharing | edit, delete |
| `pending` | its owner (frozen) | withdraw | approve / reject |
| `shared` | everyone | — | edit, delete, unshare |
| `unshared` | nobody | — | delete, reshare |

Editing carries a `version` (409 when stale); every sharing step is audited. Readers and auditors
have no access to templates.
