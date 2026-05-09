#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Starting default Celery worker..."
celery -A config worker -l info -Q transcoding -n worker.transcoding@%h