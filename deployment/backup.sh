#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${DATABASE_URL:?DATABASE_URL must be configured}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/sdo-sulu}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
MEDIA_ROOT="${MEDIA_ROOT:-/srv/sdo-sulu/media}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="${BACKUP_ROOT}/${STAMP}"

install -d -m 0700 "${TARGET}"
pg_dump --format=custom --no-owner --file="${TARGET}/database.dump" "${DATABASE_URL}"
tar --create --gzip --file="${TARGET}/media.tar.gz" --directory="${MEDIA_ROOT}" .
sha256sum "${TARGET}/database.dump" "${TARGET}/media.tar.gz" > "${TARGET}/SHA256SUMS"

find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -mtime "+${RETENTION_DAYS}" -exec rm -rf -- {} +
echo "Backup completed: ${TARGET}"
