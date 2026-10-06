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
