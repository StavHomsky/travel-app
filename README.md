# Travel App

A web app for tracking places you have visited and places on your wishlist.
Adding a place looks up its coordinates and pulls a photo and description
from Wikipedia. The dashboard shows charts and a world map; wishlist places
link to TripAdvisor.

Infrastructure (Helm chart, Jenkins pipeline, monitoring, Terraform) lives in
the companion repository [travel-devops](https://github.com/StavHomsky/travel-devops).

## Stack

| Part | Technology |
|---|---|
| Backend | Python 3, Flask, Flask-RESTful, SQLAlchemy, Alembic migrations, Gunicorn |
| Database | PostgreSQL 16 |
| Frontend | React + Vite, Leaflet map, served by Nginx |
| Tests | pytest + flake8 (backend), Vitest + ESLint (frontend) |

## Project structure

```
backend/
  app/
    api.py          HTTP layer: routes, request parsing, error responses
    services.py     business logic (the API only calls into this)
    validation.py   input validation rules
    models.py       SQLAlchemy model
    enrichment.py   geocoding + Wikipedia lookup
    health.py       /healthz (liveness) and /readyz (checks the database)
    metrics.py      Prometheus metrics at /metrics
  migrations/       Alembic database migrations
  tests/            pytest suite
  Dockerfile        multi-stage: builder -> test -> runtime (non-root)
frontend/
  src/              React pages and components
  nginx/            Nginx config: serves the SPA, proxies /api to the backend
  Dockerfile        multi-stage: deps -> test -> build -> nginx runtime (non-root)
docker-compose.yml  local stack: db + backend + frontend
```

## API

Base path `/api/v1`. All bodies are JSON. Errors come back as JSON with a
matching status code (`400`, `404`, `409`, `422`).

| Method | Path | Description |
|---|---|---|
| GET | `/locations` | List, with filters `?q=`, `country`, `type`, `visited`, `sort`, `order` |
| POST | `/locations` | Create a location |
| GET | `/locations/<id>` | Get one location |
| PUT / PATCH | `/locations/<id>` | Replace / partially update |
| DELETE | `/locations/<id>` | Delete |
| POST | `/locations/<id>/enrich` | Re-fetch map position and Wikipedia data |
| POST | `/locations/enrich-missing` | Enrich places that have no data yet |
| GET | `/stats` | Totals for the dashboard |
| POST | `/locations/import` | Import a JSON array or uploaded file |
| GET | `/locations/export` | Export all locations |

Outside `/api/v1`: `/healthz`, `/readyz`, `/metrics`.

## Run locally

Requires Docker.

```bash
cp .env.example .env     # then set real values for POSTGRES_PASSWORD and SECRET_KEY
docker compose up --build
```

- UI: http://localhost:8080
- API: http://localhost:5001/api/v1/locations

The backend runs database migrations on start and seeds sample places.

## Tests

Tests run inside the Docker build, so no local Python or Node is needed:

```bash
docker build --target test backend    # flake8 + pytest with coverage
docker build --target test frontend   # ESLint + Vitest
```

A failing test fails the build. The Jenkins pipeline runs the same targets.

## Configuration

| Variable | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | Database password (secret) |
| `SECRET_KEY` | Flask secret key (secret) |
| `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER` | Database connection |
| `LOG_LEVEL` | Log level, default `INFO` |
| `RUN_MIGRATIONS`, `SEED_DB`, `ENRICH_DB` | Startup behaviour |

Secrets come from `.env`, which is git-ignored. Only `.env.example` with
placeholder values is committed.

## Deployment

Images are built, scanned and deployed to Kubernetes by the Jenkins pipeline
in [travel-devops](https://github.com/StavHomsky/travel-devops). See its
README and `docs/deployment.md`.
