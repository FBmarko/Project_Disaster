# ==============================================================================
# AFET360 Frontend & Web Server — Production Multi-Stage Dockerfile
# Stage 1: Build React/Vite SPA with Node 22
# Stage 2: Serve static SPA & reverse-proxy API via Caddy 2.9
# ==============================================================================

# --- Stage 1: Build static assets ---
FROM node:22-bookworm-slim AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./

# Clean dependency installation
RUN npm ci

# Copy frontend source code and configuration
COPY . .

# Compile TypeScript and build static SPA bundle into dist/
RUN npm run build


# --- Stage 2: Caddy production web server ---
FROM caddy:2.9-alpine

# Copy custom Caddy configuration
COPY Caddyfile /etc/caddy/Caddyfile

# Copy compiled static assets from builder stage to standard Caddy webroot
COPY --from=builder /app/dist /usr/share/caddy

# Expose standard HTTP and HTTPS ports
EXPOSE 80 443

# Run Caddy using the custom Caddyfile
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
