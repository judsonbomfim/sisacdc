#!/bin/sh

set -eu

echo "Criando diretório de logs..."
mkdir -p /djangoweb/logs
touch /djangoweb/logs/django.log
touch /djangoweb/logs/celery.log
touch /djangoweb/logs/api_calls.log
touch /djangoweb/logs/performance.log

if [ "${MIGRATE_ON_STARTUP:-true}" = "true" ]; then
    echo "Executando migrações..."
    python manage.py migrate --noinput
else
    echo "MIGRATE_ON_STARTUP=false: migrações ignoradas no startup"
fi

if [ "${COLLECTSTATIC_ON_STARTUP:-false}" = "true" ]; then
    echo "Executando collectstatic..."
    python manage.py collectstatic --noinput
else
    echo "COLLECTSTATIC_ON_STARTUP=false: collectstatic ignorado no startup"
fi

echo "Sincronizando documentação com S3..."
python scripts/upload_docs_s3.py || echo "Aviso: upload da documentação falhou (continuando inicialização)"

WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-90}"
GUNICORN_MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-300}"
GUNICORN_MAX_REQUESTS_JITTER="${GUNICORN_MAX_REQUESTS_JITTER:-30}"

echo "Iniciando Gunicorn..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WEB_CONCURRENCY" \
    --threads "$GUNICORN_THREADS" \
    --worker-class gthread \
    --timeout "$GUNICORN_TIMEOUT" \
    --graceful-timeout 30 \
    --max-requests "$GUNICORN_MAX_REQUESTS" \
    --max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER" \
    --log-level=info \
    --capture-output \
    --access-logfile - \
    --error-logfile -

# Nota: Celery worker e beat agora rodam em containers dedicados
# Veja docker-compose.yml: serviços 'celery' e 'celery_beat'