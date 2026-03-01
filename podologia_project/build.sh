#!/usr/bin/env bash
set -o errexit

python3 -m pip install -r requirements.render.txt
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
