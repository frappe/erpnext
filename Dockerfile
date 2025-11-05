# ---- Base image ----
FROM python:3.11-slim

# ---- System setup ----
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Install wkhtmltopdf ----
RUN echo "📦 Installing wkhtmltopdf..." && \
    wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.jammy_amd64.deb && \
    apt-get update && apt-get install -y ./wkhtmltox_0.12.6-1.jammy_amd64.deb || true && \
    rm -f wkhtmltox_0.12.6-1.jammy_amd64.deb

# ---- Python setup ----
WORKDIR /app
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt --no-cache-dir

# ---- Environment variables ----
ENV FRAPPE_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# ---- Expose port ----
EXPOSE 8000

# ---- Start Frappe app ----
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "wsgi:application"]
