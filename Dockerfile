# ========= مرحلة البناء =========
FROM python:3.11-slim AS build

WORKDIR /app

# تثبيت أدوات البناء المطلوبة لتجميع mysqlclient
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libmariadb-dev \
    libmariadb-dev-compat \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات المشروع
COPY . .

# تثبيت بايثون باقات (بدون كاش)
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt --no-cache-dir


# ========= مرحلة التشغيل =========
FROM python:3.11-slim

WORKDIR /app

# تثبيت الحزم الأساسية لتشغيل Frappe و wkhtmltopdf
RUN apt-get update && apt-get install -y \
    mariadb-client \
    libmariadb-dev-compat \
    fontconfig \
    xfonts-75dpi \
    xfonts-base \
    wget \
    && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb \
    && apt-get install -y ./wkhtmltox_0.12.6-1.buster_amd64.deb \
    && rm -rf /var/lib/apt/lists/* wkhtmltox_0.12.6-1.buster_amd64.deb

# نسخ الملفات المثبّتة من مرحلة البناء
COPY --from=build /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=build /usr/local/bin /usr/local/bin
COPY . .

# تعريف متغيرات البيئة
ENV PYTHONUNBUFFERED=1 \
    FRAPPE_ENV=production \
    SITE_NAME=site1.local \
    PORT=8000

# فتح المنفذ 8000
EXPOSE 8000

# تشغيل Gunicorn مع WSGI
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:application"]
