# ==============================================================================
# AFET360 Backend — Production Dockerfile
# Multi-stage / minimal slim runtime for FastAPI + PostGIS + Uvicorn
# ==============================================================================
FROM python:3.12-slim-bookworm

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create dedicated non-root application user and group (UID 10001)
RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid appuser --home-dir /app --shell /bin/false appuser

WORKDIR /app

# Upgrade pip and install build dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy project metadata for dependency resolution and layer caching
COPY --chown=appuser:appuser pyproject.toml README.md ./

# Extract dependencies directly from pyproject.toml using standard library tomllib
RUN python -c "import tomllib; reqs = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; open('/tmp/requirements.txt', 'w').write('\n'.join(reqs) + '\n')" && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy application source, migrations, and runtime geospatial reference data
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser data/ ./data/
COPY --chown=appuser:appuser docker-entrypoint.sh ./

# Install the application package metadata (without re-resolving dependencies)
RUN pip install --no-cache-dir --no-deps . && \
    chmod +x /app/docker-entrypoint.sh

# Container liveness healthcheck using Python standard library (no curl required)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; sys_exit = 0 if urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).getcode() == 200 else 1; exit(sys_exit)"

# Expose standard API service port
EXPOSE 8000

# Switch to non-root application user
USER appuser

# Startup: database readiness -> alembic upgrade head -> single-worker uvicorn
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
