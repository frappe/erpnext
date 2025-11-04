# ============================================================================
# ERPNext Kanaan ERP - Production Dockerfile
# ============================================================================
# This Dockerfile implements a proper Frappe bench setup for production
# Version: 2.0.3 - Frappe v15 branch from GitHub (stable for ERPNext v15.85.1)
# Build: Corrected branch name to 'v15' (existing Frappe release branch)

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
# Copy the entire repository (which contains ERPNext source and requirements.txt)
COPY . /app/

# ============================================================================
# STAGE 3: Python Environment Setup
# ============================================================================
# Upgrade pip, setuptools, wheel
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Clone Frappe Framework from GitHub
# Using main branch which contains the latest stable version
RUN git clone --branch v15 --depth 1 https://github.com/frappe/frappe.git /opt/frappe

# Install Frappe framework from the cloned repository (development mode)
# This makes it importable as 'frappe' while keeping the source code accessible
RUN cd /opt/frappe && python -m pip install --no-cache-dir -e .

# Install Python dependencies from requirements.txt
# This includes all other dependencies required for production deployment
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

# Verify critical packages are installed
RUN python -c "import frappe; print(f'✅ Frappe {frappe.__version__} installed successfully')" && \
    python -c "import gunicorn; print('✅ Gunicorn installed successfully')"

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
    PYTHONPATH=/app:/opt/frappe:$PYTHONPATH \
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