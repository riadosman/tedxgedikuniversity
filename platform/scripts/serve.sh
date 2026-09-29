#!/bin/sh
set -eu
python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --config gunicorn.conf.py
