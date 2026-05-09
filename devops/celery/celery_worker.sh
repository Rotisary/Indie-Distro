#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Starting default Celery worker..."
celery -A config worker -l info -Q celery,beats,service,email-notification -n worker@%h