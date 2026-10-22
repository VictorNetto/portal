# Red Team Operations Platform

A self-hosted web platform for a professional red team to **manage, document, and report** security vulnerabilities and assessment operations. It is an internal management tool for ~20 operators — not an offensive/attack tool.

**Stack:** Python (FastAPI, SQLAlchemy 2, Alembic) · PostgreSQL 16 · Vue 3 (Vite, Pinia) · nginx · Docker Compose · ReportLab / python-docx / openpyxl for documents · SMTP for dispatch.

## What works today

| Area | Highlights |
|---|---|
| **Vulnerabilities** | Draft → sent → dispatched → acknowledged (RVS id) → waiting fix → retest loop → fixed; field locks per status; optimistic concurrency; admin status correction with audit; operators; timeline |
| **Reports** | OP-xxxx ids, write lock (10 min idle, admin force-release), Markdown sections, free-form extra sections, vulnerabilities inside the report, evidence files, two-phase dispatch with retry |
| **Editor** | Markdown editor with preview, line gutter, image paste/drop (stored as attachments), safe renderer |
| **Attachments** | Pluggable storage (local volume or S3/MinIO), type/content validation, 50 MB cap, proxied + audited reads |
| **Exports** | PDF, Excel and Word for reports; PDF/Word for a vulnerability; batch ZIP/Excel from the Hub. Internal notes are never exported |
| **Dispatch** | Decoupled dispatcher: `stub` (default, logs only) or `smtp` (real email with PDF + Excel + non-image files) |
| **Ingest API** | `POST /ingest/vulnerabilities` with API keys for scanners — see [docs/INGEST_API.md](docs/INGEST_API.md) |
| **Administration** | Users and roles (admin · write_all · read_all · write_restricted · read_restricted · auditor; see D10), forced password change on first login, API keys, audit log viewer |
| **Hub** | Vulnerabilities / Reports tabs, filter language, details drawer with timeline, row and batch actions, RVS queue |
| **i18n** | PT-BR and EN (language selector in the profile menu) |

## Quick start (development)

```bash
cp .env.example .env            # once; edit as needed
docker compose up -d --build    # db, api (reload), web (Vite HMR), nginx
```

Open **http://localhost:8080**. On the first start an `admin` user is created with a **random password printed in the api logs** (`docker compose logs api`); set `FIRST_ADMIN_PASSWORD` in `.env` before the first start to choose one. New and reset users must change their password at first login.

Database migrations live in `backend/migrations` (Alembic). The API image does not bundle them; run them with the folder mounted:

```bash
docker compose run --rm -v "$PWD/backend:/work" -w /work -e PYTHONPATH=/work api alembic upgrade head
```

### Services

| Service | Role |
|---|---|
| `nginx` | The only published port (8080). `/api/*` → backend, everything else → Vite |
| `api` | FastAPI (the backend owns no `/api` prefix; nginx strips it) |
| `web` | Vue dev server with hot reload |
| `db` | PostgreSQL, data in the `db-data` volume |
| *(files)* | Attachments in the `attachments-data` volume (`STORAGE_BACKEND=local`) |

> MinIO is optional: set `STORAGE_BACKEND=s3` and the `MINIO_*` variables to use any S3-compatible server. See decision **D9** in [docs/DECISIONS.md](docs/DECISIONS.md) for why local storage is the default.

### Configuration (`.env`)

See [.env.example](.env.example). The ones you will touch: `FIRST_ADMIN_PASSWORD`, `JWT_SECRET` (**must** be changed outside dev), `STORAGE_BACKEND`, and for real email `DISPATCH_TRANSPORT=smtp` + `DISPATCH_TO` + `SMTP_*`.

## Tests

The backend has an integration suite that drives the running API over HTTP and uses the same dev database (everything it creates is named `pytest-…` and cleaned up at the end):

```bash
docker compose exec api pip install pytest httpx pypdf    # once per container
docker compose exec api python -m pytest tests -q
```

Lint with `pip install ruff && cd backend && ruff check app tests` (configuration in `backend/pyproject.toml`).

It covers authentication and the forced password change, the vulnerability lifecycle and corrections, attachments (validation and access rules), the report lock, sections, dispatch (including the failure → retry path), exports, and the ingest API. By default it logs in as `admin` / `admin` (dev only); override with `TEST_ADMIN_USER` / `TEST_ADMIN_PASSWORD`.

## Production

A production stack is provided: built frontend, non-root API with several workers, nginx terminating TLS (with a strict Content-Security-Policy and security headers), and encrypted backup/restore scripts.

```bash
cp .env.production.example .env.production      # fill in real secrets
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Step-by-step procedures (first deployment, updates, certificates, backups and restores, troubleshooting) are in **[docs/RUNBOOK.md](docs/RUNBOOK.md)**. The API refuses to start in production with the development `JWT_SECRET`.

The UI has a browser suite too (`e2e/`, Playwright: 37 tests over login and the forced password change, the vulnerability form, the Hub, reports and their lock, dispatch and exports, the lifecycle and the admin pages). See [e2e/README.md](e2e/README.md) for the one-line command.

## Repository layout

```
backend/
  app/            FastAPI app: routers/ (HTTP), services/ (business rules), models/, schemas/,
                  render.py (PDF/Excel/Word), dispatcher.py, storage.py, security.py
  migrations/     Alembic migrations
  tests/          pytest integration suite
e2e/              Playwright browser tests (run in the official Playwright container)
frontend/
  src/            views/, components/ (Markdown editor, timeline, ...), i18n.js, api.js, router.js
nginx/            Reverse proxy config (nginx.conf = dev, prod.conf.template = production/TLS)
scripts/          backup.sh / restore.sh (database + attachments, optionally encrypted)
docs/
  specs/          Canonical specifications (SPEC.md, FRONTEND_SPEC.md)
  DECISIONS.md    Resolved design decisions D1–D11 with rationale
  BACKLOG.md      Parked features and pending decisions (template management, constraints, …)
  DEPLOYMENT.md   Deployment & networking plan + IT-request checklist
  RUNBOOK.md      Operating the production stack: deploy, update, certificates, backup/restore
  INGEST_API.md   Contract for scanners / pipelines
prototypes/       Original HTML prototypes of the screens
```

## Core concepts

- **Vulnerability** — a finding; standalone (`report_id = NULL`) or owned by a report. Inside a draft report it has no life of its own and is edited under the report's lock; once the report is dispatched it joins the normal list.
- **Report** — an operation: metadata, narrative sections, its vulnerabilities and an evidence bundle, dispatched as a unit.
- **Dispatch** — two phases (decision D2): everything moves to `dispatching` in one transaction, then the package is rendered and delivered; a delivery failure leaves it in `dispatching` so it can be retried.
- **RVS** — the blue team's own tracking id, entered after dispatch to move a vulnerability to `acknowledged`.
- **Operator** — a platform user assigned to vulnerabilities/reports.

## Which file is "the" spec?

- `docs/specs/SPEC.md` — the system spec.
- `docs/specs/FRONTEND_SPEC.md` — the frontend spec.

Earlier numbered duplicates are preserved under the respective `archive/` folders and are not authoritative.

## Known gaps

- Several **permission constraints** (who may delete, dispatch or reassign what) are catalogued but not yet decided — the current rule is "any writer".
- Date-based filters in the Hub (`created:`, `updated:`…) are designed but waiting on a product decision.
- `DISPATCH_TRANSPORT=smtp` is verified against a test SMTP server only; Azure Communication Services is not wired.
- The production stack has been exercised on a throwaway server (self-signed certificate) but not yet on the real VM with the org certificate.
