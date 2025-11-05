FROM python:3.11-bookworm

# Set environment variables
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    gcc \
    g++ \
    make \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libmariadb-dev \
    libjpeg-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    mariadb-client \
    libmariadb-dev-compat \
    fontconfig \
    xfonts-75dpi \
    xfonts-base \
    xvfb \
    && wget -O /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bookworm_amd64.deb \
    && dpkg -i /tmp/wkhtmltox.deb || apt-get -f -y install \
    && ln -s /usr/local/bin/wkhtmltopdf /usr/bin/wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/* /tmp/wkhtmltox.deb

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install yarn
RUN npm install -g yarn

# Create app directory
RUN mkdir -p /home/frappe/bench
WORKDIR /home/frappe/bench

# Install Python dependencies for Frappe/ERPNext
RUN pip install --upgrade pip
RUN pip install frappe-bench

# Initialize bench (if needed)
RUN bench init frappe-bench --skip-assets --python $(which python) --skip-redis-config-generation

WORKDIR /home/frappe/bench/frappe-bench

# Clone ERPNext repo (adjust version as needed)
RUN bench get-app erpnext https://github.com/frappe/erpnext --branch version-14

# Expose ports
EXPOSE 8000 9000

# Create startup script
RUN cat > /start.sh << EOF
#!/bin/bash

# Check if site exists, if not create one
if [ ! -f /home/frappe/bench/frappe-bench/sites/.initialized ]; then
    echo "Initializing new site..."
    
    # Set MariaDB connection details from environment variables
    export DB_HOST=\${DB_HOST:-localhost}
    export DB_PORT=\${DB_PORT:-3306}
    export DB_NAME=\${DB_NAME:-frappe}
    export DB_USER=\${DB_USER:-root}
    export DB_PASSWORD=\${DB_PASSWORD:-}
    
    # Create site
    bench new-site \${SITE_NAME:-erp.example.com} \
        --mariadb-root-password=\${DB_PASSWORD} \
        --admin-password=\${ADMIN_PASSWORD:-admin} \
        --install-app erpnext \
        --force
    
    touch /home/frappe/bench/frappe-bench/sites/.initialized
fi

# Start bench services
bench start
EOF

RUN chmod +x /start.sh

CMD ["/start.sh"]
