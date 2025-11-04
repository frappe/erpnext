# ============================================================================
# ERPNext Kanaan ERP - Production Dockerfile
# ============================================================================
# This Dockerfile implements a proper Frappe bench setup for production

FROM python:3.10-slim

WORKDIR /app

# ============================================================================
# STAGE 1: System Dependencies
# ============================================================================
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

# ============================================================================
# STAGE 2: Copy Project Source Code
# ============================================================================
# Copy the entire repository (which contains frappe/erpnext source)
COPY . /app/

# ============================================================================
# STAGE 3: Python Environment Setup
# ============================================================================
# Upgrade pip, setuptools, wheel
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies (NOT frappe/erpnext - those are in the repo)
# Remove frappe and erpnext from requirements.txt since they're in /app
RUN python -m pip install --no-cache-dir \
    PyMySQL>=1.0.0 \
    psycopg2-binary>=2.9.0 \
    redis>=4.0.0 \
    rq>=1.11.0 \
    gunicorn>=20.1.0 \
    Werkzeug>=2.2.0 \
    gevent>=21.0.0 \
    python-dateutil>=2.8.2 \
    requests>=2.28.0 \
    urllib3>=1.26.0 \
    Unidecode>=1.4.0 \
    barcodenumber>=0.5.0 \
    rapidfuzz>=3.0.0 \
    holidays>=0.75 \
    alembic>=1.10.0 \
    sqlalchemy>=1.4.0 \
    secure-smtplib>=0.1.1 \
    weasyprint>=59.0 \
    pypdf>=3.15.0 \
    python-bidi>=0.4.2 \
    openpyxl>=3.10.0 \
    xlrd>=2.0.0 \
    click>=8.0.0 \
    pydantic>=1.10.0 \
    python-dotenv>=0.21.0 \
    python-json-logger>=2.0.0

# Verify gunicorn is installed
RUN python -m pip list | grep gunicorn && echo "✅ Gunicorn installed successfully"

# ============================================================================
# STAGE 4: Create Required Directories
# ============================================================================
RUN mkdir -p /app/logs \
    && mkdir -p /app/private/files \
    && mkdir -p /app/sites \
    && mkdir -p /app/public/files \
    && chmod -R 755 /app

# ============================================================================
# STAGE 5: Node Dependencies
# ============================================================================
RUN cd /app && npm ci --omit=dev 2>/dev/null || npm install || true

# ============================================================================
# STAGE 6: Configuration Files
# ============================================================================
# Copy nginx configuration if exists
RUN if [ -f /app/nginx.conf ]; then cp /app/nginx.conf /etc/nginx/nginx.conf; fi

# Copy supervisor configuration if exists
RUN if [ -f /app/supervisor.conf ]; then cp /app/supervisor.conf /etc/supervisor/conf.d/erpnext.conf; fi

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# ============================================================================
# STAGE 7: Environment Variables
# ============================================================================
ENV FRAPPE_BENCH_PATH=/app \
    PYTHONPATH=/app:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production \
    FRAPPE_ENV=production

# ============================================================================
# STAGE 8: Health Check
# ============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || curl -f http://localhost:8080/api/health || exit 1

# ============================================================================
# STAGE 9: Expose Ports
# ============================================================================
# Port 8000: Gunicorn (API)
# Port 8080: Nginx (Frontend)
# Port 3000: Node/WebSocket
EXPOSE 8000 8080 3000

# ============================================================================
# STAGE 10: Entry Point
# ============================================================================
# docker-entrypoint.sh will:
# 1. Wait for MariaDB and Redis
# 2. Initialize site if needed
# 3. Start gunicorn with wsgi:application
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "wsgi:application"]