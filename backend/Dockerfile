ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends curl postgresql-client openssl ca-certificates && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN addgroup --system --gid 10001 app && adduser --system --uid 10001 --ingroup app app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY app ./app
COPY worker.py ./worker.py
COPY scripts/staging-e2e.sh ./staging-e2e.sh
COPY entrypoint.sh ./entrypoint.sh
RUN chmod 0555 ./entrypoint.sh ./staging-e2e.sh
USER 10001:10001
ENTRYPOINT ["./entrypoint.sh"]
