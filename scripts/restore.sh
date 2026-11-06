#!/usr/bin/env bash
# Restore a backup made by scripts/backup.sh. DESTRUCTIVE: it REPLACES the
# database and the attachments of the target stack.
#
#   scripts/restore.sh <backup-file> --yes
#
# Environment (optional): COMPOSE_CMD (as in backup.sh) and BACKUP_PASSPHRASE
# (required when the file ends in .enc).
set -euo pipefail

FILE="${1:-}"
[ -f "$FILE" ] || { echo "usage: $0 <backup-file> --yes" >&2; exit 2; }
[ "${2:-}" = "--yes" ] || { echo "This REPLACES the database and attachments of the target stack. Re-run with --yes to confirm." >&2; exit 2; }

COMPOSE_CMD="${COMPOSE_CMD:-docker compose -f docker-compose.prod.yml --env-file .env.production}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Docker needs host-style paths for bind mounts; under Git Bash on Windows that means
# converting /tmp/... to C:\... (a no-op on Linux/macOS).
hostpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi; }

echo "[1/5] Reading the backup ..."
ARCHIVE="$FILE"
if [[ "$FILE" == *.enc ]]; then
  [ -n "${BACKUP_PASSPHRASE:-}" ] || { echo "ERROR: set BACKUP_PASSPHRASE to open an encrypted backup" >&2; exit 2; }
  openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE < "$FILE" > "$WORK/backup.tar.gz" \
    || { echo "ERROR: could not decrypt (wrong passphrase?)" >&2; exit 1; }
  ARCHIVE="$WORK/backup.tar.gz"
fi
tar xzf "$ARCHIVE" -C "$WORK"
DIR="$(find "$WORK" -maxdepth 1 -type d -name 'portal-backup-*' | head -1)"
[ -n "$DIR" ] || { echo "ERROR: not a portal backup" >&2; exit 1; }
( cd "$DIR" && sha256sum -c SHA256SUMS ) || { echo "ERROR: the backup is corrupted (checksum mismatch)" >&2; exit 1; }

echo "[2/5] Stopping the API (no writes during the restore) ..."
$COMPOSE_CMD stop api

echo "[3/5] Restoring the database ..."
# Recreate the database from scratch, then load the dump into it.
$COMPOSE_CMD exec -T db sh -c '
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
       -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\" WITH (FORCE)" \
       -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\""'
$COMPOSE_CMD exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error' < "$DIR/db.dump"

echo "[4/5] Restoring the attachments ..."
API_CID="$($COMPOSE_CMD ps -aq api)"
MSYS_NO_PATHCONV=1 docker run --rm --volumes-from "$API_CID" -v "$(hostpath "$DIR"):/in:ro" alpine \
  sh -c 'mkdir -p /data/attachments && rm -rf /data/attachments/* && tar xzf /in/attachments.tar.gz -C /data && chown -R 10001 /data/attachments'

echo "[5/5] Starting the API ..."
$COMPOSE_CMD start api
echo "OK: restored from $FILE"
