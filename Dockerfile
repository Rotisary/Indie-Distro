FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt


RUN addgroup --system django && adduser --system --ingroup django django

COPY --chown=django:django ./devops/server.sh /server.sh
RUN sed -i 's/\r$//g' /server.sh && chmod +x /server.sh

COPY --chown=django:django ./devops/celery/celery_worker.sh /celery-worker.sh
RUN sed -i 's/\r$//g' /celery-worker.sh && chmod +x /celery-worker.sh

COPY --chown=django:django ./devops/celery/celery_worker_io.sh /celery-worker-io.sh
RUN sed -i 's/\r$//g' /celery-worker-io.sh && chmod +x /celery-worker-io.sh

COPY --chown=django:django ./devops/celery/celery_worker_transcoding.sh /celery-worker-transcoding.sh
RUN sed -i 's/\r$//g' /celery-worker-transcoding.sh && chmod +x /celery-worker-transcoding.sh

COPY --chown=django:django ./devops/celery/celery_worker_packaging.sh /celery-worker-packaging.sh
RUN sed -i 's/\r$//g' /celery-worker-packaging.sh && chmod +x /celery-worker-packaging.sh

COPY --chown=django:django ./devops/celery/celery_beat.sh /celery-beat.sh
RUN sed -i 's/\r$//g' /celery-beat.sh && chmod +x /celery-beat.sh


USER django

EXPOSE 8000
