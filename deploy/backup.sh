#!/usr/bin/env bash
# Nocny backup bazy: pg_dump -> gzip, 7 ostatnich kopii lokalnie w /srv/backups.
# Jeśli w /srv/jafastage/deploy/.env są dane Backblaze B2
# (B2_KEY_ID, B2_APP_KEY, B2_BUCKET), kopia idzie też poza serwer,
# zaszyfrowana AES-256 hasłem BACKUP_PASSPHRASE. Bez B2 działa tylko lokalnie.
# Uruchamiany z crona hosta (RUNBOOK).
set -euo pipefail
cd "$(dirname "$0")"
set -a; source .env; set +a
STAMP=$(date +%Y%m%d-%H%M)
mkdir -p /srv/backups
LOCAL="/srv/backups/jafastage-${STAMP}.sql.gz"
docker compose exec -T db pg_dump -U jafa jafastage | gzip > "$LOCAL"
echo "$(date -Is) lokalnie: $LOCAL ($(du -h "$LOCAL" | cut -f1))"

if [ -n "${B2_KEY_ID:-}" ] && [ -n "${B2_APP_KEY:-}" ] && [ -n "${B2_BUCKET:-}" ]; then
    ENC="/tmp/jafastage-${STAMP}.sql.gz.enc"
    openssl enc -aes-256-cbc -pbkdf2 -salt -pass "pass:${BACKUP_PASSPHRASE}" -in "$LOCAL" -out "$ENC"
    AWS_ACCESS_KEY_ID="$B2_KEY_ID" AWS_SECRET_ACCESS_KEY="$B2_APP_KEY" \
        docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -v /tmp:/tmp \
        amazon/aws-cli --endpoint-url "https://s3.eu-central-003.backblazeb2.com" \
        s3 cp "$ENC" "s3://${B2_BUCKET}/db/" --only-show-errors
    rm -f "$ENC"
    echo "$(date -Is) B2: wyslano do ${B2_BUCKET}/db/"
fi

# lokalnie trzymaj 7 ostatnich
ls -t /srv/backups/*.sql.gz | tail -n +8 | xargs -r rm
