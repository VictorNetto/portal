# Operations Runbook

Step-by-step procedures for running the portal in production. Background and the reasons behind the choices are in [DEPLOYMENT.md](DEPLOYMENT.md); this file is the "what do I type" companion. Everything was exercised end-to-end on a throwaway stack (self-signed certificate, empty database) before being written down.

All commands run on the server from the repository root.

```bash
# Shorthand used below
export PORTAL_ENV_FILE=.env.production
alias dc='docker compose -f docker-compose.prod.yml --env-file .env.production'
```

---

## 1. First deployment

**Prerequisites** (see DEPLOYMENT.md §8): Ubuntu 24.04, Oracle Linux 9 or SLES 16 / 15 SP7 VM with Docker + Compose, DNS name pointing at it, an org-PKI certificate for that name. For a new server, follow [INSTALL.md](INSTALL.md) instead: it covers the OS and Docker too, and ends where this runbook takes over.

1. Get the code: `git clone <repo> && cd portal`.
2. Create the secrets file and fill in **every** value:
   ```bash
   cp .env.production.example .env.production
   chmod 600 .env.production
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"    # -> JWT_SECRET
   ```
   The API **refuses to start** in production with the development `JWT_SECRET` or one shorter than 32 characters. Choose strong random values for `POSTGRES_PASSWORD` (and the same password inside `DATABASE_URL`).
3. Install the certificate. In `./certs` (or the folder named by `PORTAL_CERT_DIR`):
   - `fullchain.pem` — the server certificate **followed by** the intermediate chain
   - `privkey.pem` — the private key (`chmod 600`; never commit it — `certs/` is git-ignored)
4. Build and migrate:
   ```bash
   dc build
   dc up -d db
   dc run --rm api alembic upgrade head
   ```
5. Start everything and read the first admin password:
   ```bash
   dc up -d
   dc ps                 # every service Up; api "healthy"
   dc logs api | grep -i password     # unless you set FIRST_ADMIN_PASSWORD
   ```
6. Open `https://<PORTAL_SERVER_NAME>`, log in as `admin` — you are forced to set a new password immediately.
7. **Set up backups now** (section 4) and take a first one.
8. Email: set `DISPATCH_TRANSPORT=smtp`, `DISPATCH_TO` and the `SMTP_*` values in `.env.production`, then `dc up -d api`. Until then sending only logs (`stub`) and nothing is delivered. A send that cannot deliver leaves the report in *Rascunho*, frozen, with *Falha no envio* and the error shown; fix the settings and press **Tentar novamente**.

What is exposed: only nginx publishes ports (80 → redirect, 443). `db`, `api` and `web` are reachable only on the private Docker network.

## 2. Releasing an update

```bash
git pull
dc build
dc run --rm api alembic upgrade head      # apply new migrations (a no-op when there are none)
dc up -d
dc ps && dc logs --tail 50 api
```

Take a backup first when the release contains a migration. Migrations are forward-only; to go back, restore the pre-release backup (section 5).

## 3. Everyday operations

| Task | Command |
|---|---|
| Status | `dc ps` |
| Logs | `dc logs -f api` (also `nginx`, `db`) |
| Restart one service | `dc restart api` |
| Stop / start all | `dc stop` / `dc up -d` |
| Health check | `curl -fsS https://<host>/api/health` |
| Disk used by data | `docker system df -v` (watch the `attachments-data` volume) |

All services restart automatically after a crash or a reboot (`restart: unless-stopped`).

**Add a user / reset a password / manage API keys:** use the admin pages in the portal. A reset password forces a change at the next use.

**Certificate renewal.** PKI certificates expire and do not renew themselves. Put a calendar reminder a few weeks before expiry. To renew: replace `certs/fullchain.pem` and `certs/privkey.pem`, then `dc restart nginx`. Check what you have with `openssl x509 -in certs/fullchain.pem -noout -enddate`.

## 4. Backups

`scripts/backup.sh` writes one archive with a PostgreSQL dump **and** the uploaded files (the two must be restored together), plus checksums.

```bash
export BACKUP_PASSPHRASE='a long passphrase kept in the team password manager'
scripts/backup.sh /srv/portal-backups          # -> portal-backup-YYYYMMDD-HHMMSS.tar.gz.enc
```

- With `BACKUP_PASSPHRASE` set the archive is encrypted (AES-256). **Without the passphrase the backup is unreadable**, so store it separately from the backups. Without it the script still works but warns that the archive is not encrypted.
- Backups contain confidential findings: keep them on org-controlled storage (DEPLOYMENT.md §6), never on a consumer cloud.
- `KEEP_DAYS` (default 14) deletes older backups from the target folder; `0` keeps everything.
- Schedule it with cron (example: every night at 02:30), logging to a file you monitor:
  ```
  30 2 * * *  cd /opt/portal && BACKUP_PASSPHRASE="$(cat /root/.portal-backup-pass)" scripts/backup.sh /srv/portal-backups >> /var/log/portal-backup.log 2>&1
  ```
- **A backup you have never restored is not a backup.** Do a restore test on a scratch machine at least once, and after any significant change.

With `STORAGE_BACKEND=s3` the files are in the object store, not in the archive: back that store up separately.

## 5. Restoring

> Destructive: this **replaces** the database and attachments of the stack it runs against. Stop and think about which server you are on.

```bash
export BACKUP_PASSPHRASE='…'                                    # for .enc files
scripts/restore.sh /srv/portal-backups/portal-backup-20261007-025930.tar.gz.enc --yes
```

The script verifies the checksums first (a corrupted backup is refused before anything is changed), stops the API, recreates the database from the dump, restores the files, and starts the API again. Afterwards run `dc run --rm api alembic upgrade head` if the backup is older than the running release, then log in and spot-check.

Disaster recovery on a new machine: do sections 1.1–1.4 (code, `.env.production` **with the same `JWT_SECRET` if you want existing sessions to survive**, certificate, build), `dc up -d db`, then restore, then `dc up -d`.

## 6. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `api` keeps restarting, log says *Unsafe production configuration* | `JWT_SECRET` missing, the dev value, or shorter than 32 characters |
| Browser says the connection is not private | Certificate missing the hostname in its **SAN**, expired, or chain not included in `fullchain.pem` |
| nginx will not start, *cannot load certificate* | `certs/fullchain.pem` / `privkey.pem` missing or not readable; mismatched pair |
| `502 Bad Gateway` right after an update | api still starting or migrations pending: `dc logs api`, then `dc run --rm api alembic upgrade head` |
| Uploads fail with `413` | file over 50 MB (app limit) or over 100 MB (proxy limit) |
| Report frozen with **Falha no envio** | email delivery failed — the error is shown on the report; fix `SMTP_*` / `DISPATCH_TO`, then **Tentar novamente**. Nothing is re-issued: the VULN ids are already assigned |
| Audit log shows the same IP for everyone | requests are not coming through the nginx container (bypassing the proxy) |
| Someone left a report locked | the lock frees itself after 10 minutes of inactivity; an admin can also force-release it on the report page |
