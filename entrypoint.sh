#!/bin/sh

echo "Executando migrações..."
python manage.py migrate

echo "Pulando collectstatic (desenvolvimento)..."
# python manage.py collectstatic --noinput

echo "Iniciando Gunicorn..."
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --log-level=info --timeout 300

# Nota: Celery worker e beat agora rodam em containers dedicados
# Veja docker-compose.yml: serviços 'celery' e 'celery_beat'