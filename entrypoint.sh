#!/bin/sh

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --log-level=info && celery -A core worker -B --loglevel=info && celery -A proj beat --loglevel=info