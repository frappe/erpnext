# ==============================
# 1️⃣  Base image
# ==============================
FROM python:3.10-slim

# ==============================
# 2️⃣  Environment variables
# ==============================
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    FRAPPE_ENV=production \
    TZ=UTC

# ==============================
# 3️⃣  System dependencies
# ==============================
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    mariadb-client \
    libffi-dev \
    libssl-dev \
    libmariadb-dev \
    libmariadb-dev-compat \
    python3-dev \
    xfonts-base \
    xfonts-75dpi \
    fontconfig \
    && apt-get install -y --no-install-recommends \
       wkhtmltopdf \
       || (echo "⚠️ wkhtmltopdf not in repo, installing from source..." \
       && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb \
       && apt-get install -y ./wkhtmltox_0.12.6-1.buster_amd64.deb) \
    && rm -rf /var/lib/apt/lists/*

# ==============================
# 4️⃣  Create working directory
# ==============================
WORKDIR /app

# ==============================
# 5️⃣  Copy project files
# ==============================
COPY . /app

# ==============================
# 6️⃣  Install Python dependencies
# ==============================
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt --no-cache-dir \
    && pip install frappe-bench gunicorn

# ==============================
# 7️⃣  Set environment for Frappe
# ==============================
ENV SITE_NAME=${SITE_NAME:-site1.local} \
    FRAPPE_DB_HOST=${MYSQLHOST:-127.0.0.1} \
    FRAPPE_DB_PORT=${MYSQLPORT:-3306} \
    FRAPPE_DB_USER=${MYSQLUSER:-root} \
    FRAPPE_DB_PASSWORD=${MYSQLPASSWORD:-password} \
    FRAPPE_REDIS_CACHE=${FRAPPE_REDIS_CACHE:-redis://localhost:6379} \
    FRAPPE_REDIS_QUEUE=${FRAPPE_REDIS_QUEUE:-redis://localhost:6380} \
    PORT=${PORT:-8000}

# ==============================
# 8️⃣  Expose port
# ==============================
EXPOSE 8000

# ==============================
# 9️⃣  Run migrations and start app
# ==============================
CMD bash -c "\
    echo '🚀 Starting Frappe in Production Mode...' && \
    echo 'Checking Database Connection...' && \
    until mariadb -h $FRAPPE_DB_HOST -P $FRAPPE_DB_PORT -u$FRAPPE_DB_USER -p$FRAPPE_DB_PASSWORD -e 'SELECT 1;' >/dev/null 2>&1; do \
        echo '⏳ Waiting for DB...'; sleep 3; \
    done && \
    echo '✅ Database Connected!' && \
    echo '🔧 Running Bench Setup...' && \
    python3 -m frappe.utils.bench_helper make-default-site --site $SITE_NAME || true && \
    echo '🔥 Starting Gunicorn...' && \
    gunicorn --bind 0.0.0.0:${PORT} --workers 4 --timeout 120 wsgi:application"
