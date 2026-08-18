# syntax=docker/dockerfile:1

# ---------- build ----------
FROM node:22-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite inlines these at build time, so they are build arguments rather than runtime env.
ARG VITE_API_BASE_URL=""
ARG VITE_TILE_URL=""
ARG VITE_TILE_ATTRIBUTION=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_TILE_URL=$VITE_TILE_URL \
    VITE_TILE_ATTRIBUTION=$VITE_TILE_ATTRIBUTION

RUN npm run build

# ---------- runtime ----------
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder --chown=nginx:nginx /build/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --spider -q http://127.0.0.1:8080/ || exit 1
