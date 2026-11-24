<!-- page: api -->
# The integration API

The portal doesn't live on its own. Scanners find vulnerabilities, ticketing systems follow fixes, spreadsheets from past semesters hold history. The **integration API** is the door for those systems. Through it, a program can read vulnerabilities and reports, download evidence and documents, record RVS IDs, create and edit vulnerabilities, group them in batches and import past vulnerabilities with their history.

The API lives at `/api/v1` and is separate from the one the portal itself uses. A program doesn't sign in with a username and password, but with an **API key**, created by an administrator and limited to the **scopes** that program needs. A key only works on `/api/v1`; no other part of the portal accepts it.

This chapter starts with what applies to the whole API (keys, authentication, formats and paging) and then goes through the endpoints, grouped by what they do. If you are going to write an integration, read the first two sections first; the others work as a reference. This table sums up every endpoint:

| Endpoint | Scope | Section |
|---|---|---|
| `GET /api/v1/vulnerabilities` | `vulns:read` | [Reading vulnerabilities](#api-ler) |
| `GET /api/v1/vulnerabilities/{ref}` | `vulns:read` | [Reading vulnerabilities](#api-ler) |
| `GET /api/v1/vulnerabilities/{ref}/attachments` | `vulns:read` | [Reading vulnerabilities](#api-ler) |
| `GET /api/v1/attachments/{id}/content` | `vulns:read` or `reports:read` | [Reading vulnerabilities](#api-ler) |
| `GET /api/v1/vulnerabilities/{ref}/export` | `exports` | [Reading vulnerabilities](#api-ler) |
| `POST /api/v1/vulnerabilities` | `vulns:write` | [Create and edit](#api-criar), [Import](#api-importar) |
| `PATCH /api/v1/vulnerabilities/{ref}` | `vulns:write` | [Create and edit](#api-criar) |
| `POST /api/v1/batches` | `vulns:write` | [Batches](#api-lotes) |
| `GET /api/v1/rvs-queue` | `rvs:write` or `vulns:read` | [The RVS queue](#api-rvs) |
| `POST /api/v1/vulnerabilities/{ref}/rvs` | `rvs:write` | [The RVS queue](#api-rvs) |
| `GET /api/v1/reports` | `reports:read` | [Reading reports](#api-relatorios) |
| `GET /api/v1/reports/{ref}` | `reports:read` | [Reading reports](#api-relatorios) |
| `GET /api/v1/reports/{ref}/export` | `exports` | [Reading reports](#api-relatorios) |
| `GET /api/health` | none | [Errors and monitoring](#api-erros) |

<!-- page: api-chaves -->
# Keys, scopes and authentication

Every call to the API carries a key, and the key decides what the call can do. Only an administrator creates keys, on the **API keys** page: they name the key, choose its scopes and, if they wish, an expiry date. The full key is shown once only, right after it is created. The portal keeps just a hash of it and its first eight characters, the prefix, which identify the key in lists and logs.

## Scopes

A scope is a permission. Each endpoint requires one, and a key only does what its scopes allow.

| Scope | Allows |
|---|---|
| `vulns:read` | Reading vulnerabilities and their evidence |
| `vulns:write` | Creating and editing vulnerabilities and creating batches |
| `vulns:import` | Together with `vulns:write`, importing past vulnerabilities with their status, dates, number and RVS ID |
| `rvs:write` | Seeing the RVS queue and recording RVS IDs |
| `reports:read` | Reading reports and their evidence |
| `exports` | Downloading documents as PDF, Word and Excel |

The rule is to give each system only what it uses. A ticketing system that only records RVS IDs needs only `rvs:write`; a scanner that creates findings needs only `vulns:write`. The `vulns:import` scope calls for extra care, because it allows creating vulnerabilities with past dates and numbers: give it only to the import script's key, and revoke that key when the import is done.

A key reads every record its scope allows. The per-person restrictions of the Restricted editor and reader roles apply to people, not to systems.

## Authentication

The key goes in the `X-API-Key` header of each request. When there is a body, it is JSON:

```
X-API-Key: <your key>
Content-Type: application/json
```

A missing, unknown, revoked or expired key always gets the same answer, `401`, so that nobody can find out by trial which keys exist. A valid key without the endpoint's scope gets `403`, naming the missing scope. Outside `/api/v1`, no key works, whatever its scopes.

## What is recorded

A key's actions go into the audit logs like a person's, with the actor `api:<prefix>`: creations, edits, RVS IDs recorded, exports and evidence downloads. Vulnerabilities created through the API belong to the administrator who issued the key.

<!-- page: api-convencoes -->
# Formats, paging and syncing

A few rules hold for every endpoint, and knowing them up front saves surprises.

Where a path has `{ref}`, you can use the record's UUID or its internal ID, such as `VULN-0012` or `OP-0003`, in any case. Bodies and responses are JSON in UTF-8. Dates and times in responses are always UTC; in parameters, you can send them with a `Z` or an offset, and the portal converts them.

API responses have a format of their own, separate from what the portal's interface uses, so an integration doesn't break when the interface changes. They never carry internal notes or the *Shared with* list, just like exports.

## Paging

Lists, `/vulnerabilities` and `/reports`, come in last-change order and in pages:

```
{"items": [ ... ], "next_cursor": "MjAyNi0xMC0wOF..."}
```

The `limit` parameter says how many items come per page, from 1 to 200 (the default is 50). For the next page, pass the `next_cursor` you received as the `cursor` parameter. When `next_cursor` is `null`, the list is over. Lists carry a summary of each record; for the full content, read the record by its `{ref}`.

## Syncing

Last-change order makes it simple to keep another system up to date. The `updated_since` parameter limits the list to what was created or changed from a given moment, in ISO 8601, such as `2026-10-25T14:00:00Z`. Keep the `updated_at` of the last item you processed and, on the next run, ask for `updated_since` with that value, following `next_cursor` to the end. A record changed again shows up again, so your system always gets the latest version.

In Python, reading everything that changed since a given moment looks like this:

```
import os, requests

API = "https://<portal>/api/v1"
H = {"X-API-Key": os.environ["PORTAL_KEY"]}

def changed_since(since):
    params = {"updated_since": since, "limit": 200}
    while True:
        page = requests.get(f"{API}/vulnerabilities", headers=H, params=params, timeout=30)
        page.raise_for_status()
        page = page.json()
        yield from page["items"]
        if not page["next_cursor"]:
            break
        params["cursor"] = page["next_cursor"]

for v in changed_since("2026-10-25T00:00:00Z"):
    print(v["internal_id"], v["status"], v["updated_at"])
```

<!-- page: api-ler -->
# Reading vulnerabilities

Four endpoints, all with the `vulns:read` scope, read vulnerabilities and their evidence; a fifth, with the `exports` scope, downloads a vulnerability's document.

## Listing vulnerabilities

`GET /api/v1/vulnerabilities` lists the vulnerabilities that haven't been deleted, in pages and in last-change order. The parameters, all optional, filter the list:

| Parameter | Filters by |
|---|---|
| `status` | One or more statuses; repeat the parameter for several, as in `status=sent&status=fixing` |
| `source` | Source containing the text, in any case |
| `report` | A report's UUID or number; `none` for those in no report |
| `batch` | A batch, such as `BATCH-0001`, in any case; `none` for those in no batch |
| `cvss_min` | CVSS greater than or equal to, from 0 to 10 |
| `updated_since` | Created or changed from that moment on |
| `limit`, `cursor` | Paging, as in [Formats, paging and syncing](#api-convencoes) |

Each item of the response is a summary of the vulnerability. The possible statuses are `draft`, `ready`, `sent`, `fixing`, `retesting`, `fixed` and `risk_accepted`. The `internal_id` is null while the vulnerability is a draft, and the `rvs_id` until the RVS ID is recorded. The `report` field carries the report it belongs to, or null; `batch_id`, the batch it came in; and `imported_at`, when it was imported with its history.

```
curl -sS "https://<portal>/api/v1/vulnerabilities?status=fixing&limit=1" \
  -H "X-API-Key: $PORTAL_KEY"
```

```
{
  "items": [
    {
      "id": "92157428-3168-4c4e-9031-569928030ee9",
      "internal_id": "VULN-0003",
      "status": "fixing",
      "identifier": "Cross-Site Scripting (stored) - bi",
      "cwe": "CWE-79",
      "cvss_score": 10,
      "source": "nuclei",
      "rvs_id": "RVS-2026-1005",
      "report": null,
      "batch_id": null,
      "imported_at": null,
      "created_at": "2026-10-08T12:59:30.258918",
      "updated_at": "2026-10-08T12:59:30.315866"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozMC4zMTU4NjZ8OTIxNTc0Mjgt…"
}
```

An invalid status, date or cursor gets `422`, and a report in `report` that doesn't exist, `404`.

## Reading a vulnerability

`GET /api/v1/vulnerabilities/{ref}` returns the full vulnerability. Besides the summary fields, it carries the Markdown texts (`description`, `finding_detail` and `mitigation`), the `references`, the `cvss_vector`, the `operators` by username, the `metadata` sent by the tool that created it and the date it entered each status: `ready_at`, `sent_at`, `accepted_at`, `fixing_at`, `retesting_at`, `fixed_at` and `risk_accepted_at`. If the defense team accepted the risk, the reason comes in `risk_reason`. A vulnerability that doesn't exist gets `404`.

```
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0003 -H "X-API-Key: $PORTAL_KEY"
```

```
{
  "id": "92157428-3168-4c4e-9031-569928030ee9",
  "internal_id": "VULN-0003",
  "status": "fixing",
  "identifier": "Cross-Site Scripting (stored) - bi",
  "cwe": "CWE-79",
  "cvss_score": 10,
  "source": "nuclei",
  "rvs_id": "RVS-2026-1005",
  "report": null,
  "batch_id": null,
  "imported_at": null,
  "created_at": "2026-10-08T12:59:30.258918",
  "updated_at": "2026-10-08T12:59:30.315866",
  "description": "Content stored and rendered without escaping.",
  "finding_detail": "Found in bi. To reproduce: request to /bi/v2/resource/…",
  "mitigation": "Sanitise on input and escape on output.",
  "references": [],
  "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N",
  "operators": ["benjamin", "michelle"],
  "metadata": {},
  "ready_at": "2026-10-08T12:59:30.282810",
  "sent_at": "2026-10-08T12:59:30.301332",
  "accepted_at": "2026-10-08T12:59:30.319272",
  "fixing_at": "2026-10-08T12:59:30.319272",
  "retesting_at": null,
  "fixed_at": null,
  "risk_accepted_at": null,
  "risk_reason": null
}
```

## Evidence

`GET /api/v1/vulnerabilities/{ref}/attachments` lists the files attached to the vulnerability, oldest first, each with `id`, `filename`, `display_name`, `mime_type`, `size_bytes` and `created_at`:

```
[
  {
    "id": "3f1c2a9e-5b7d-4e61-9a0c-2d8e4b6f1a73",
    "filename": "login-burp.png",
    "display_name": "Login request",
    "mime_type": "image/png",
    "size_bytes": 48213,
    "created_at": "2026-10-20T14:02:11.502114"
  }
]
```

To download a file, use its `id` in `GET /api/v1/attachments/{id}/content`. The response is the file itself, with its `Content-Type` and `Content-Disposition: attachment`. A vulnerability's evidence needs `vulns:read`, and a report's, `reports:read`; without the scope of the file's owner, the answer is `404`, as if it didn't exist. Each download is kept in the audit logs.

```
curl -sS -o login-burp.png \
  https://<portal>/api/v1/attachments/3f1c2a9e-5b7d-4e61-9a0c-2d8e4b6f1a73/content \
  -H "X-API-Key: $PORTAL_KEY"
```

## Exporting

`GET /api/v1/vulnerabilities/{ref}/export`, with the `exports` scope, returns the same file as the *Export* button, with the evidence images. The `format` parameter chooses between `pdf`, the default, and `docx`; any other format gets `422`. The file name comes in the `Content-Disposition`, such as `VULN-0002.docx`, and the export is kept in the audit logs.

```
curl -sS -o VULN-0002.pdf "https://<portal>/api/v1/vulnerabilities/VULN-0002/export?format=pdf" \
  -H "X-API-Key: $PORTAL_KEY"
```

<!-- page: api-criar -->
# Creating and editing vulnerabilities

A scanner or another tool can record its findings straight into the portal, without anyone copying them by hand. With the `vulns:write` scope, `POST /api/v1/vulnerabilities` creates a vulnerability, and `PATCH /api/v1/vulnerabilities/{ref}` edits one that hasn't been sent yet.

## Creating

The body is a JSON object of up to 1 MB, with the same fields as the portal's form. All of them are optional, but at least one of `identifier`, `description` and `finding_detail` must be filled in: a vulnerability with none of them would say nothing.

| Field | Content |
|---|---|
| `identifier` | The finding's name or a CVE, up to 500 characters |
| `description` | The Description, in Markdown, up to 100,000 characters; the same goes for the next two |
| `finding_detail` | The Finding Details |
| `mitigation` | The Mitigation / Solution |
| `cwe` | `CWE-79` or just `79`; the portal stores it as `CWE-79` |
| `cvss_score` | The score, from 0 to 10 |
| `cvss_vector` | The vector, up to 200 characters |
| `references` | Up to 50 URLs, each starting with `http://` or `https://` |
| `source` | The originating tool, such as `nuclei` or `burp`; it is what the `source:` filter searches |
| `internal_notes` | The internal notes, in Markdown |
| `operators` | Up to 20 usernames of active users with the Administrator, Editor (all) or Restricted editor role |
| `status` | `draft`, the default, or `ready` |
| `batch_id` | This run's batch (see [Batches](#api-lotes)) |
| `metadata` | A free-form object, kept as it came, up to 64 KB |

The `status` deserves attention. A vulnerability created as `draft` waits for an analyst to review it in the portal, which is the best choice when the finding came from an automated tool. Created as `ready`, it already needs `identifier`, `description` and `finding_detail`, the same fields the *Complete* button requires, and gets its internal ID straight away. An ordinary creation never produces an already sent vulnerability; to bring in a past one with its history, use the [import](#api-importar).

Fields the portal doesn't know aren't refused: they go into the metadata, together with the `metadata` object. That way a tool can send its own data, such as the host or the template that produced the finding, without the portal having to know about it.

```
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \
  -d '{"identifier": "Exposed .git directory", "source": "nuclei", "cwe": "527",
       "cvss_score": 5.3, "operators": ["jonathan"], "host": "app.example.com"}'
```

The response, with status `201`, carries the vulnerability's `id`, which is also its address in the portal (`/vulnerabilities/<id>`), and the `internal_id`, present only when it was created as `ready`:

```
{"id": "72643b23-af52-42d9-a139-c1aea6f70a15", "internal_id": null, "status": "draft", "batch_id": null, "imported": false}
```

There is no de-duplication: repeating the same request creates another vulnerability. If a creation failed because of a network error, check whether it arrived, with the `source` filter, before sending it again.

## Editing

`PATCH /api/v1/vulnerabilities/{ref}` changes only the fields sent, with the same names and rules as creation; whatever isn't in the body stays as it is. This is how a tool corrects a finding it recorded, fills in a field or moves a vulnerability to another batch: `"batch_id": "BATCH-0004"` puts it in an existing batch, and `"batch_id": null` takes it out of its batch. The `operators` list, when sent, replaces the previous one. The response is the full vulnerability, as when reading it.

```
curl -sS -X PATCH https://<portal>/api/v1/vulnerabilities/VULN-0042 \
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \
  -d '{"cvss_score": 7.5, "mitigation": "Upgrade the library to version 2.4."}'
```

Editing has limits, which protect what was already delivered and the work of the people in the portal. Only draft or ready vulnerabilities outside a report can be edited. One already sent gets `409`, and so does one inside a draft report; that one is edited in the portal, under the report's reservation. A ready vulnerability must keep its `identifier`, `description` and `finding_detail`, and a draft at least one of them. The lifecycle stays in the portal, so `status`, the import fields and unknown fields get `422`.

If someone else might be working on the same vulnerability, send `if_updated_at` with the `updated_at` you last read. If the record changed since then, nothing is written and the answer is `409`: read it again and decide. On the other side, whoever is editing the vulnerability in the portal gets the conflict notice when saving.

A request that changes nothing creates no version and no audit entry. Each real change goes into the logs with the key as the actor, and a batch move shows as `{"from", "to"}`.

<!-- page: api-lotes -->
# Batches

A tool usually records many findings in the same run, such as a network scan or a sweep of a domain. A **batch** groups the vulnerabilities of one run, so that it is easy later to find, review and follow everything that came together.

The batch is created before the vulnerabilities. `POST /api/v1/batches`, with the `vulns:write` scope and no body, creates a new batch and returns the number the portal gave it:

```
{"batch_id": "BATCH-0001", "created_at": "2026-11-24T19:30:04.949885"}
```

The tool then sends that `batch_id` with each `POST /api/v1/vulnerabilities` of the run. The number takes any case, and a batch that doesn't exist gets `422`. This script creates a batch and records one finding in it for each JSON file in the folder:

```
BATCH=$(curl -sS -X POST https://<portal>/api/v1/batches -H "X-API-Key: $PORTAL_KEY" | jq -r .batch_id)
for f in findings/*.json; do
  jq --arg b "$BATCH" '. + {batch_id: $b}' "$f" |
    curl -sS -X POST https://<portal>/api/v1/vulnerabilities \
      -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" -d @-
done
```

To read a batch, filter the list: `GET /api/v1/vulnerabilities?batch=BATCH-0001`. In the portal, the same filter is `batch:BATCH-0001` in Operations, and each vulnerability shows its batch at the top of its page.

## Changing the batch later

A vulnerability's batch is the integration's business, so it only changes through the API, never on the portal's form. While the vulnerability is a draft or ready, a [PATCH](#api-criar) with `batch_id` moves it to another batch, and `null` takes it out. This script moves the whole of `BATCH-0003` into `BATCH-0004`:

```
curl -sS "https://<portal>/api/v1/vulnerabilities?batch=BATCH-0003&limit=200" -H "X-API-Key: $PORTAL_KEY" |
  jq -r '.items[].id' | while read id; do
    curl -sS -X PATCH "https://<portal>/api/v1/vulnerabilities/$id" \
      -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" -d '{"batch_id": "BATCH-0004"}'
  done
```

<!-- page: api-importar -->
# Importing past vulnerabilities

When the portal arrives, the work of earlier semesters already exists somewhere else, in a spreadsheet or an old system. For the dashboards and timelines to tell the whole story, those vulnerabilities can be **imported** as they ended up: with their final status, the date of each stage, their original number and their RVS ID.

The import uses the same endpoint and the same body as [creation](#api-criar), `POST /api/v1/vulnerabilities`, with a few more fields. Those fields require the key to have, besides `vulns:write`, the `vulns:import` scope; without it, any of them gets `403`.

| Field | Content |
|---|---|
| `status` | Any status: `draft`, `ready`, `sent`, `fixing`, `retesting`, `fixed` or `risk_accepted` |
| `internal_id` | The original number, such as `VULN-0042`; without it, the vulnerability gets the next number, and a draft has no number |
| `created_at`, `ready_at`, `sent_at` | The dates of creation, completion and sending |
| `accepted_at`, `fixing_at` | Acceptance by the defense team and the start of the fix |
| `retesting_at`, `fixed_at` | The retest request and the fix |
| `risk_accepted_at` | When the defense team accepted the risk |
| `updated_at` | The last change; by default, the latest of the dates |
| `rvs_id` | The RVS ID, required for `fixing`, `retesting` and `fixed` |
| `accepted_by`, `risk_accepted_by` | The usernames of who accepted or took the risk, if they are portal users |
| `risk_reason` | The reason, required for `risk_accepted` |

Dates use ISO 8601, with a `Z` or an offset, and are converted to UTC. None may be in the future.

## The dates must tell a coherent story

The portal checks that the dates make sense for the status. Each status needs the dates of the stages leading to it, and none of the stages that would come after. A `sent` vulnerability needs `created_at`, `ready_at` and `sent_at`, and may have `accepted_at`. One in `fixing` also needs `fixing_at` and the `rvs_id`; `accepted_at`, if not sent, is set to `fixing_at`. In `retesting`, it needs `retesting_at` too. A `fixed` one needs `created_at`, `ready_at`, `sent_at`, `fixing_at`, `fixed_at` and `rvs_id`, and the retest is optional. A `risk_accepted` one needs `created_at`, `ready_at`, `sent_at`, `risk_accepted_at` and the `risk_reason`.

The dates must also follow the lifecycle's order: created, ready, sent, accepted, fixing, retesting, fixed, with the risk accepted after sending. When something doesn't fit, the `422` answer lists every problem at once, so you can fix the spreadsheet in a single pass. Beyond draft, the usual required fields apply too: `identifier`, `description` and `finding_detail`.

## The original number

With `internal_id`, the vulnerability keeps the number it had, and the portal's next numbers come after the highest number imported, so there are never two alike. A number that already exists gets `409`, and so does an RVS ID that already belongs to another vulnerability.

## What the import doesn't do

The import delivers nothing to anyone: no email is sent. Nor does it invent history. The audit logs have a single creation entry, marked `"import": true`, not one per stage. The vulnerability keeps the import date in `imported_at`, which appears in API reads and as *Imported on …* on its page, and the response carries `"imported": true`. Imported vulnerabilities are standalone, with no report. If a vulnerability went through fixes that failed in the past, those don't become events; note them in `internal_notes` or the `metadata`.

```
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \
  -H "X-API-Key: $IMPORT_KEY" -H "Content-Type: application/json" \
  -d '{"identifier": "SQL injection in the Customer Portal", "description": "…", "finding_detail": "…",
       "status": "fixed", "internal_id": "VULN-0042", "rvs_id": "RVS-2025-00017",
       "created_at": "2025-03-03T14:00:00-03:00", "ready_at": "2025-03-04T10:00:00-03:00",
       "sent_at": "2025-03-05T09:00:00-03:00", "fixing_at": "2025-03-12T16:00:00-03:00",
       "retesting_at": "2025-04-01T10:00:00-03:00", "fixed_at": "2025-04-02T11:00:00-03:00",
       "internal_notes": "Imported from the 2025S1 spreadsheet"}'
```

```
{"id": "…", "internal_id": "VULN-0042", "status": "fixed", "batch_id": null, "imported": true}
```

Before importing a whole semester, try a few vulnerabilities first. Use a key just for the import, with an expiry date, and revoke it when you are done.

<!-- page: api-rvs -->
# The RVS queue

When the organisation follows fixes in a ticketing system, that system is the one that knows the RVS ID opened for each vulnerability. Two endpoints let it record the RVS ID straight into the portal, without anyone on the defense team typing it.

`GET /api/v1/rvs-queue`, with the `rvs:write` or `vulns:read` scope, lists the sent vulnerabilities that don't have an RVS ID yet, from the longest-waiting to the most recent. The list isn't paged, and each item has the summary fields from [Reading vulnerabilities](#api-ler).

```
curl -sS https://<portal>/api/v1/rvs-queue -H "X-API-Key: $PORTAL_KEY"
```

```
[
  {
    "id": "6598c3c4-c1eb-43d3-8412-3c36d1682462",
    "internal_id": "VULN-0001",
    "status": "sent",
    "identifier": "Insecure deserialisation - erp",
    "cwe": "CWE-502",
    "cvss_score": 3.3,
    "source": "nessus",
    "rvs_id": null,
    "report": null,
    "batch_id": null,
    "imported_at": null,
    "created_at": "2026-10-08T12:59:30.068791",
    "updated_at": "2026-10-08T12:59:30.108013"
  }
]
```

Once the RVS is open, `POST /api/v1/vulnerabilities/{ref}/rvs`, with the `rvs:write` scope, records it. The body carries the ID, 1 to 200 characters long:

```
curl -sS -X POST https://<portal>/api/v1/vulnerabilities/VULN-0001/rvs \
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \
  -d '{"rvs_id": "RVS-2026-001"}'
```

The vulnerability moves to *Fixing*, and the response is the full vulnerability, with `"status": "fixing"` and the `rvs_id`. Recording the RVS ID also counts as accepting the vulnerability, as when the defense team does it in the portal. It is kept in the audit logs, and the ID can't be changed afterwards.

Since an RVS ID can only be recorded once, and only on a sent vulnerability, attempts outside those conditions get `409`: on a vulnerability that isn't sent, on one that already has an RVS ID, or with an ID that already belongs to another vulnerability. An empty `rvs_id` gets `422`.

<!-- page: api-relatorios -->
# Reading reports

Through the API, reports are only read: creating, editing and sending them remains the Red Team's work in the portal. With the `reports:read` scope, an integration can list and read them, and with `exports`, download their documents.

## Listing reports

`GET /api/v1/reports` lists the reports that haven't been deleted, in pages and in last-change order. The `status` parameter filters by `draft` or `sent` (repeat it for both), and `client` searches the client's name. Paging and `updated_since` work as in [Formats, paging and syncing](#api-convencoes).

Each item carries the `internal_id` (`OP-xxxx`, null until sent), the name, the client, the status, the operation's dates as `YYYY-MM-DD`, the sending date and three counts: `vulnerability_count`, how many vulnerabilities the report has, `fixed_count`, how many have been fixed, and `closed_count`, how many are fixed or have had their risk accepted.

```
curl -sS "https://<portal>/api/v1/reports?status=sent&limit=1" -H "X-API-Key: $PORTAL_KEY"
```

```
{
  "items": [
    {
      "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
      "internal_id": "OP-0001",
      "name": "Web Application Pentest - Customer Portal",
      "client_name": "Banco Aurora S.A.",
      "status": "sent",
      "start_date": "2026-08-03",
      "end_date": "2026-08-21",
      "sent_at": "2026-10-08T12:59:35.258463",
      "vulnerability_count": 3,
      "fixed_count": 0,
      "closed_count": 0,
      "created_at": "2026-10-08T12:59:35.029437",
      "updated_at": "2026-10-08T12:59:35.204803"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozNS4yMDQ4MDN8MDU2YzNlZWUt…"
}
```

## Reading a report

`GET /api/v1/reports/{ref}` returns the full report. Besides the summary fields, it carries the operation's data (`test_type`, `test_model`, `environment`, `demand_origin` and `scope`), the executive summary and introduction in Markdown (`executive_summary_md` and `introduction_md`), the additional sections in order, the operators, a summary of each of the report's vulnerabilities and the list of its evidence. As everywhere in the API, internal notes aren't included. A report that doesn't exist gets `404`.

```
curl -sS https://<portal>/api/v1/reports/OP-0001 -H "X-API-Key: $PORTAL_KEY"
```

```
{
  "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
  "internal_id": "OP-0001",
  "name": "Web Application Pentest - Customer Portal",
  "client_name": "Banco Aurora S.A.",
  "status": "sent",
  "…": "the other summary fields",
  "test_type": "Pentest",
  "test_model": "Gray box",
  "environment": "Staging",
  "demand_origin": "Annual contract",
  "scope": "banco-aurora-s.a..example",
  "executive_summary_md": "Vulnerabilities requiring **priority attention** were found…",
  "introduction_md": "Results of the work carried out for **Banco Aurora S.A.**.",
  "sections": [
    {"position": 1, "title": "Methodology", "content_markdown": "Manual and automated testing, following OWASP and PTES."}
  ],
  "operators": ["jonathan"],
  "vulnerabilities": [
    {"id": "e4a61965-ab90-41f6-b0d3-d05db0816f74", "internal_id": "VULN-0074", "status": "sent", "…": "each one's summary"}
  ],
  "attachments": []
}
```

## Exporting

`GET /api/v1/reports/{ref}/export`, with the `exports` scope, returns the same files as the *Export* button. The `format` parameter chooses the report as `pdf`, the default, or `docx`, or the vulnerabilities spreadsheet as `xlsx`. The file name comes in the `Content-Disposition`, such as `OP-0001_20261025.pdf` or `OP-0001_vulnerabilidades_20261025.xlsx`.

```
curl -sS -o OP-0001.xlsx "https://<portal>/api/v1/reports/OP-0001/export?format=xlsx" \
  -H "X-API-Key: $PORTAL_KEY"
```

<!-- page: api-erros -->
# Errors, monitoring and good practice

When something goes wrong, the response has an HTTP code, which says the kind of problem, and a body with the `detail` field, which says the problem itself. Most of the time `detail` is a text; for format errors, such as a number out of range, it is a list with the field and the reason.

| Code | Means |
|---|---|
| `401` | The key is missing, invalid, revoked or expired |
| `403` | The key lacks the endpoint's scope, or the import scope for the fields sent |
| `404` | The record doesn't exist or was deleted |
| `409` | The action doesn't fit the record's current state |
| `413` | The body is over 1 MB |
| `422` | Invalid data or parameters, an invalid `cursor` included |

A `409` comes up in cases like recording the RVS ID of a vulnerability that isn't sent, editing one that was already sent, sending an outdated `if_updated_at` or importing a number or an RVS ID that already exists. These are a few examples of `detail` in a `422`:

```
{"detail": "Required for status 'ready': description, finding_detail"}
{"detail": "unknown operator(s): nobody; operator(s) not active writers: isabella"}
{"detail": "status 'fixed' needs: fixing_at; sent_at is after fixing_at"}
{"detail": [{"loc": ["body", "cvss_score"], "msg": "Input should be less than or equal to 10", ...}]}
```

## Checking the portal

`GET /api/health` needs no key and answers `200` while the portal is up, which is useful for monitoring:

```
curl -sS https://<portal>/api/health
```

```
{"status": "ok", "environment": "production"}
```

## Good practice

Use one key per system, with only the scopes it uses and an expiry date, and revoke the ones no longer used. Never put the key in code or in a repository: read it from an environment variable or a secrets vault.

To keep another system up to date, use `updated_since` and `next_cursor` instead of downloading everything on each run. When a finding still needs an analyst's review, create it as `draft`, and in a run with several findings, create a batch and send its `batch_id` with each one.

Remember that there is no de-duplication: after a network error, check whether the vulnerability arrived before sending it again. And to import, use a dedicated key, try a few vulnerabilities first and revoke the key at the end.
