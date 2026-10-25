# Design Decisions Log

Resolved edge-case decisions for the Red Team Operations Platform MVP. Each entry records the question, the decision, and why. The specs in `docs/specs/` are the normative source; this file explains the reasoning behind choices that were otherwise ambiguous.

Status legend: ✅ decided · ⏳ open

---

## D1 — Deleting a draft report with linked vulns ✅

**Question:** `vulnerabilities.report_id` was `ON DELETE RESTRICT`, and a report vuln can never become standalone — so a draft report with vulns couldn't be deleted. What is the delete flow?

**Decision:** A report vuln has no independent existence until its parent report dispatches, so:
- Deleting a **`draft`** report **cascade-deletes its draft vulns**. `report_id` FK becomes `ON DELETE CASCADE`.
- Deletion is **blocked at the app layer for any non-`draft` report** — once dispatched, the report and its (now independent) vulns are immutable and cannot be deleted.
- Standalone vulns are never touched by report deletion (they have no `report_id`).

**Why:** Draft report vulns are not yet "real" findings; they only exist inside the report. Cascade is safe for drafts; the app-layer guard prevents cascade from ever reaching live, dispatched records.

---

## D2 — Dispatch atomicity (DB + render + MinIO + email) ✅

**Question:** §9 dispatch spans Postgres, artifact rendering, MinIO, and email — these cannot be truly atomic. What happens if delivery fails after the DB transition?

**Decision:** Introduce a transient **`dispatching`** status (added to both `vuln_status` and `report_status`). Two phases:
1. **DB transaction:** flip report + linked vulns to `dispatching`, assign `VULN-xxxx` internal IDs, commit. Fast, atomic, all in Postgres.
2. **Render + dispatch:** build PDF/Excel/DOCX, call the dispatcher. On success → flip to `dispatched`, set `dispatched_at`. On failure → **stay in `dispatching`** with the error recorded; the operator retries.

While a report is `dispatching` it is **locked from editing**. Nothing ever reads as `dispatched` unless delivery actually succeeded.

**Why:** A half-sent state must never masquerade as a completed dispatch. A retryable transient state is more honest than a rollback that would have to un-assign already-issued internal IDs.

---

## D3 — `identifier` required-ness ✅

**Question:** `vulnerabilities.identifier` was `NOT NULL`, but scanner imports and quick drafts often have no CVE/name yet.

**Decision:** `identifier` is **nullable while `draft` / `saved_local`**, and **required as a dispatch precondition** enforced at the app layer (standalone: at `send`/`saved_local`→`dispatched`; report vuln: at parent report dispatch). DB column is nullable.

**Why:** Forcing an identifier at creation breaks API imports and rapid drafting. The meaningful gate is dispatch, not creation.

---

## D4 — Stuck / abandoned locks ✅

**Question:** The 10-minute idle release handles normal churn, but what about a lock held by an operator who left (closed laptop)? No override path existed.

**Decision:** Keep the 10-minute idle release. Add an explicit **force-release available to `admin` only** for now. The UI shows who holds a lock and since when. Force-release is **audited** (dedicated `lock_override` audit action).

**Future:** May widen force-release to `writer-all` if the team finds admin-only too restrictive — this is a single permission-check change and does not touch the lock mechanism.

**Why:** Admin-only is the safe default and trivially widened later. The 10-min window still covers the common case automatically.

---

## D5 — Concurrent edits to standalone vulns ✅

**Question:** Standalone vulns have no lock by design, so two operators editing one = silent last-write-wins (lost edits).

**Decision:** **Optimistic concurrency** via a dedicated `version` integer column on `vulnerabilities`. The client submits the `version` it last read; the server rejects a stale write with **HTTP 409 Conflict** and the client re-fetches. `version` increments on every successful write.

**Why:** No locks to manage, no lost writes, cheap to implement. A dedicated integer avoids timestamp-granularity/clock issues that `updated_at`-based checks suffer.

---

## D6 — Correcting mistaken transitions ✅

**Question:** The lifecycle is forward-only (except the retest loop), and RVS ID is immutable once set. What about human mistakes — an accidental dispatch, a wrong RVS ID?

**Decision:** Provide an **`admin` correction path**: admins can reset a record's status and clear an incorrectly entered RVS ID. **Every correction is written to the audit log** (via a `correction` / `status_change` entry capturing from→to and the admin actor).

**Why:** Real-world use produces mistakes; requiring manual DB surgery is brittle and dangerous. Scoping corrections to admin + full audit keeps it controlled.

---

## D7 — API-key hashing ✅

**Question:** §10.1 specified bcrypt for API keys. bcrypt is deliberately slow (good for human passwords, bad for machine keys verified on every request).

