# Red Team Operations Platform — MVP Specification

## Overview

A self-hosted web platform for red team operators to manage, document, and report security vulnerabilities and assessment operations. Targets ~20 concurrent operators, deployed as a modular monolith.

**Stack:** Python (FastAPI) · PostgreSQL · MinIO (local S3) · Vue (SPA) · Tailwind CSS · Docker · Azure Communication Services (email)

---

## 0. Glossary

| Term | Definition |
|---|---|
| **RVS** | *Reporte de Vulnerabilidade de Segurança* — the blue team's own tracking record for a vulnerability. After we dispatch a finding, the blue team creates an RVS in their system and replies with an RVS ID, which we store on the vulnerability. |
| **Blue team** | The defensive team that receives our dispatched vulnerabilities and reports, and performs remediation. |
| **Dispatch** | The act of sending a vuln or report outbound via the dispatcher service, transitioning its status to `dispatched`. The current transport is email; it is designed to be swapped. |
| **Dispatcher** | The single decoupled egress module (§12) that handles all outbound delivery. Email today, ServiceNow in the future — callers are insulated from the transport. |
| **Standalone vuln** | A vulnerability with `report_id = NULL`. Managed independently; can be dispatched on its own. |
| **Report vuln** | A vulnerability exclusively owned by one report (`report_id` set). Cannot be dispatched individually — only dispatched as part of its parent report. |
| **Operator** | A platform user assigned to a vulnerability or report. |

**Blue-team interaction flow:** we create and dispatch a finding → blue team receives the email/payload → blue team registers it in their system and sends back an RVS ID → operator enters that RVS ID on our platform (transitions the vuln to `acknowledged`) → remediation tracking continues from there.

---

## Table of Contents

