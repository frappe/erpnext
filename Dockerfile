# ──────────────────────────────────────────────────────────────────────────────
# ERPNext Fork – Docker Image
# Repository: https://github.com/fastlog-org/erpnext_test
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm AS builder

ARG FRAPPE_BRANCH=version-17
ARG PAYMENTS_BRANCH=version-17
# Fork-specific settings – point at this repository
ARG ERPNEXT_REPO=https://github.com/fastlog-org/erpnext_test
ARG ERPNEXT_BRANCH=develop

# Build-time system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        python3-dev \
        libffi-dev \
        libssl-dev \
        libmariadb-dev-compat \
        libmariadb-dev \
        curl \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Node.js 18 LTS (arch-aware)
ENV NODE_VERSION=18.20.4
RUN ARCH=$(dpkg --print-architecture | sed 's/amd64/x64/;s/arm64/arm64/') \
    && curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" \
       | tar -xJ -C /usr/local --strip-components=1 \
    && npm install -g yarn

# Create dedicated frappe user
RUN useradd -ms /bin/bash frappe \
    && mkdir -p /home/frappe/frappe-bench \
    && chown -R frappe:frappe /home/frappe

USER frappe
WORKDIR /home/frappe

ENV PATH="/home/frappe/.local/bin:${PATH}"

# Install bench CLI
RUN pip install --no-cache-dir --user frappe-bench

# Initialise bench (clones Frappe framework)
RUN bench init \
        --frappe-branch "${FRAPPE_BRANCH}" \
        --frappe-path "https://github.com/frappe/frappe" \
        --no-procfile \
        --no-backups \
        --skip-redis-config-generation \
        frappe-bench

WORKDIR /home/frappe/frappe-bench

# Install Payments app (dependency of ERPNext)
# Using git clone to guarantee directory name matches app_name ("payments")
RUN git clone --depth 1 \
        --branch "${PAYMENTS_BRANCH}" \
        https://github.com/frappe/payments \
        apps/payments \
    && ./env/bin/pip install --no-cache-dir -q -e apps/payments \
    && echo "payments" >> apps.txt

# Install ERPNext from this fork.
# Directory is named "erpnext" to match app_name in hooks.py,
# regardless of the repository name (erpnext_test).
RUN git clone --depth 1 \
        --branch "${ERPNEXT_BRANCH}" \
        "${ERPNEXT_REPO}" \
        apps/erpnext \
    && ./env/bin/pip install --no-cache-dir -q -e apps/erpnext \
    && echo "erpnext" >> apps.txt

# Install Node.js dependencies for all apps (payments + erpnext may have
# their own package.json entries that bench init didn't process).
RUN bench setup requirements --node

# Build production frontend assets
ENV NODE_ENV=production
RUN bench build --production


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="ERPNext Fork" \
      org.opencontainers.image.source="https://github.com/fastlog-org/erpnext_test" \
      org.opencontainers.image.description="Custom ERPNext build based on fastlog-org/erpnext_test"

# Runtime system dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git \
        mariadb-client \
        gettext-base \
        nginx \
        curl \
        # C libs needed by Python packages
        libssl3 \
        libmariadb3 \
        # PDF / image support
        libxrender1 \
        libxext6 \
        libx11-6 \
        libjpeg62-turbo \
        libpng16-16 \
        libfreetype6 \
        fontconfig \
        fonts-cantarell \
        # WeasyPrint / pango
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
        libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# wkhtmltopdf (arch-aware)
RUN ARCH=$(dpkg --print-architecture) \
    && curl -sLO \
       "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_${ARCH}.deb" \
    && dpkg -i "wkhtmltox_0.12.6.1-3.bookworm_${ARCH}.deb" \
    && rm "wkhtmltox_0.12.6.1-3.bookworm_${ARCH}.deb"

# Re-create frappe user in the runtime image
RUN useradd -ms /bin/bash frappe

# Node.js binary – required by the Socket.IO / websocket service.
# We copy only the node binary; the frappe node_modules are included
# inside the bench directory copied below.
COPY --from=builder /usr/local/bin/node /usr/local/bin/node

# Copy the fully-built bench from the builder stage
COPY --from=builder --chown=frappe:frappe \
    /home/frappe/frappe-bench /home/frappe/frappe-bench

# Copy container helper scripts
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh

USER frappe
WORKDIR /home/frappe/frappe-bench

ENV PATH="/home/frappe/frappe-bench/env/bin:/home/frappe/.local/bin:${PATH}" \
    HOME=/home/frappe

# sites volume is shared between all application containers
VOLUME ["/home/frappe/frappe-bench/sites"]

EXPOSE 8000 9000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["web"]
