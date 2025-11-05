# استخدم صورة Python خفيفة
FROM python:3.11-slim

# إعداد بيئة العمل
WORKDIR /app

# تثبيت المتطلبات الأساسية (بما في ذلك pkg-config)
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
       || (echo "⚠️ wkhtmltopdf not in repo, installing from source..." \
       && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb \
       && apt-get install -y ./wkhtmltox_0.12.6-1.buster_amd64.deb) \
    && rm -rf /var/lib/apt/lists/*

# نسخ الملفات إلى داخل الكونتينر
COPY . .

# تثبيت متطلبات المشروع
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt --no-cache-dir

# تعريف المتغيرات الخاصة بقاعدة البيانات
ENV MYSQL_DATABASE=railway \
    MYSQL_USER=root \
    MYSQL_PASSWORD=eLtJZovDmgTLoeBlFYbvzoudseKHyrFY \
    MYSQL_HOST=mainline.proxy.rlwy.net \
    MYSQL_PORT=40503

# منفذ التشغيل
EXPOSE 8000

# أمر التشغيل الافتراضي
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:application"]
