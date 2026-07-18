#!/usr/bin/env bash
# Синк логов в S3 (cloud.ru). Лежит на сервере рядом
# с docker-compose.yml (/opt/zheka), запускается из cron, см. PROD.md.
#
# Режимы:
#   backup_logs.sh            синк logs/ в S3 (для cron)
#   backup_logs.sh list       содержимое бакета и объём
#   backup_logs.sh lifecycle  разово применить политику ротации S3
set -euo pipefail
cd "$(dirname "$0")"

# Точечное чтение из .env: source не используем (спецсимволы),
# одинарные кавычки вокруг значения снимаем
env_get() { grep "^$1=" .env | cut -d= -f2- | sed "s/^'//;s/'$//"; }

TENANT_ID=$(env_get TENANT_ID || true)
S3_KEY_ID=$(env_get AWS_ACCESS_KEY_ID || true)
S3_SECRET=$(env_get AWS_SECRET_ACCESS_KEY || true)
S3_BUCKET=$(env_get S3_BUCKET || true)
S3_ENDPOINT=$(env_get S3_ENDPOINT || true)
S3_REGION=$(env_get S3_REGION || true)
S3_RETENTION_DAYS=$(env_get S3_RETENTION_DAYS || true)

s3_configured() {
    [ -n "$TENANT_ID" ] && [ -n "$S3_KEY_ID" ] && [ -n "$S3_SECRET" ] \
        && [ -n "$S3_BUCKET" ] && [ -n "$S3_ENDPOINT" ]
}

# aws-cli одноразовым контейнером: на хост ничего не ставим.
# Ключ cloud.ru — склейка TENANT_ID:KEY_ID
aws_s3() {
    docker run --rm \
        -v "$(pwd)/logs:/logs:ro" \
        -e AWS_ACCESS_KEY_ID="${TENANT_ID}:${S3_KEY_ID}" \
        -e AWS_SECRET_ACCESS_KEY="${S3_SECRET}" \
        amazon/aws-cli --endpoint-url "$S3_ENDPOINT" \
        --region "${S3_REGION:-ru-central-1}" "$@"
}

do_backup() {
    if ! s3_configured; then
        echo "ПРЕДУПРЕЖДЕНИЕ: S3 не настроен (TENANT_ID/AWS_*/S3_*" \
             "в .env), синк логов пропущен"
        exit 0
    fi
    # sync докидывает только новые/изменившиеся файлы
    aws_s3 s3 sync /logs "s3://${S3_BUCKET}/logs/" --quiet
    echo "Логи синхронизированы: s3://${S3_BUCKET}/logs/"
}

do_list() {
    echo "=== s3://${S3_BUCKET}/logs/ ==="
    aws_s3 s3 ls "s3://${S3_BUCKET}/logs/"
    echo "=== Всего в бакете ==="
    aws_s3 s3 ls "s3://${S3_BUCKET}/" --recursive --summarize | tail -2
}

do_lifecycle() {
    DAYS="${S3_RETENTION_DAYS:-90}"
    RULES='{"Rules":['
    RULES+='{"ID":"delete-old-logs","Status":"Enabled",'
    RULES+='"Filter":{"Prefix":"logs/"},'
    RULES+='"Expiration":{"Days":'"$DAYS"'}}]}'
    aws_s3 s3api put-bucket-lifecycle-configuration \
        --bucket "$S3_BUCKET" \
        --lifecycle-configuration "$RULES"
    echo "Политика применена: logs/* удаляются через $DAYS дней"
    aws_s3 s3api get-bucket-lifecycle-configuration --bucket "$S3_BUCKET"
}

case "${1:-backup}" in
    backup)    do_backup ;;
    list)      do_list ;;
    lifecycle) do_lifecycle ;;
    *)  echo "Использование: $0 [backup|list|lifecycle]" >&2; exit 1 ;;
esac