- [§1 Entity Model](#1-entity-model)
- [§2 Lifecycles](#2-lifecycles)
- [§3 Write Locking](#3-write-locking)
- [§4 Field-Level Edit Permissions](#4-field-level-edit-permissions)
- [§5 Vulnerability Fields](#5-vulnerability-fields)
- [§6 Report Fields](#6-report-fields)
- [§7 Report Editor](#7-report-editor)
- [§8 Vulnerability List UI](#8-vulnerability-list-ui)
- [§9 Report Dispatch](#9-report-dispatch)
- [§10 User Management](#10-user-management)
- [§11 Input Integration](#11-input-integration)
- [§12 Dispatcher Service](#12-dispatcher-service)
- [§13 Infrastructure & Deployment](#13-infrastructure--deployment)
- [§14 Deferred Post-MVP](#14-deferred-post-mvp)
- [§15 Data Model](#15-data-model)
- [§16 Technical Decisions](#16-technical-decisions)

---

## 1. Entity Model

### Two Vulnerability Types

| Type | `report_id` FK | Lock required | Lifecycle |
|---|---|---|---|
| **Standalone** | `NULL` | Never | Full lifecycle (see §2.1) |
| **Report vuln** | Set (exclusive) | Parent report lock | Starts in draft inside report; goes independent after report dispatched |

A vulnerability belongs to **at most one report**, exclusively. A standalone vuln cannot be migrated into a report and vice versa.

### One Table Per Entity

No separate draft tables. A single `vulnerabilities` table and a single `reports` table. The `status` column carries the full lifecycle state.

---

## 2. Lifecycles

### 2.1 Standalone Vulnerability

```
draft ──[save_draft]──────────► draft
draft ──[send]────────────────► saved_local   (internal ID assigned)
saved_local ──────────────────► dispatched    (routed via dispatcher service)
dispatched ───────────────────► acknowledged  (blue team assigns RVS ID)
acknowledged ─────────────────► waiting_fix
waiting_fix ──────────────────► pending_retest
pending_retest ───────────────► waiting_fix   (retest failed)
pending_retest ───────────────► fixed
```

### 2.2 Report

```
draft ──[save_draft]──────────► draft
draft ──[send]────────────────► dispatched    (end of report lifecycle)
```

Once dispatched, a report is **immutable** except for its internal notes field.

### 2.3 Report Vulnerability

```
draft   (exists only inside a report; edited under the report lock)
  │
  └── parent report dispatched
           │
           ▼
        dispatched  ──► acknowledged ──► waiting_fix ──► pending_retest ──► fixed
                                                              │
                                                              └──► waiting_fix
```

When the parent report is dispatched, all its linked vulns transition to `dispatched` in one batch. The package sent via the dispatcher service (§12) is a single combined payload: one PDF (the full operation report), one Excel file (all vulns as rows), and all non-image file attachments from all vulns. Only after this bulk dispatch are the vulns treated as independent records, each following its own lifecycle forward. See §9 for the full dispatch sequence.

---

## 3. Write Locking

**This section is the canonical lock definition. All other sections reference §3 rather than restate these rules.**

- The **report** is the only entity that carries a write lock.
- Holding the report lock grants write access to: the report itself, and all vulnerabilities with a FK to that report.
- Lock auto-releases after **10 minutes of inactivity** (idle-release: no writes for 10 min → lock is considered free on the next acquire attempt; no background job needed).
- **Standalone vulnerabilities** have no lock — freely editable by any authorized writer.
- Once a report is `dispatched`, it is immutable; the lock is not used. The only post-dispatch editable field is `internal_notes` on the report — no coordination needed for that field alone.

---

## 4. Field-Level Edit Permissions

### Vulnerabilities

| Status | Editable fields |
|---|---|
| `draft`, `saved_local` | All fields |
| `dispatched` | Internal notes · status · RVS ID — all other text fields read-only |
| `acknowledged` and beyond | Internal notes · status only — RVS ID is read-only (setting the RVS ID **is** the acknowledgment action; once set it cannot change) |

### Reports

| Status | Editable fields |
|---|---|
| `draft` | All fields |
| `dispatched` | Internal notes only — all other fields frozen |

---

## 5. Vulnerability Fields

| Field | Type | Notes |
|---|---|---|
| **Internal ID** | Auto-generated | e.g. `VULN-0042`; assigned on `saved_local` |
| **RVS ID** | Text, nullable | The blue team's tracking ID (see Glossary). Filled in when they respond post-dispatch; triggers transition to `acknowledged` |
| **Identifier** | Text | CVE-YYYY-NNNNN or free-text name |
| **CWE** | Text | e.g. `CWE-79` |
| **Description** | Markdown | |
| **Finding Detail** | Markdown | Technical write-up |
| **Mitigation / Solution** | Markdown | |
| **References** | List of URLs | |
| **CVSSv3.1 Score** | Float 0.0–10.0 | Manual entry |
| **CVSSv3.1 Vector** | Text | Manual string e.g. `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` |
| **Operators** | Linked users | List of operators assigned to this vuln |
| **Source** | Text, nullable | Origin of the vuln (e.g. `manual`, `nuclei`, `bugcrowd`, `api-import`). Set at creation; follows standard field-lock rules (read-only after `dispatched`) |
| **Extra Metadata** | JSON | Additional fields from inbound API calls stored as-is; see §11 and §15.8 |
| **Internal Notes** | Markdown | Operator-only; excluded from all exports |
| **Attachments** | Files | See §5.1 |
| **report_id** | FK, nullable | `NULL` = standalone vuln (see Glossary) |
| **Status** | Enum | See §2.1 / §2.3 |

> **Post-MVP:** CVSSv3.1 interactive calculator widget.

### 5.1 Attachments

All files are stored in MinIO (S3). URLs are pre-signed or proxied through the backend — no direct public S3 exposure.

- **Images** (PNG, JPG, GIF, WebP): operator assigns a name on upload; system stores the file in S3 and inserts `![name](url)` at cursor. Renders inline in editor and exported PDF.
- **Non-image files**: stored in S3 as downloadable attachments; included in the dispatch package when the vuln (or its parent report) is dispatched via the dispatcher service (§12).
- Upload methods: drag-and-drop, clipboard paste (Ctrl+V), file picker.

---

## 6. Report Fields

| Field | Type | Notes |
|---|---|---|
| **Internal ID** | Auto-generated | e.g. `OP-0007`; assigned on first save |
| **Name** | Text | |
| **Client Name** | Text | Target organisation; appears on cover |
| **Operators** | Linked users | All operators assigned to this report |
| **Start Date / End Date** | Dates | Execution window |
| **Status** | Enum | `draft` / `dispatched` |
| **Report content & sections** | See §7 | Cover, Executive Summary, TOC, Introduction, Report Data (structured fields), free-form extras, then linked vulns |
| **Evidence Bundle** | Files | Images, videos, code snippets, tables; stored in S3; available for embedding in report sections |
| **Internal Notes** | Markdown | Editable even after dispatch; excluded from exports |
| **Lock** | See §3 | Single lock covering the report and all its linked vulns |

---

## 7. Report Editor

### Structure
A report renders in the following fixed order. This table is the single source of truth for section definitions, storage, and editability.

| # | Section | Storage | Editable | Notes |
|---|---|---|---|---|
| 1 | **Cover** | Auto-rendered from report fields | No | Renders: name, client name, dates, operators |
| 2 | **Executive Summary** | `executive_summary_md` on `reports` | Yes | Pre-populated with a default template on report creation |
| 3 | **TOC** | Generated at render time | No | Built from section titles + vuln identifiers; never stored |
| 4 | **Introduction** | `introduction_md` on `reports` | Yes | Always custom; blank by default |
| 5 | **Report Data** | Structured columns on `reports` | Yes | See subfields below |
| 6 | **Free-form extras** | `report_sections` table (§15.6) | Yes | Operator-added, operator-ordered; any number; rendered here |
| 7 | **Vulnerabilities** | `vulnerabilities` table, FK to report | Auto-rendered | Sorted by CVSSv3.1 score descending |

**Report Data subfields** (all free text for MVP; enum constraints added post-MVP when values stabilise):

| Field | Column | Example values |
|---|---|---|
| Test type | `test_type` | infra, web, mobile, API |
| Demand origin | `demand_origin` | who/what originated the engagement |
| Environment | `environment` | production, staging, QA |
| Scope | `scope` | free-text description of what was in scope |
| Test model | `test_model` | graybox, blackbox, whitebox |

### Editing
- Vulnerability fields (description, finding detail, mitigation, etc.) are edited through the dedicated vulnerability editor — not inside the report editor.
- The report editor handles: editing report metadata, filling section content, adding/removing/reordering free-form extras, managing the evidence bundle.
- Editing requires the report lock (§3). Only one operator edits a given report at a time.

### Media Upload (Evidence Bundle)
- Upload via drag-and-drop or clipboard paste.
- Images: stored in S3; available for inline embedding in narrative sections via `![name](url)`.
- Non-image files: stored in S3 as evidence attachments; included in the dispatch package.

### Export Formats
| Template | Contents | Formats |
|---|---|---|
| Vulnerability Report | Single standalone vuln — all structured fields | PDF, DOCX |
| Operation Report | Report sections (in order) · all linked vulns (CVSS desc) · evidence bundle | PDF, DOCX |

Internal notes are stripped from all exports.

---

## 8. Vulnerability List UI

| Shown | Condition |
|---|---|
| Standalone vulns (all statuses) | Always |
| Report vulns | Only after parent report is `dispatched` — appear as independent records |
| Report vulns while report is `draft` | Never shown in this list; only visible inside the report editor |

---

## 9. Report Dispatch

Triggered by the operator clicking **Send** on a `draft` report. The following happen atomically:

1. All linked vulns transition `draft → dispatched` in one batch.
2. An **Excel file** is generated with all vulns as rows.
3. The **dispatcher service** is called with: PDF report + Excel + all non-image file attachments from all vulns combined. The dispatcher currently sends an email via Azure Communication Services (plain message body + all files attached). This is not hardcoded — the dispatcher is a swappable module; future implementations may route to ServiceNow or other destinations without touching this flow.
4. Report status set to `dispatched` — immutable from this point (except internal notes).
5. Report vulns appear in the vulnerability list as independent records, each managing its own lifecycle forward.

---

## 10. User Management

### 10.1 Authentication (MVP)

- Username + password; passwords hashed with bcrypt.
- JWT sessions: short-lived access tokens + refresh tokens.
- **API Keys** for machine-to-machine integrations: generated and revoked by `admin`, carry a role scope and optional expiry date.
- Auth layer structured as a pluggable strategy so **Azure AD / SSO can be added post-MVP** without touching application logic.

**First run:** if no users exist on startup, one `admin` user is seeded with a randomly generated password printed to container stdout (never stored in plaintext). User must change it on first login.

> **Post-MVP:** Azure AD SSO via Azure Entra ID.

### 10.2 Roles

| Role | Permissions |
|---|---|
| `admin` | Full access; user management, API key management, system config |
| `writer-all` | Create and edit any vuln or report |
| `reader-all` | Read-only across all records |
| `auditor` | Read-only + full audit log access |

> **Post-MVP:** `writer-report-selected` and `reader-selected` scoped roles (per-resource grants table). Deferred — ~20 operators makes global roles sufficient for MVP.

### 10.3 Audit Logs

Captured for every: login/logout · record create/read/update/delete · status transition · export action · API key generation/revocation/use · permission change.

Each entry stores: user · timestamp · action type · target entity ID · IP address.

Accessible via dedicated UI to the `auditor` role and `admin`.

---

## 11. Input Integration

- REST API accepting vulnerability data from external tools (scanners, C2s, recon pipelines).
- Required fields validated; additional fields stored as structured metadata.
- Callers control the initial status via a request parameter: `"status": "draft"` (default) or `"status": "saved_local"`. No system-level configuration — the caller decides per request.
- Authenticated via API keys (admin-managed).

### RVS Management Panel
- Queue view: vulns in `dispatched` status with no RVS ID.
- Operator fills in RVS ID → status transitions to `acknowledged`.

---

## 12. Dispatcher Service *(Decoupled Module)*

The dispatcher is the single egress point for all outbound notifications and exports. The rest of the platform calls one interface — `dispatch(target, payload)` — and knows nothing about the underlying transport.

**Current implementation:** Azure Communication Services email (plain message body + attachments).
**Future implementations:** ServiceNow, webhook, etc. — added by swapping the concrete implementation without modifying callers.

### Rendering (decoupled from transport)
Rendered artifacts are passed to the dispatcher as byte payloads — the renderer does not know or care about the destination. See §16 for library choices and rationale.

| Format | Scope |
|---|---|
| PDF | Single vuln report or full operation report, via selectable template |
| Excel | Vuln list with all fields as columns |
| DOCX | Single vuln report or full operation report |

### External Read API
Read-only REST endpoints exposing `dispatched`+ vulns and reports to authorized external consumers. API-key authenticated, role-scoped.

### Post-MVP Path
- ServiceNow implementation replaces or supplements email transport.
- Excel export deprecated when ServiceNow integration matures.
- New transports added by implementing the dispatcher interface.

---

## 13. Infrastructure & Deployment

| Concern | Solution |
|---|---|
| Deployment | Docker Compose, self-hosted, LAN + internet access |
| Database | PostgreSQL — single table per entity, `status` column carries lifecycle |
| File storage | MinIO (local S3-compatible) |
| Backend | Python — FastAPI |
| Frontend | Vue (SPA, API-driven) |
| Styling | Tailwind CSS |
| PDF export | WeasyPrint — see §16 |
| DOCX export | python-docx — see §16 |
| Dispatcher (MVP transport) | Azure Communication Services (email) |
| SSO | Deferred post-MVP; auth layer pre-wired for plug-in |
| Scale | ~20 concurrent operators — modular monolith |

---

## 14. Deferred Post-MVP

- Azure AD / SSO integration
- CVSSv3.1 calculator widget
- ServiceNow dispatcher implementation (replaces email)
- Excel export deprecation (follows ServiceNow migration)
- `writer-report-selected` and `reader-selected` scoped roles + per-resource grants table
- Status transitions driven by ServiceNow webhooks (currently all manual)

---

## 15. Data Model

**Stack:** PostgreSQL · SQLAlchemy 2.0 · Alembic (migrations). Files live in MinIO; DB stores S3 keys and metadata only.

### 15.1 Enums

| Enum | Values |
|---|---|
| `user_role` | `admin` · `writer_all` · `reader_all` · `auditor` |
| `vuln_status` | `draft` · `saved_local` · `dispatched` · `acknowledged` · `waiting_fix` · `pending_retest` · `fixed` |
| `report_status` | `draft` · `dispatched` |
| `audit_action` | `login` · `logout` · `create` · `read` · `update` · `delete` · `status_change` · `export` · `dispatch` · `api_key_create` · `api_key_revoke` · `permission_change` |

All 7 `vuln_status` values are implemented in MVP. Transitions currently triggered manually by operators; designed so ServiceNow can drive them post-MVP without schema changes.

### 15.2 Sequences

| Sequence | Format | Assigned when |
|---|---|---|
| `report_seq` | `OP-%04d` | First save of a report (draft → first write) |
| `vuln_seq` | `VULN-%04d` | Standalone: `saved_local` transition. Report vuln: parent report dispatched |

### 15.3 Table: `users`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `username` | text | UNIQUE NOT NULL | |
| `password_hash` | text | NULL | bcrypt; NULL reserved for future SSO-only accounts |
| `role` | user_role | NOT NULL | |
| `must_change_password` | bool | NOT NULL default true | forced on first-run admin and manual resets |
| `is_active` | bool | NOT NULL default true | deactivate instead of hard delete |
| `created_at` | timestamptz | NOT NULL | |
| `updated_at` | timestamptz | NOT NULL | |

### 15.4 Table: `api_keys`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `label` | text | NOT NULL | human-readable name |
| `key_prefix` | text | NOT NULL | first 8 chars of plaintext key; shown in UI for identification |
| `key_hash` | text | UNIQUE NOT NULL | full key hashed (bcrypt); plaintext shown exactly once at creation |
| `role` | user_role | NOT NULL | scope of this key |
| `created_by` | uuid | FK users NOT NULL | admin who issued it |
| `expires_at` | timestamptz | NULL | optional; admin-configured |
| `revoked_at` | timestamptz | NULL | soft-revoke |
| `last_used_at` | timestamptz | NULL | updated on each authenticated request |
| `created_at` | timestamptz | NOT NULL | |

### 15.5 Table: `reports`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `internal_id` | text | UNIQUE NULL | `OP-0007`; assigned from sequence on first save |
| `name` | text | NOT NULL | |
| `client_name` | text | NULL | target organisation; rendered on cover |
| `start_date` | date | NULL | |
| `end_date` | date | NULL | |
| `status` | report_status | NOT NULL default `draft` | |
| `executive_summary_md` | text | NULL | pre-populated with default template on creation |
| `introduction_md` | text | NULL | always custom |
| `test_type` | text | NULL | free text (MVP); enum post-MVP |
| `demand_origin` | text | NULL | free text |
| `environment` | text | NULL | free text |
| `scope` | text | NULL | free text |
| `test_model` | text | NULL | free text (MVP); enum post-MVP |
| `internal_notes` | text | NULL | markdown; editable even after dispatch |
| `dispatched_at` | timestamptz | NULL | |
| `lock_user_id` | uuid | FK users NULL | current lock holder |
| `lock_acquired_at` | timestamptz | NULL | |
| `lock_last_activity_at` | timestamptz | NULL | bumped on every write; idle-release triggers at now − 10 min |
| `created_by` | uuid | FK users NOT NULL | |
| `created_at` | timestamptz | NOT NULL | |
| `updated_at` | timestamptz | NOT NULL | |
| `deleted_at` | timestamptz | NULL | soft delete; all queries filter `IS NULL` |

**Lock implementation** (implements the rule in §3): any write to the report or its linked vulns bumps `lock_last_activity_at`. Lock acquisition checks lazily — if `now − lock_last_activity_at > 10 min`, the lock is considered free (no background job needed). `lock_user_id` is set to NULL on release. Dispatched reports skip lock checks entirely; only `internal_notes` is editable post-dispatch and requires no coordination.

### 15.6 Table: `report_sections`

Stores **free-form extra sections only** — the five typed sections (Cover, Executive Summary, TOC, Introduction, Report Data) are stored as columns on `reports`. Rows here are rendered after Report Data and before the vulnerabilities, in operator-defined order.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `report_id` | uuid | FK reports ON DELETE CASCADE NOT NULL | |
| `position` | int | NOT NULL | operator-controlled render order among extras (1-based) |
| `title` | text | NOT NULL | section heading as it appears in the report |
| `content_markdown` | text | NULL | |
| `created_at` | timestamptz | NOT NULL | |
| `updated_at` | timestamptz | NOT NULL | |

UNIQUE on (`report_id`, `position`); reordering shifts positions in a single transaction.

### 15.7 Table: `report_operators`

| Column | Type | Constraints |
|---|---|---|
| `report_id` | uuid | FK reports ON DELETE CASCADE |
| `user_id` | uuid | FK users |
| PK | | (`report_id`, `user_id`) |

### 15.8 Table: `vulnerabilities`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `internal_id` | text | UNIQUE NULL | `VULN-0042`; assigned on `saved_local` (standalone) or parent report dispatch (report vuln) |
| `report_id` | uuid | FK reports ON DELETE RESTRICT NULL | NULL = standalone; exclusive — one report only |
| `status` | vuln_status | NOT NULL default `draft` | |
| `rvs_id` | text | NULL | set at the `acknowledged` transition; read-only thereafter (app-enforced) |
| `identifier` | text | NOT NULL | CVE-YYYY-NNNNN or free-text name |
| `cwe` | text | NULL | e.g. `CWE-79` |
| `description` | text | NULL | markdown |
| `finding_detail` | text | NULL | markdown |
| `mitigation` | text | NULL | markdown |
| `references` | jsonb | NOT NULL default `'[]'` | ordered array of URL strings |
| `cvss_score` | numeric(3,1) | NULL | 0.0–10.0; CVSS label derived at render time |
| `cvss_vector` | text | NULL | manual string e.g. `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` |
| `source` | text | NULL | origin label e.g. `manual`, `nuclei`, `bugcrowd`, `api-import`; free text, set at creation |
| `internal_notes` | text | NULL | markdown; excluded from all exports |
| `extra_metadata` | jsonb | NOT NULL default `'{}'` | stores additional fields from inbound API |
| `dispatched_at` | timestamptz | NULL | |
| `acknowledged_at` | timestamptz | NULL | |
| `waiting_fix_at` | timestamptz | NULL | |
| `pending_retest_at` | timestamptz | NULL | |
| `fixed_at` | timestamptz | NULL | |
| `created_by` | uuid | FK users NOT NULL | |
| `created_at` | timestamptz | NOT NULL | |
| `updated_at` | timestamptz | NOT NULL | |
| `deleted_at` | timestamptz | NULL | soft delete |

**`report_id` constraint:** enforced at app layer — a vuln's `report_id` cannot change once the parent report is `dispatched`. `ON DELETE RESTRICT` prevents deleting a report that still has vulns.

### 15.9 Table: `vulnerability_operators`

| Column | Type | Constraints |
|---|---|---|
| `vulnerability_id` | uuid | FK vulnerabilities ON DELETE CASCADE |
| `user_id` | uuid | FK users |
| PK | | (`vulnerability_id`, `user_id`) |

### 15.10 Table: `attachments`

Covers both vuln attachments and report evidence bundle. Exactly one of the two owner FKs is non-null (CHECK constraint enforced).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK | |
| `vulnerability_id` | uuid | FK vulnerabilities ON DELETE CASCADE NULL | |
| `report_id` | uuid | FK reports ON DELETE CASCADE NULL | evidence bundle |
| `s3_key` | text | NOT NULL | MinIO object key |
| `original_filename` | text | NOT NULL | |
| `display_name` | text | NULL | operator-assigned name; for images used as markdown alt-text `![display_name](url)` |
| `mime_type` | text | NOT NULL | |
| `size_bytes` | bigint | NOT NULL | |
| `is_image` | bool | NOT NULL | true → embedded inline; false → sent as file attachment on dispatch |
| `uploaded_by` | uuid | FK users NOT NULL | |
| `created_at` | timestamptz | NOT NULL | |

CHECK: `(vulnerability_id IS NULL) != (report_id IS NULL)` — exactly one owner.

### 15.11 Table: `audit_logs`

Append-only. Never updated or deleted.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | bigserial | PK | integer sequence preferred over uuid for append-only high-volume table |
| `user_id` | uuid | FK users NULL | human actor; NULL if API key |
| `api_key_id` | uuid | FK api_keys NULL | machine actor; NULL if human |
| `action` | audit_action | NOT NULL | |
| `entity_type` | text | NULL | `vulnerability` / `report` / `user` / `api_key` |
| `entity_id` | uuid | NULL | |
| `detail` | jsonb | NULL | e.g. `{"from": "dispatched", "to": "acknowledged", "rvs_id": "RVS-2025-001"}` |
| `ip_address` | inet | NULL | |
| `created_at` | timestamptz | NOT NULL default now() | |

CHECK: `(user_id IS NULL) != (api_key_id IS NULL)` — exactly one actor.

### 15.12 Indexes

| Table | Index | Rationale |
|---|---|---|
| `vulnerabilities` | `(report_id)` | fetch all vulns for a report |
| `vulnerabilities` | `(status)` | filtered list views |
| `vulnerabilities` | `(status, dispatched_at)` | RVS queue (dispatched + no rvs_id) |
| `vulnerabilities` | `(cvss_score DESC)` | report export ordering |
| `vulnerabilities` | `(deleted_at)` | soft-delete filter |
| `reports` | `(status)` | list views |
| `reports` | `(lock_last_activity_at)` | idle-lock detection |
| `audit_logs` | `(entity_type, entity_id)` | per-record history |
| `audit_logs` | `(created_at)` | time-range queries |
| `attachments` | `(vulnerability_id)` | fetch attachments for a vuln |
| `attachments` | `(report_id)` | fetch evidence bundle for a report |

### 15.13 Entity Relationship Summary

```
users ─────────────────────── creates ──► vulnerabilities
  │                                          │        │
  ├── vulnerability_operators ──────────────┘        │ report_id (nullable FK)
  │                                                   │
  ├── report_operators ──────────────────────────────►│
  │                                          reports ◄┘
  │                                            │
  │                                            ├── report_sections
  │                                            └── attachments (evidence)
  │
  └── api_keys                        vulnerabilities
                                            └── attachments (vuln files)

audit_logs ◄── (user_id OR api_key_id) + entity reference
```

---

## 16. Technical Decisions

### PDF Export: WeasyPrint

Pipeline: Markdown → HTML (via `markdown-it-py`) → CSS-styled template → PDF (via WeasyPrint).

| Library | Verdict | Reason |
|---|---|---|
| **WeasyPrint** | ✅ Chosen | Pure Python, Docker-friendly, CSS-based templates, headers/footers/page numbers, actively maintained |
| Playwright | Rejected (MVP) | Pixel-perfect rendering, but ~300 MB Docker layer + browser binary dependency |
| pandoc | Rejected | Requires full LaTeX (~500 MB); harder to template |
| reportlab | Rejected | No Markdown input; verbose for complex layouts |

Templates are HTML + CSS files — familiar to anyone using Tailwind. WeasyPrint can be swapped for Playwright post-MVP if rendering fidelity requirements grow without changing the rest of the pipeline.

### DOCX Export: python-docx

Produces `.docx` from structured report data. No binary dependencies. Sufficient for document-style red team reports.

### CVSSv3.1 Input

MVP: manual entry of score (float) + vector string. No interactive calculator widget. **Post-MVP:** calculator widget deferred until after first release.
