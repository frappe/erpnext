FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    software-properties-common \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install MariaDB client and other dependencies
RUN apt-get update && apt-get install -y \
    mariadb-client \
    libmariadb-dev \
    build-essential \
    python3-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install wkhtmltopdf
RUN wget -O /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb \
    && apt-get update && apt-get install -y /tmp/wkhtmltox.deb \
    && rm /tmp/wkhtmltox.deb

# Create user and directories
RUN useradd -m -s /bin/bash frappe \
    && mkdir -p /home/frappe/bench

WORKDIR /home/frappe/bench

# Install bench
RUN pip3 install frappe-bench

# Initialize bench
USER frappe
RUN bench init frappe-bench --python python3 --skip-assets

WORKDIR /home/frappe/bench/frappe-bench

# Install ERPNext
RUN bench get-app erpnext https://github.com/frappe/erpnext --branch version-14

# Switch back to root for startup script
USER root

# Create startup script
RUN echo '#!/bin/bash\n\
\n\
cd /home/frappe/bench/frappe-bench\n\
\n\
# Wait for database to be ready\n\
echo "Waiting for database..."\n\
while ! mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -P $DB_PORT -e "SELECT 1;" > /dev/null 2>&1; do\n\
  sleep 5\n\
done\n\
\n\
# Check if site exists\n\
if [ ! -f sites/.initialized ]; then\n\
  echo "Creating new site..."\n\
  su frappe -c "cd /home/frappe/bench/frappe-bench && bench new-site $SITE_NAME --mariadb-root-password=$DB_PASSWORD --admin-password=$ADMIN_PASSWORD --force"\n\
  su frappe -c "cd /home/frappe/bench/frappe-bench && bench --site $SITE_NAME install-app erpnext"\n\
  touch sites/.initialized\n\
  echo "Site created successfully!"\n\
fi\n\
\n\
echo "Starting bench..."\n\
su frappe -c "cd /home/frappe/bench/frappe-bench && bench start"\n\
' > /start.sh

RUN chmod +x /start.sh

EXPOSE 8000 9000

CMD ["/bin/bash", "/start.sh"]
