#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Starting Celery beat..."
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --max-interval 10