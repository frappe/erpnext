# ============================================================================
# ERPNext Kanaan ERP - Production Dockerfile
# ============================================================================
# Cache-bust: 2025-11-04-11-56-08-utc-fresh-build

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    npm \
    nodejs \
    mariadb-client \
    redis-tools \
    supervisor \
    nginx \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Create required directories
RUN mkdir -p /app/logs \
    && mkdir -p /app/private/files \
    && mkdir -p /app/sites \
    && mkdir -p /app/public/files \
    && chmod -R 755 /app

# Install Python dependencies from requirements.txt
# Force fresh build - timestamp: 2025-11-04T11:56-v2
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir -r /app/requirements.txt && \
    python -m pip list | grep gunicorn

# Install Node dependencies
RUN cd /app && npm ci --omit=dev || npm install || echo "npm install completed with warnings"

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Copy configs
RUN if [ -f /app/nginx.conf ]; then cp /app/nginx.conf /etc/nginx/nginx.conf; fi && \
    if [ -f /app/supervisor.conf ]; then cp /app/supervisor.conf /etc/supervisor/conf.d/erpnext.conf; fi

# Set environment variables
ENV FRAPPE_BENCH_PATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080 || exit 1

# Expose ports
EXPOSE 8000 8080 3000

# Entry point
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "wsgi:application"]