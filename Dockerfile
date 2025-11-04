# ============================================================================
# ERPNext Kanaan ERP - Multi-Stage Dockerfile
# ============================================================================
# Stage 1: Builder - تجميع الـ Assets و Dependencies
# ============================================================================
FROM python:3.10-slim as builder

WORKDIR /app

# تثبيت المتطلبات النظام
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    npm \
    nodejs \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/*

# تثبيت Frappe Bench
RUN pip install --no-cache-dir frappe-bench

# ============================================================================
# Stage 2: Production - الصورة النهائية
# ============================================================================
FROM python:3.10-slim

WORKDIR /app

# تثبيت المتطلبات النظام للإنتاج
RUN apt-get update && apt-get install -y --no-install-recommends \
    mariadb-client \
    redis-tools \
    git \
    curl \
    npm \
    nodejs \
    supervisor \
    nginx \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# نسخ المشروع
COPY . /app

# تثبيت Python Dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt || echo "No requirements.txt found"

# تثبيت Node Dependencies
RUN cd /app && npm ci --omit=dev 2>/dev/null || echo "npm install skipped"

# إنشاء المجلدات المطلوبة
RUN mkdir -p /app/logs \
    && mkdir -p /app/private/files \
    && mkdir -p /app/sites \
    && chmod -R 755 /app

# نسخ Nginx Config
COPY nginx.conf /etc/nginx/nginx.conf || true

# نسخ Supervisor Config
COPY supervisor.conf /etc/supervisor/conf.d/erpnext.conf || true

# نسخ Docker Entry Point Script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# تعيين متغيرات البيئة الافتراضية
ENV FRAPPE_BENCH_PATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production

# الحد الأدنى من الأوامر الصحية
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080 || exit 1

# إذاعة المنافذ
EXPOSE 8000 8080 3000

# نقطة دخول التطبيق
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "wsgi:application"]