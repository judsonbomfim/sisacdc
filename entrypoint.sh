#!/bin/sh

echo "Executando migrações..."
python manage.py migrate

echo "Pulando collectstatic (desenvolvimento)..."
# python manage.py collectstatic --noinput

echo "Iniciando Gunicorn..."
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --log-level=info &

echo "Iniciando Celery Worker e Beat..."
celery -A core worker -B --loglevel=info &

echo "Serviços iniciados. Aguardando..."
wait