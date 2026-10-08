# Ingest API

Lets scanners, C2s and recon pipelines push vulnerabilities into the portal (SPEC §11).

## Authentication

An **admin** creates a key under *Chaves de API* (role `write_all` or `admin`; keys with
`read_all` / `auditor` are refused). The plaintext is shown **once**. Send it in a header:

```
X-API-Key: <key>
```

Keys work **only** on `/ingest/*`. They cannot reach the UI endpoints, users, keys or the audit
log, regardless of role. A revoked, expired, unknown or missing key all return the same `401`.

## Create a vulnerability

`POST /api/ingest/vulnerabilities` — JSON, max 1 MB.

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
| `operators` | string[] ≤ 20 | **usernames**; must be active `admin`, `write_all` or `write_restricted` accounts |
| `status` | `"draft"` (default) \| `"saved_local"` | the caller decides per request |
| `metadata` | object | stored as-is; ≤ 64 KB together with unknown fields |
| *(any other field)* | any | stored in metadata |

Rules:

- At least one of `identifier`, `description`, `finding_detail` must be non-blank.
- `status: "saved_local"` additionally requires `identifier`, `description`, `finding_detail` and
  `mitigation` (the same as the UI's *Enviar*) and assigns the `VULN-xxxx` internal id.
- Ingest can never create a `dispatched` (or later) vulnerability.
- The record is owned by the admin who issued the key; the **key** is the actor in the audit log.

### Example

```bash
curl -sS -X POST https://portal.example/api/ingest/vulnerabilities \
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \
  -d '{
        "identifier": "Exposed .git directory",
        "source": "nuclei",
        "cwe": "CWE-527",
        "cvss_score": 5.3,
        "references": ["https://cwe.mitre.org/data/definitions/527.html"],
        "operators": ["alice"],
        "metadata": {"template": "git-config", "host": "app.example.com"}
      }'
# 201 {"id":"…","internal_id":null,"status":"draft"}
```

### Errors

| Status | Meaning |
|---|---|
| 401 | missing / invalid / revoked / expired key |
| 403 | key role cannot create vulnerabilities |
| 413 | body over 1 MB |
| 422 | validation failed (the `detail` says what) |

## Not implemented yet

- Idempotency / de-duplication: a retried request creates a second record. An `external_id`
  field (unique per `source`) would fix that — needs a decision.
- Rate limiting, and a batch endpoint.
