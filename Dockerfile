# ========= Dockerfile =========
FROM python:3.11-slim

# تثبيت المتطلبات الأساسية
RUN apt-get update && apt-get install -y \
    curl git default-mysql-client build-essential redis-server nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# تعيين مجلد العمل
WORKDIR /app

# نسخ الملفات
COPY . /app/

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# بناء واجهة ERPNext (اختياري)
RUN if [ -f package.json ]; then npm install && npm run build || true; fi

# إعداد البيئة
ENV PYTHONPATH=/app
ENV PORT=8000

# فتح المنفذ
EXPOSE 8000

# تشغيل التطبيق باستخدام Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} wsgi:application"]
