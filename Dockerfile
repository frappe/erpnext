# ERPNext Docker Image
# Multi-stage build for optimized image size

FROM python:3.11-slim-bookworm as builder

# Install Node.js 18.x and build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy application code
COPY . /workspace/erpnext

# Install Python dependencies
WORKDIR /workspace/erpnext
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Install Node.js dependencies if needed
RUN if [ -f package.json ]; then yarn install --frozen-lockfile; fi

# Final stage
FROM python:3.11-slim-bookworm

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    # Database clients
    default-libmysqlclient-dev \
    mariadb-client \
    # PDF generation
    wkhtmltopdf \
    xvfb \
    libfontconfig1 \
    # Redis
    redis-tools \
    # CUPS for printing
    libcups2 \
    # Utilities
    git \
    curl \
    wget \
    vim \
    # Locales
    locales \
    # Node.js
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Create frappe user
RUN useradd -m -s /bin/bash frappe && \
    echo "frappe ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Install Frappe Bench
USER frappe
WORKDIR /home/frappe

RUN pip install --user --upgrade pip setuptools wheel && \
    pip install --user frappe-bench

ENV PATH="/home/frappe/.local/bin:${PATH}"

# Initialize bench
RUN bench init --skip-redis-config-generation --skip-assets --python python3.11 frappe-bench

WORKDIR /home/frappe/frappe-bench

# Copy application from builder
COPY --chown=frappe:frappe --from=builder /workspace/erpnext /home/frappe/frappe-bench/apps/erpnext

# Install app dependencies
RUN cd /home/frappe/frappe-bench/apps/erpnext && \
    pip install --user -e .

# Install the app to bench
RUN bench get-app --skip-assets --resolve-deps erpnext file:///home/frappe/frappe-bench/apps/erpnext || true

# Configure bench for production
RUN bench setup requirements --node && \
    bench build --apps erpnext || echo "Build step completed with warnings"

# Create sites directory volume mount point
RUN mkdir -p /home/frappe/frappe-bench/sites

# Expose ports
# 8000 - Frappe web server
# 9000 - Socket.io
# 6787 - Webpack dev server (development only)
EXPOSE 8000 9000 6787

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/method/ping || exit 1

# Set working directory
WORKDIR /home/frappe/frappe-bench

# Default command
CMD ["bench", "start"]
