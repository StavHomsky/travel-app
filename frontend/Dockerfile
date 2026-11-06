# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Travel Locations frontend - multi-stage build
#
#   deps     npm ci (cached until package-lock.json changes)
#   test     ESLint + Vitest   (docker build --target test .)
#   build    vite build -> static files in /src/dist
#   runtime  nginx (non-root) serving only the static files - no Node.js,
#            no node_modules, no source code in the final image
# ---------------------------------------------------------------------------
ARG NODE_IMAGE=node:24-alpine
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.30-alpine

# ---------- deps ----------
FROM ${NODE_IMAGE} AS deps
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ---------- test ----------
FROM deps AS test
COPY . .
RUN npm run lint && npm test

# ---------- build ----------
FROM deps AS build
COPY . .
RUN npm run build

# ---------- runtime ----------
FROM ${NGINX_IMAGE} AS runtime
ARG APP_VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="travel-frontend" \
      org.opencontainers.image.description="Travel Locations web UI (React + nginx)" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"
USER root                                                                
RUN apk upgrade --no-cache                                                  
USER 101

# Where nginx forwards /api requests (overridable at runtime).
ENV BACKEND_URL=http://backend:5000

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /src/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
