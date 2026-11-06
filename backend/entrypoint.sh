#!/bin/sh
# Container entrypoint: optional one-off setup steps, then the real command.
# In Kubernetes these flags stay "false" - an init container / Job does the
# migrations instead, so several replicas never migrate at the same time.
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running database migrations..."
  flask db upgrade
fi

if [ "${SEED_DB:-false}" = "true" ]; then
  flask seed-db
fi

if [ "${ENRICH_DB:-false}" = "true" ]; then
  flask enrich-db --limit 20 || echo "Enrichment failed (no internet?); continuing."
fi

# exec replaces this shell, so gunicorn becomes PID 1 and receives
# SIGTERM directly when Docker/Kubernetes stops the container.
exec "$@"
