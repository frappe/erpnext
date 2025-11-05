# =========================
# 1️⃣ Base Image
# =========================
FROM python:3.11-slim

# =========================
# 2️⃣ Environment setup
# =========================
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRAPPE_ENV=production

WORKDIR /opt/frappe

# =========================
# 3️⃣ Install system dependencies
# =========================
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    mariadb-client \
    libffi-dev \
    libssl-dev \
    libmysqlclient-dev \
    python3-dev \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# =========================
# 4️⃣ Install Node.js (for Frappe assets)
# =========================
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn

# =========================
# 5️⃣ Clone Frappe Framework
# =========================
RUN git clone --depth 1 https://github.com/frappe/frappe.git /opt/frappe

# =========================
# 6️⃣ Install Python requirements
# =========================
RUN pip install --no-cache-dir -e /opt/frappe \
    && pip install --no-cache-dir gunicorn mysqlclient redis

# =========================
# 7️⃣ Copy your app (مثل KanaanERP)
# =========================
COPY . /opt/frappe/apps/kanaanerpgaza

# =========================
# 8️⃣ Install your custom app
# =========================
RUN pip install --no-cache-dir -e /opt/frappe/apps/kanaanerpgaza

# =========================
# 9️⃣ Expose Railway port
# =========================
EXPOSE 8000

# =========================
# 🔟 Environment Variables (من Railway)
# =========================
ENV SITE_NAME=site1.local \
    FRAPPE_REDIS_CACHE=redis://localhost:6379 \
    FRAPPE_REDIS_QUEUE=redis://localhost:6379 \
    FRAPPE_DB_PASSWORD=$MYSQLPASSWORD

# =========================
# 1️⃣1️⃣ Command to run Frappe via Gunicorn
# =========================
COPY ./wsgi.py /opt/frappe/wsgi.py
COPY ./gunicorn.conf.py /opt/frappe/gunicorn.conf.py

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:application"]
