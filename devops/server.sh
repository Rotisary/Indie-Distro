#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Daphne server..."
daphne -b 0.0.0.0 -p 8000 config.asgi:application