#!/usr/bin/env bash
set -euo pipefail

project_dir=${PROJECT_DIR:-/opt/song-blog}
backup_dir="$project_dir/backups"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)

cd "$project_dir"
mkdir -p "$backup_dir"

db_file="$backup_dir/mysql_${timestamp}.sql.gz"
media_file="$backup_dir/media_${timestamp}.tar.gz"

/usr/bin/docker compose -f compose.yaml -f compose.prod.yaml exec -T db \
  sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump -h 127.0.0.1 -u"$MYSQL_USER" --single-transaction --quick --routines --events --triggers --no-tablespaces "$MYSQL_DATABASE"' \
  | gzip -9 > "$db_file"

tar -C "$project_dir/data" -czf "$media_file" media
test -s "$db_file"
test -s "$media_file"
sha256sum "$db_file" "$media_file" > "$backup_dir/checksums_${timestamp}.sha256"

find "$backup_dir" -maxdepth 1 -type f -mtime +14 \
  \( -name 'mysql_*.sql.gz' -o -name 'media_*.tar.gz' -o -name 'checksums_*.sha256' \) \
  -delete