**Decision:** Hash API keys with **plain SHA-256**, and **enforce high entropy at generation** — keys are 32+ bytes from a CSPRNG (`secrets.token_urlsafe(32)` or similar). Lookup is an indexed query on the stored hash. User passwords remain on **bcrypt** (unchanged — they are low-entropy and need slow hashing).

**Why:** A fast hash is safe here *because* the key is unguessable random input; there is nothing to brute-force, so bcrypt's slowness buys nothing and would add latency to every authenticated API call. Salting/peppering is unnecessary for the same reason (rejected HMAC-with-server-secret: marginal benefit, adds a secret to manage and rotate).

**Spec impact:** §10.1 and the `api_keys.key_hash` note (§15.4) change bcrypt → SHA-256.

---

## D8 — Audit logging of read events ✅

**Question:** §10.3 logs every read. With list views and polling this is high volume and risks drowning the audit log in noise.

**Decision:** **Keep per-read audit logging.** The portal holds confidential red-team findings; a record of *who accessed which vulnerability/report and when* is a deliberate security control, not incidental noise.

**Operational note:** watch `audit_logs` growth. The table is append-only with a `bigserial` PK and indexed on `(entity_type, entity_id)` and `(created_at)` (§15.11–12). If volume becomes a problem post-MVP, address it with **retention/archival or partitioning** — not by dropping read capture. List-view reads should log the *query/listing* access, not one row per item returned, to keep volume proportional to user actions.

**Why:** Confidentiality and traceability outweigh table-size concerns, which are solvable operationally without sacrificing the security signal.

---

## D9 — Attachment storage: pluggable backend, local volume by default ✅

**Context:** the spec calls for MinIO, but every route to the image is closed from the dev network: Docker Hub (`minio/minio`) is blocked by the org proxy, GHCR denies, Quay returns 401, and `dl.min.io` no longer serves binaries.

**Decision:** storage sits behind a small interface (`app/storage.py`: `put` / `open` / `delete`) with two backends, selected by `STORAGE_BACKEND`:
- `local` (default) — files on the `attachments-data` Docker volume. Needs only official images.
- `s3` — any S3-compatible server via the `minio` SDK (`MINIO_*` settings). Verified against a `moto` S3 server; not yet against a real MinIO.

Files are never exposed directly: the API proxies every read, so authentication and per-read audit logging (D8) always apply. Uploads are validated by extension allowlist + magic bytes (client Content-Type ignored); SVG is excluded; 50 MB cap; attachments follow the vuln's content-field lock (draft / saved_local only).

**Why:** unblocks attachments now without changing any endpoint; production can pick `s3` (MinIO or an equivalent such as SeaweedFS/Garage) later with a config change.

**Open:** the local volume must be included in backups when this backend is used in production (`docs/DEPLOYMENT.md`).

---

## D10 — Restricted roles and per-record access ✅

**Context:** with many users, most should not see (or touch) every record. Two roles were added next to the original ones, and the original two were renamed `writer_all → write_all`, `reader_all → read_all` (migration `f4d6e8a0b2c3` renames the enum values in place, so existing users and API keys keep their access).

| Role | Sees | Changes |
|---|---|---|
| `admin` | everything | everything |
| `write_all` | everything | everything |
| `read_all` | everything | nothing |
| `auditor` | everything | nothing (plus the audit log) |
| `write_restricted` | records it **created**, **operates**, or was **shared** | creates its own; edits records it created or operates; deletes only what it created |
| `read_restricted` | records it created/operates, or was **shared** with | nothing |

**How it works**
- Per-record lists: `viewers` ("Shared with") on every vulnerability and report, set by anyone who can edit that record. No groups yet — access is granted user by user.
- A report's vulnerabilities follow the report: whoever reads/edits the report reads/edits them (under the report lock, as before).
- Enforcement is in one module (`backend/app/access.py`), used by every service: lists and the RVS queue are filtered in SQL; single-record reads, exports (single and batch), attachments and the lifecycle actions check the record.
- A record the user may not read answers **404, never 403**, so its existence is not revealed. A readable record the user may not change answers 403.
- The UI mirrors the same rules (`frontend/src/access.js`) so it only offers what will work; the server never trusts it.
- The creator always keeps access, so removing yourself as operator cannot strand a record.
- Ingest: operators named in a payload may also be `write_restricted` users.

**Consequences / open points**
- Restricted writers can list user names (needed to pick operators); restricted readers cannot.
- Dispatch, RVS acknowledgment and the post-acknowledgment transitions follow "may edit this record". Tighten them in the constraints catalogue if needed.
- Not covered by this decision: groups/teams, sharing requests, read-only sharing for `write_*` roles.

---

