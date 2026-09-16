#!/usr/bin/env bash
set -euo pipefail

: "${RESTORE_TEST_DATABASE_URL:?Set RESTORE_TEST_DATABASE_URL to a disposable database whose name ends in _restore_test}"
case "${RESTORE_TEST_DATABASE_URL}" in
  *_restore_test|*_restore_test\?*) ;;
  *) echo "Refusing to continue: restore-test database name must end in _restore_test." >&2; exit 2 ;;
esac

BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/sdo-sulu}"
TARGET="${1:-$(find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)}"
test -d "${TARGET}"
cd "${TARGET}"
sha256sum --check SHA256SUMS

psql "${RESTORE_TEST_DATABASE_URL}" --set ON_ERROR_STOP=1 --command="DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
pg_restore --exit-on-error --no-owner --dbname="${RESTORE_TEST_DATABASE_URL}" database.dump
psql "${RESTORE_TEST_DATABASE_URL}" --set ON_ERROR_STOP=1 --command="SELECT COUNT(*) AS django_migrations FROM django_migrations;"

TEMP_MEDIA="$(mktemp -d)"
trap 'rm -rf -- "${TEMP_MEDIA}"' EXIT
tar --extract --gzip --file=media.tar.gz --directory="${TEMP_MEDIA}"
test -d "${TEMP_MEDIA}"
echo "Restore test completed successfully from ${TARGET}."
