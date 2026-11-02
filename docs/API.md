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
| `GET /v1/vulnerabilities` | `vulns:read` | summaries; filters `status` (repeatable), `source`, `report` (UUID, number or `none`), `cvss_min`, `updated_since`; paging `limit` (≤ 200) + `cursor` |
| `GET /v1/vulnerabilities/{ref}` | `vulns:read` | full record (no internal notes, no viewers) |
| `GET /v1/vulnerabilities/{ref}/attachments` | `vulns:read` | evidence metadata |
| `GET /v1/attachments/{id}/content` | `vulns:read` / `reports:read` | evidence file; needs the scope of its owner (404 otherwise) |
| `GET /v1/vulnerabilities/{ref}/export?format=pdf\|docx` | `exports` | same file as the UI export |
| `GET /v1/rvs-queue` | `rvs:write` or `vulns:read` | sent, no RVS ID yet, oldest first |
| `POST /v1/vulnerabilities/{ref}/rvs` `{"rvs_id"}` | `rvs:write` | sent → fixing; 409 otherwise or when already set |
| `POST /v1/vulnerabilities` | `vulns:write` | create (below) |
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
| `status` | `"draft"` (default) \| `"ready"` | the caller decides per request |
| `metadata` | object | stored as-is; ≤ 64 KB together with unknown fields |
| *(any other field)* | any | stored in metadata |

- At least one of `identifier`, `description`, `finding_detail` must be non-blank.
- `ready` also requires `identifier`, `description`, `finding_detail` and `mitigation` (as the
  UI's *Concluir*) and assigns the `VULN-xxxx` number.
- Never creates a `sent` (or later) vulnerability.

Response `201 {"id": "…", "internal_id": null, "status": "draft"}`.

## Errors

| Status | Meaning |
|---|---|
| 401 | missing / invalid / revoked / expired key |
| 403 | the key lacks the endpoint's scope |
| 404 | record not found (or deleted) |
| 409 | not allowed in the current status (e.g. RVS on a vuln not sent, or already set) |
| 413 | body over 1 MB |
| 422 | validation failed, including an invalid `cursor` (the `detail` says what) |

## Not implemented yet

- Idempotency / de-duplication (`external_id` unique per `source`): a retried create makes a second
  record.
- Updates and lifecycle moves (`PATCH`, send, transitions), batch create, evidence upload.
- Change feed / webhooks; per-key rate limiting.