## D11 — Report templates (first version) ✅

**What a template is:** the text of a report's sections — Sumário Executivo, Introdução and the
Seções Adicionais (titles, order, content). Nothing else (no client, dates, people, vulnerabilities).

**How it works**
- *Saving:* "Salvar como Template" on the report editor opens a modal (name; admins also get
  "Disponível para todos os usuários"). It saves what is on screen, unsaved edits included.
  Anyone who can create reports may save one.
- *Using:* the "Criar Relatório" card has a Template chip, "Nenhum" by default; clicking it lists the
  templates the user can use (mine, for all users, and — admins only — other users').
  "Nenhum" keeps the standard starting text (the executive-summary outline).
- *Copied, not linked:* the report receives a copy; later changes to the template never reach it.
  The report remembers which template it came from (`reports.template_id`, set to NULL if the
  template is ever deleted).
- *Sharing is reviewed* (replaces the earlier "admin shares directly"):

  | State | Who sees / uses it | Owner may | Admin may |
  |---|---|---|---|
  | `private` | its owner | edit, delete, **request** sharing | edit, delete |
  | `pending` | its owner (frozen) | **withdraw** the request | **approve** / **reject** (→ private) |
  | `shared` | everyone | nothing — recreate it to change it | edit, delete, **unshare** |
  | `unshared` | nobody (owner included; admins see it, cannot use it) | — | delete, **reshare** |

  Only the owner requests; only an admin approves — admins' own templates go through the same two
  steps, and nothing can be shared at creation. The owner is warned before requesting that an approved
  template leaves their control. `POST /report-templates/{id}/sharing {action}`; every step is
  audited, and the template records when it was requested and who decided, when.
- *Admins* see every template (with an "N aguardando aprovação" queue on the Templates page) and may
  edit or delete any of them. A template a user may not see answers 404 and cannot start a report (422).
- *Editing* carries a `version` (409 on a stale one). Deleting never touches reports created from it.
  Readers and auditors have no access to templates at all (403).

**Not yet:** duplicate, and create from scratch on the page. See `BACKLOG.md`.


## D12 — Session limits and portal dialogs ✅

**Decision:** a session lasts at most **1 hour** from login and ends sooner after **15 minutes without
activity**. Both limits are enforced by the server, not only on screen.

- Every token carries the session start (`sst`). `/auth/refresh` returns a new pair but keeps the
  start, so renewing never pushes the 1 h end. The refresh token lives 15 min (capped at the end);
  the access token 5 min. An idle browser therefore cannot renew after 15 min, whatever it does.
- The browser renews at most once a minute and only after real activity (mouse, keys, scroll),
  shared across tabs through `localStorage`. Background calls (lock heartbeat) do not count as
  activity.
- On screen (`SessionGuard`): 2 min before the idle end, "Você ainda está aí?" with a countdown;
  5 min before the 1 h end, "save your work". When the session ends with **unsaved edits**, the page
  stays and a modal asks for the password again; signing in starts a new session and the edits can
  be saved. "Descartar e sair" leaves without further questions. With nothing unsaved, the user goes
  to the login page with the reason.
- Settings: `SESSION_MAX_MINUTES`, `SESSION_IDLE_MINUTES`, `ACCESS_TOKEN_TTL_MINUTES`.

**Dialogs:** `window.confirm`/`prompt` are replaced by one portal modal (`AppDialog`,
`confirmDialog()`/`promptDialog()` in `dialog.js`). Only the browser's own "leave this site?" on tab
close stays native: browsers allow nothing else there.

## D13 — Integration API with scoped keys ✅

**Decision:** other systems integrate through `/api/v1`, authenticated by API keys that carry
**scopes** (`vulns:read`, `vulns:write`, `rvs:write`, `reports:read`, `exports`) instead of a user
role. An admin picks the scopes and an optional expiry per key.

- Keys read every record their scope allows (per-user access is for people). They never reach the
  UI endpoints.
- Records are addressed by UUID or number; lists are keyset-paginated by `updated_at` with
  `updated_since`, which is enough to sync without a change feed for now.
- Responses use their own schemas (no internal notes, viewers or locks) so integrations don't follow
  UI changes. Writes and exports are audited with the key as the actor.
- Migration: existing keys whose role could create vulnerabilities got `vulns:write`; the others
  had no ability and got no scope.
- The first machine endpoint, `POST /ingest/vulnerabilities`, was removed: `POST /v1/vulnerabilities`
  does the same, and nothing outside used the old path yet.
- **Out for now:** dispatch through the API (it emails people; stays a human decision), deletes and
  admin actions. **Later:** de-duplication (`external_id`), updates/lifecycle, batch, evidence
  upload, webhooks.
