#!/usr/bin/env bash
# Back up the portal: PostgreSQL dump + uploaded attachments, in one archive.
#
#   scripts/backup.sh [output_dir]
#
# Environment (all optional):
#   COMPOSE_CMD        how to call compose.
#                      default: docker compose -f docker-compose.prod.yml --env-file .env.production
#   BACKUP_PASSPHRASE  if set, the archive is encrypted with AES-256 (openssl, PBKDF2).
#                      Keep the passphrase somewhere safe: without it the backup is unreadable.
#   KEEP_DAYS          delete backups in output_dir older than this many days (default 14; 0 = keep all)
#
# Backups contain confidential findings: store them on org-controlled infrastructure
# (docs/DEPLOYMENT.md §6), never on a public/consumer cloud, and encrypt them.
set -euo pipefail

COMPOSE_CMD="${COMPOSE_CMD:-docker compose -f docker-compose.prod.yml --env-file .env.production}"
OUT_DIR="${1:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
NAME="portal-backup-$STAMP"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Docker needs host-style paths for bind mounts; under Git Bash on Windows that means
# converting /tmp/... to C:\... (a no-op on Linux/macOS).
hostpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi; }

mkdir -p "$OUT_DIR"
mkdir -p "$WORK/$NAME"

echo "[1/3] Dumping the database ..."
# Run pg_dump INSIDE the db container, so no client tools are needed on the host.
$COMPOSE_CMD exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$WORK/$NAME/db.dump"
[ -s "$WORK/$NAME/db.dump" ] || { echo "ERROR: the database dump is empty" >&2; exit 1; }

echo "[2/3] Archiving the attachments ..."
API_CID="$($COMPOSE_CMD ps -q api)"
[ -n "$API_CID" ] || { echo "ERROR: the api container was not found (is the stack up?)" >&2; exit 1; }
# Reuse the api container's volumes (read-only) so the volume name does not matter.
MSYS_NO_PATHCONV=1 docker run --rm --volumes-from "$API_CID:ro" -v "$(hostpath "$WORK/$NAME"):/out" alpine \
  sh -c 'mkdir -p /data/attachments && tar czf /out/attachments.tar.gz -C /data attachments'
[ -s "$WORK/$NAME/attachments.tar.gz" ] || { echo "ERROR: the attachments archive was not created" >&2; exit 1; }

echo "[3/3] Packing ..."
( cd "$WORK/$NAME" && sha256sum db.dump attachments.tar.gz > SHA256SUMS )
tar czf "$WORK/$NAME.tar.gz" -C "$WORK" "$NAME"

if [ -n "${BACKUP_PASSPHRASE:-}" ]; then
  FINAL="$OUT_DIR/$NAME.tar.gz.enc"
  openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASSPHRASE < "$WORK/$NAME.tar.gz" > "$FINAL"
else
  FINAL="$OUT_DIR/$NAME.tar.gz"
  cp "$WORK/$NAME.tar.gz" "$FINAL"
  echo "WARNING: BACKUP_PASSPHRASE is not set, so this backup is NOT encrypted." >&2
fi

if [ "$KEEP_DAYS" -gt 0 ]; then
  find "$OUT_DIR" -maxdepth 1 -name 'portal-backup-*' -type f -mtime +"$KEEP_DAYS" -print -delete | sed 's/^/pruned old backup: /'
fi

echo "OK: $FINAL ($(du -h "$FINAL" | cut -f1))"
