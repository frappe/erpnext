# ========= مرحلة البناء =========
FROM python:3.11-slim AS builder

# تعيين مجلد العمل
WORKDIR /app

# تثبيت المتطلبات الأساسية
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
    pkg-config \
    xfonts-base \
    xfonts-75dpi \
    fontconfig \
    && apt-get install -y --no-install-recommends \
       wkhtmltopdf \
       || (echo "⚠️ Installing wkhtmltopdf from source..." \
       && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb \
       && apt-get install -y ./wkhtmltox_0.12.6-1.buster_amd64.deb) \
    && rm -rf /var/lib/apt/lists/*

# نسخ الملفات إلى الحاوية
COPY . .

# تحديث pip وتثبيت متطلبات المشروع
RUN pip install --upgrade pip setuptools wheel \
    && pip install frappe-bench gunicorn mysqlclient --no-cache-dir \
    && pip install -r requirements.txt --no-cache-dir || true

# ========= مرحلة التشغيل =========
FROM python:3.11-slim

WORKDIR /app

# تثبيت المتطلبات الضرورية فقط للتشغيل (أخف حجمًا)
RUN apt-get update && apt-get install -y \
    mariadb-client \
    libmariadb-dev-compat \
    wkhtmltopdf \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# نسخ الملفات من مرحلة البناء
COPY --from=builder /usr/local /usr/local
COPY . .

# إعداد متغيرات قاعدة البيانات (Railway)
ENV MYSQL_DATABASE=railway \
    MYSQL_USER=root \
    MYSQL_PASSWORD=eLtJZovDmgTLoeBlFYbvzoudseKHyrFY \
    MYSQL_HOST=mainline.proxy.rlwy.net \
    MYSQL_PORT=40503 \
    FRAPPE_SITE_NAME=kanaan.localhost \
    TZ=Asia/Tehran

# فتح المنفذ 8000
EXPOSE 8000

# أمر التشغيل (تشغيل Frappe عبر bench أو Gunicorn)
CMD ["bash", "-c", "bench start || gunicorn --bind 0.0.0.0:8000 wsgi:application"]
