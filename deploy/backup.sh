#!/usr/bin/env bash
# Nocny backup bazy: pg_dump -> gzip -> szyfrowanie AES-256 -> Backblaze B2.
# Uruchamiany z crona hosta (RUNBOOK). Wymaga w /srv/jafastage/deploy/.env:
#   BACKUP_PASSPHRASE, B2_KEY_ID, B2_APP_KEY, B2_BUCKET
set -euo pipefail
cd "$(dirname "$0")"
source .env
STAMP=$(date +%Y%m%d-%H%M)
FILE="/tmp/jafastage-${STAMP}.sql.gz.enc"
docker compose exec -T db pg_dump -U jafa jafastage | gzip \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass "pass:${BACKUP_PASSPHRASE}" \
  > "$FILE"
# upload do B2 (S3-compatible endpoint)
docker run --rm -v /tmp:/tmp amazon/aws-cli \
  --endpoint-url "https://s3.eu-central-003.backblazeb2.com" \
  s3 cp "$FILE" "s3://${B2_BUCKET}/db/" \
  --region eu-central-003 2>/dev/null || {
    AWS_ACCESS_KEY_ID="$B2_KEY_ID" AWS_SECRET_ACCESS_KEY="$B2_APP_KEY" \
    docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -v /tmp:/tmp \
      amazon/aws-cli --endpoint-url "https://s3.eu-central-003.backblazeb2.com" \
      s3 cp "$FILE" "s3://${B2_BUCKET}/db/"; }
rm -f "$FILE"
# lokalnie trzymaj 7 ostatnich (na wypadek problemów z B2)
mkdir -p /srv/backups
docker compose exec -T db pg_dump -U jafa jafastage | gzip \
  > "/srv/backups/jafastage-${STAMP}.sql.gz"
ls -t /srv/backups/*.sql.gz | tail -n +8 | xargs -r rm
