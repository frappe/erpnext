# Development Setup

This guide explains how to set up ERPNext locally for development.

## Prerequisites

| Tool    | Minimum Version |
| ------- | --------------- |
| Python  | 3.10            |
| Node.js | 18              |
| MariaDB | 10.6            |
| Redis   | 6               |
| Git     | 2.x             |

---

## Option 1: Docker (Recommended)

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Steps

```bash
git clone https://github.com/frappe/frappe_docker
cd frappe_docker

docker compose -f compose.yaml \
  -f overrides/compose.erpnext.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  up -d
```

- **URL:** http://localhost:8080
- **Username:** `Administrator`
- **Password:** `admin`

---

## Option 2: Local Setup with Bench

```bash
# Install Bench
pip install frappe-bench

# Initialize bench
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench

# Get ERPNext
bench get-app --branch version-15 erpnext

# Create a site
bench new-site erpnext.localhost --admin-password admin

# Install ERPNext
bench --site erpnext.localhost install-app erpnext

# Add to hosts
bench --site erpnext.localhost add-to-hosts

# Start server
bench start
```

Open http://erpnext.localhost:8000

---

## Enabling Developer Mode

```bash
bench --site erpnext.localhost set-config developer_mode 1
bench clear-cache
```

> Never enable developer mode on a production instance.

---

## Running Tests

```bash
# Run all tests
bench --site erpnext.localhost run-tests --app erpnext

# Run a specific module
bench --site erpnext.localhost run-tests --app erpnext --module erpnext.accounts
```

---

## Common Issues

**`bench` command not found**

```bash
export PATH=$PATH:$HOME/.local/bin
```

**MariaDB connection refused**

```bash
sudo service mariadb start
```

**Port 8000 already in use**

```bash
lsof -i :8000
kill -9 <PID>
```
