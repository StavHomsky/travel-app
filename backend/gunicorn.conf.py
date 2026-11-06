"""Gunicorn (production web server) settings, overridable with env vars."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# One worker process with several threads. Prometheus counters live in the
# process memory, so with several workers each scrape would only see one
# worker's numbers. We scale by running more pods (replicas) instead.
workers = int(os.environ.get("GUNICORN_WORKERS", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# /locations/enrich-missing can take ~20 s (1 request/second to OpenStreetMap).
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
graceful_timeout = 20  # finish in-flight requests when Kubernetes stops the pod

accesslog = None  # the app writes its own JSON access log (logging_config.py)
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
worker_tmp_dir = "/dev/shm"  # keeps working with a read-only root filesystem

# Gunicorn's runtime control socket is not needed (Kubernetes manages the
# process) and would try to write into a home directory the app user lacks.
control_socket_disable = True
