#!/bin/sh

python manage.py migrate
python manage.py collectstatic --noinput
nohup gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --log-level=info &
nohup celery -A core worker -B --loglevel=info