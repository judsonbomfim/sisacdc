#!/bin/sh

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
celery -A core worker -B --loglevel=info
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 45 --log-level=info