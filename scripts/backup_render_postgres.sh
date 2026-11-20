#!/usr/bin/env bash
# Create a private, verified PostgreSQL custom-format backup.
# Required: DATABASE_URL (use Render's EXTERNAL database URL with sslmode=require).
# Optional: BACKUP_DIR (defaults to ./backups).
set -euo pipefail
umask 077

: "${DATABASE_URL:?Set DATABASE_URL in your shell; never paste it into this script or commit it.}"
command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump is required (install PostgreSQL client tools)." >&2; exit 1; }
command -v pg_restore >/dev/null 2>&1 || { echo "pg_restore is required (install PostgreSQL client tools)." >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required." >&2; exit 1; }

case "$DATABASE_URL" in
  postgres://*|postgresql://*) ;;
  *) echo "DATABASE_URL must be a PostgreSQL connection URL." >&2; exit 1 ;;
esac
case "$DATABASE_URL" in
  *sslmode=*) ;;
  *) echo "Use Render's external URL with sslmode=require." >&2; exit 1 ;;
esac

backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$backup_dir/ai-export-sales-${stamp}.dump"
checksum="$archive.sha256"

if [ -e "$archive" ] || [ -e "$checksum" ]; then
  echo "Refusing to overwrite an existing backup." >&2
  exit 1
fi

# Do not enable shell tracing: DATABASE_URL contains credentials.
pg_dump --dbname="$DATABASE_URL" --format=custom --no-owner --no-privileges --file="$archive"
pg_restore --list "$archive" >/dev/null
(
  cd "$backup_dir"
  sha256sum "$(basename "$archive")" > "$(basename "$checksum")"
)
chmod 600 "$archive" "$checksum"
echo "Backup created and archive structure verified: $archive"
echo "Checksum: $checksum"
echo "Copy both files to encrypted storage outside this machine before relying on this backup."
