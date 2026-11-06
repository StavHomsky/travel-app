# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Travel Locations API - multi-stage build
#
#   builder    installs dependencies into a virtualenv
#   test       builder + dev tools + source; runs flake8 and pytest
#              (docker build --target test .)
#   prod-deps  the virtualenv without pip (not needed at runtime)
#   runtime    slim image: only the virtualenv + app code, non-root user
#              (default target)
# ---------------------------------------------------------------------------
ARG PYTHON_IMAGE=python:3.12-slim

# ---------- builder ----------
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Copy only requirements first: this layer is cached until they change,
# so editing app code does not reinstall every package.
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# ---------- test ----------
FROM builder AS test
WORKDIR /src
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY . .
RUN flake8 . && pytest -q -p no:cacheprovider --cov=app --cov-report=xml:/reports/coverage.xml --junitxml=/reports/junit.xml

# ---------- prod-deps ----------
FROM builder AS prod-deps
RUN pip uninstall -y pip

# ---------- runtime ----------
FROM ${PYTHON_IMAGE} AS runtime
ARG APP_VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="travel-backend" \
      org.opencontainers.image.description="Travel Locations REST API (Flask)" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_VERSION=${APP_VERSION} \
    FLASK_APP=wsgi:app

# Apply OS security patches and create an unprivileged user.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=prod-deps /opt/venv /opt/venv
# Code is owned by root and only readable by the app user: a compromised
# process cannot modify it.
COPY app ./app
COPY migrations ./migrations
COPY seed ./seed
COPY wsgi.py gunicorn.conf.py entrypoint.sh ./

USER 10001
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=2)"

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
