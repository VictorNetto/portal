# Integration API

Lets other systems read vulnerabilities and reports, download exports, record RVS IDs and push
vulnerabilities into the portal (SPEC §11, D13). The user-facing documentation, with examples, is
the **API** section of the in-app Documentação page (`frontend/src/docs.js`); this file is the
developer summary.

## Authentication and scopes

An **admin** creates a key under *Chaves de API* with one or more scopes and an optional expiry.
The plaintext is shown **once**; only a SHA-256 hash and the 8-char prefix are stored (D7).

```
X-API-Key: <key>
```

| Scope | Allows |
|---|---|
| `vulns:read` | read vulnerabilities and their evidence |
| `vulns:write` | create vulnerabilities |
| `vulns:import` | with `vulns:write`: create past vulnerabilities with their status, dates, number and RVS ID ([Import](#import-past-vulnerabilities)) |
| `rvs:write` | see the RVS queue and record RVS IDs |
| `reports:read` | read reports and their evidence |
| `exports` | download PDF / Word / Excel |

- Keys work **only** on `/v1/*` (public path `/api/v1/*`). They
  cannot reach the UI endpoints, users, keys or the audit log (`401`).
- Missing / unknown / revoked / expired key: the same `401`. Missing scope: `403`
  (`"This API key lacks the scope 'rvs:write'"`).
- Keys read every record their scope allows: per-user access (D10) is for people, not systems.
- Creations, RVS records, exports and evidence downloads are audited with the key as the actor
  (`api:<prefix>`). Records created by a key belong to the admin who issued it.

Code: scopes in `backend/app/scopes.py`, the dependency `require_scope()` in `deps.py`, the endpoints
in `routers/integration.py`, the response shapes in `schemas/integration.py` (kept apart from the UI
schemas so integrations don't follow UI changes).

## Endpoints

| Method and path | Scope | Purpose |
|---|---|---|
| `GET /v1/vulnerabilities` | `vulns:read` | summaries; filters `status` (repeatable), `source`, `report` (UUID, number or `none`), `batch` (`BATCH-0001` or `none`), `cvss_min`, `updated_since`; paging `limit` (≤ 200) + `cursor` |
| `GET /v1/vulnerabilities/{ref}` | `vulns:read` | full record (no internal notes, no viewers) |
| `GET /v1/vulnerabilities/{ref}/attachments` | `vulns:read` | evidence metadata |
| `GET /v1/attachments/{id}/content` | `vulns:read` / `reports:read` | evidence file; needs the scope of its owner (404 otherwise) |
| `GET /v1/vulnerabilities/{ref}/export?format=pdf\|docx` | `exports` | same file as the UI export |
| `GET /v1/rvs-queue` | `rvs:write` or `vulns:read` | sent, no RVS ID yet, oldest first |
| `POST /v1/vulnerabilities/{ref}/rvs` `{"rvs_id"}` | `rvs:write` | sent → fixing; 409 otherwise or when already set |
| `POST /v1/vulnerabilities` | `vulns:write` | create (below) |
| `PATCH /v1/vulnerabilities/{ref}` | `vulns:write` | edit a draft or ready vulnerability, its batch included (below) |
| `POST /v1/batches` | `vulns:write` | a new batch id for the vulns of one run (below) |
| `GET /v1/reports` | `reports:read` | summaries with `vulnerability_count` and `fixed_count`; filters `status`, `client`, `updated_since`; paging |
| `GET /v1/reports/{ref}` | `reports:read` | full report with sections, vulnerability summaries, evidence list |
| `GET /v1/reports/{ref}/export?format=pdf\|xlsx\|docx` | `exports` | same files as the UI export |
| `GET /health` | none | liveness |

`{ref}` is a UUID or the record number (`VULN-0012`, `OP-0003`, case-insensitive).

**Paging and sync.** Lists are ordered by `(updated_at, id)` and keyset-paginated: the response is
`{"items": [...], "next_cursor": "..."}`; pass `cursor` for the next page, `null` means the end.
`updated_since` (ISO 8601; a `Z`/offset is converted to UTC) returns what changed since then, so
"remember the last `updated_at`, ask again with `updated_since`, follow `next_cursor`" keeps another
system in sync. Times are UTC. `updated_at` is maintained by the DB on every row update.

## Create a vulnerability

`POST /v1/vulnerabilities` — JSON, max 1 MB.

| Field | Type | Notes |
|---|---|---|
| `identifier` | string ≤ 500 | CVE or free-text name |
| `description`, `finding_detail`, `mitigation` | string ≤ 100 000 | Markdown |
| `cwe` | string | `CWE-79` or `79` (normalised to `CWE-79`) |
| `cvss_score` | number 0–10 | |
| `cvss_vector` | string ≤ 200 | |
| `references` | string[] ≤ 50 | each must be an `http(s)` URL |
| `source` | string ≤ 200 | e.g. `nuclei`, `burp` |
| `internal_notes` | string | |
| `operators` | string[] ≤ 20 | **usernames**; active `admin`, `write_all` or `write_restricted` accounts |
| `batch_id` | string | from `POST /v1/batches` (any case); an unknown id is a 422 |
| `status` | `"draft"` (default) \| `"ready"` | the caller decides per request; any other status only with `vulns:import` |
| `metadata` | object | stored as-is; ≤ 64 KB together with unknown fields |
| *(any other field)* | any | stored in metadata |

- At least one of `identifier`, `description`, `finding_detail` must be non-blank.
- `ready` also requires `identifier`, `description` and `finding_detail` (as the UI's
  *Concluir*; `mitigation` may stay blank) and assigns the `VULN-xxxx` number.
- Never creates a `sent` (or later) vulnerability.

Response `201 {"id": "…", "internal_id": null, "status": "draft", "batch_id": null, "imported": false}`.

## Import past vulnerabilities

For vulnerabilities from earlier semesters, tracked elsewhere. The same `POST /v1/vulnerabilities`
and body, from a key that also holds **`vulns:import`**: the vulnerability arrives as it ended up,
with the dates of each step, so the timeline and the dashboards' durations are the real ones.
Without that scope, any of these fields is a `403`.

| Field | Notes |
|---|---|
| `status` | any: `draft`, `ready`, `sent`, `fixing`, `retesting`, `fixed`, `risk_accepted` |
| `internal_id` | its original number (`VULN-0042`, any case); the counter moves past it, so new numbers never collide. Omitted: the next number. A draft has none. `409` if it exists |
| `created_at`, `ready_at`, `sent_at`, `accepted_at`, `fixing_at`, `retesting_at`, `fixed_at`, `risk_accepted_at` | ISO 8601 (a `Z`/offset is converted to UTC); none in the future |
| `updated_at` | defaults to the last of its dates; not before it |
| `rvs_id` | required for `fixing`, `retesting`, `fixed`; `409` if another vulnerability has it |
| `accepted_by`, `risk_accepted_by` | usernames of existing accounts (optional) |
| `risk_reason` | required for `risk_accepted` |

Each status needs the dates of the steps that lead to it, and nothing later:

| Status | Required | Optional |
|---|---|---|
| `draft` | `created_at` | |
| `ready` | + `ready_at` | |
| `sent` | + `sent_at` | `accepted_at` |
| `risk_accepted` | `created_at`, `ready_at`, `sent_at`, `risk_accepted_at`, `risk_reason` | `accepted_at` |
| `fixing` | `created_at`, `ready_at`, `sent_at`, `fixing_at`, `rvs_id` | `accepted_at` (default `fixing_at`) |
| `retesting` | + `retesting_at` | `accepted_at` |
| `fixed` | `created_at`, `ready_at`, `sent_at`, `fixing_at`, `fixed_at`, `rvs_id` | `accepted_at`, `retesting_at` |

Dates must follow each other (created ≤ ready ≤ sent ≤ accepted ≤ fixing ≤ retesting ≤ fixed, and
sent ≤ risk accepted); the `422` lists every problem at once. The content rules are the usual ones
(beyond `draft`: `identifier`, `description` and `finding_detail`), and `internal_notes`,
`operators`, `batch_id` and `metadata` work as for any creation.

Nothing is sent (no email), and no history is made up: the audit log has one creation entry
with `"import": true`. The record keeps `imported_at` (in the reads and on its page, *Importada
em …*). The response says `"imported": true`. Imports are standalone vulnerabilities.

```json
{
  "identifier": "SQL injection em Portal do Cliente", "description": "…", "finding_detail": "…",
  "status": "fixed", "internal_id": "VULN-0042", "rvs_id": "RVS-2025-00017",
  "created_at": "2025-03-03T14:00:00-03:00", "ready_at": "2025-03-04T10:00:00-03:00",
  "sent_at": "2025-03-05T09:00:00-03:00", "fixing_at": "2025-03-12T16:00:00-03:00",
  "retesting_at": "2025-04-01T10:00:00-03:00", "fixed_at": "2025-04-02T11:00:00-03:00",
  "internal_notes": "Imported from the 2025S1 tracker"
}
```

## Batches

A tool that creates many vulnerabilities in one run can group them: call `POST /v1/batches`
(no body) first, which returns `201 {"batch_id": "BATCH-0001", "created_at": "…"}`, then send
`"batch_id": "BATCH-0001"` with each `POST /v1/vulnerabilities` of the run. The id is made by the
portal; a vulnerability can be moved to another batch or taken out of it later with `PATCH`
(below). Vulnerability reads include `batch_id` (`null` when in none),
`GET /v1/vulnerabilities?batch=BATCH-0001` lists one batch, and the Hub filters it with
`batch:BATCH-0001`.

```bash
BATCH=$(curl -s -X POST -H "X-API-Key: $KEY" https://portal/api/v1/batches | jq -r .batch_id)
for f in findings/*.json; do
  jq --arg b "$BATCH" '. + {batch_id: $b}' "$f" |
    curl -s -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d @- https://portal/api/v1/vulnerabilities
done
```

## Edit a vulnerability

`PATCH /v1/vulnerabilities/{ref}` (`vulns:write`) changes the fields sent and nothing else, with
the names and rules of the create body: `identifier`, `cwe`, `description`, `finding_detail`,
`mitigation`, `references`, `cvss_score`, `cvss_vector`, `source`, `internal_notes`, `operators`
(usernames; replaces the list) and `batch_id` (an existing batch, any case; `null` takes the
vulnerability out of its batch). The response is the full record, as `GET` returns it.

- Only a **draft** or **ready** standalone vulnerability: once sent it is a `409`, and so is one
  inside a draft report (edit it in the portal, under the report's lock).
- A ready vulnerability keeps `identifier`, `description` and `finding_detail`; a draft keeps at
  least one of them (`422` otherwise).
- Unknown fields are a `422` (no metadata here), and so are `status` and the import fields: the
  lifecycle stays in the portal.
- `if_updated_at` (optional): the `updated_at` the tool last read. If the record changed since,
  nothing is written and the answer is `409`; read it again.
- A request that changes nothing makes no new version and no audit entry. Each change is audited
  with the key as the actor (a batch move as `{"from", "to"}`), and an editor open in the portal
  sees it as a conflict.

```bash
# Move every vulnerability of BATCH-0003 into BATCH-0004
curl -s -H "X-API-Key: $KEY" "https://portal/api/v1/vulnerabilities?batch=BATCH-0003&limit=200" |
  jq -r '.items[].id' | while read id; do
    curl -s -X PATCH -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
      -d '{"batch_id": "BATCH-0004"}' "https://portal/api/v1/vulnerabilities/$id"
  done
```

## Errors

| Status | Meaning |
|---|---|
| 401 | missing / invalid / revoked / expired key |
| 403 | the key lacks the endpoint's scope |
| 404 | record not found (or deleted) |
| 409 | not allowed in the current status (e.g. RVS on a vuln not sent, or already set; editing a sent vuln), or `if_updated_at` is stale |
| 413 | body over 1 MB |
| 422 | validation failed, including an invalid `cursor` (the `detail` says what) |

## Not implemented yet

- Idempotency / de-duplication (`external_id` unique per `source`): a retried create makes a second
  record.
- Lifecycle moves (complete, send, transitions), editing metadata, evidence upload.
- Change feed / webhooks; per-key rate limiting.
