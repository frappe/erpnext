# 🚀 ERIK ERP - Deployment Guide

**Complete guide for deploying ERIK ERP to production**

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Replit Autoscale (Recommended)](#replit-autoscale-recommended)
3. [Manual Deployment](#manual-deployment)
4. [Environment Variables](#environment-variables)
5. [Database Setup](#database-setup)
6. [Post-Deployment](#post-deployment)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## 🌐 Overview

ERIK ERP can be deployed using several methods:

### Deployment Options

| Method | Difficulty | Cost | Scalability | Recommended For |
|--------|-----------|------|-------------|-----------------|
| **Replit Autoscale** | Easy | Low | Auto | Development & Small Teams |
| **Docker** | Medium | Variable | Manual | Self-hosted |
| **AWS/GCP/Azure** | Hard | Variable | Manual | Enterprise |
| **DigitalOcean** | Medium | Low | Manual | Small-Medium Business |

### Architecture in Production

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   FastAPI App   │
                    │  (uvicorn/gun)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │
                    │    Database     │
                    └─────────────────┘

External Services:
  - Anthropic Claude AI (for AI assistant & OCR)
  - Email/SMS providers (for notifications)
  - Bank APIs (for integrations)
  - Mobile money APIs
```

---

## 🔵 Replit Autoscale (Recommended)

### Prerequisites

- Replit account
- Project on Replit

### Step 1: Fix Port Configuration

**CRITICAL**: Before deploying, you must manually edit the `.replit` file.

1. Open `.replit` in the Replit editor
2. Find the `[[ports]]` section (approximately lines 50-85)
3. **Delete ALL port configurations**
4. Save the file

**Delete this entire block:**
```toml
[[ports]]
localPort = 5000
externalPort = 5000

[[ports]]
localPort = 5001
externalPort = 5173

[[ports]]
localPort = 8000
externalPort = 8000
exposeLocalhost = true

[[ports]]
localPort = 34711
externalPort = 80

# ... all other port configurations
```

**Why?**: Autoscale deployments require only ONE external port (port 80), and Replit will auto-detect it.

---

### Step 2: Verify Deployment Configuration

The deployment configuration is already set in `.replit`:

```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 80"]
build = ["sh", "-c", "cd frontend && npm install && npm run build"]
```

---

### Step 3: Deploy

1. Click the **"Deploy"** button in Replit
2. Select **"Autoscale"**
3. Wait for build to complete (3-5 minutes)
4. Your app will be live at `https://your-repl-name.repl.co`

---

### Step 4: Configure Custom Domain (Optional)

1. Go to Replit Deploy settings
2. Add custom domain (e.g., `erp.yourcompany.com`)
3. Update DNS records as instructed
4. Wait for SSL certificate provisioning (automatic)

---

### Deployment Features

✅ **Auto-scaling** - Scales based on traffic  
✅ **Zero-downtime deployments** - Rolling updates  
✅ **Automatic SSL** - HTTPS enabled by default  
✅ **Built-in database** - PostgreSQL included  
✅ **Environment secrets** - Secure secret management  

---

## 🐳 Manual Deployment (Docker)

### Prerequisites

- Docker & Docker Compose installed
- PostgreSQL database
- Anthropic API key

### Step 1: Create Dockerfile

**backend/Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose port
EXPOSE 80

# Run with gunicorn for production
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:80"]
```

**frontend/Dockerfile:**
```dockerfile
FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy frontend code
COPY . .

# Build production bundle
RUN npm run build

# Install serve
RUN npm install -g serve

# Expose port
EXPOSE 5000

# Serve static files
CMD ["serve", "-s", "dist", "-l", "5000"]
```

---

### Step 2: Create docker-compose.yml

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: erikerp
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: erikerp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://erikerp:${DB_PASSWORD}@postgres:5432/erikerp
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      SECRET_KEY: ${SECRET_KEY}
    ports:
      - "8000:80"
    depends_on:
      - postgres
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:5000"
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

---

### Step 3: Create .env File

**.env:**
```bash
DB_PASSWORD=your-secure-password
ANTHROPIC_API_KEY=sk-ant-xxxxx
SECRET_KEY=your-secret-key-here
```

---

### Step 4: Deploy with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

---

## ☁️ Cloud Platform Deployment

### AWS (Elastic Beanstalk)

1. **Install EB CLI:**
```bash
pip install awsebcli
```

2. **Initialize EB:**
```bash
eb init -p python-3.11 erik-erp
```

3. **Create environment:**
```bash
eb create erik-erp-prod
```

4. **Set environment variables:**
```bash
eb setenv DATABASE_URL=postgresql://... ANTHROPIC_API_KEY=sk-ant-...
```

5. **Deploy:**
```bash
eb deploy
```

---

### Google Cloud Platform (Cloud Run)

1. **Build container:**
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/erik-erp
```

2. **Deploy:**
```bash
gcloud run deploy erik-erp \
  --image gcr.io/PROJECT_ID/erik-erp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql://...,ANTHROPIC_API_KEY=sk-ant-...
```

---

### DigitalOcean App Platform

1. **Create `app.yaml`:**
```yaml
name: erik-erp
services:
  - name: backend
    source_dir: backend
    github:
      repo: your-username/erik-erp
      branch: main
    build_command: pip install -r requirements.txt
    run_command: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
    envs:
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
      - key: ANTHROPIC_API_KEY
        value: ${ANTHROPIC_API_KEY}
    
  - name: frontend
    source_dir: frontend
    build_command: npm install && npm run build
    run_command: npx serve -s dist

databases:
  - name: db
    engine: PG
    version: "16"
```

2. **Deploy via CLI or web console**

---

## 🔐 Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `ANTHROPIC_API_KEY` | Claude AI API key | `sk-ant-xxxxx` |
| `SECRET_KEY` | JWT secret key | Random 32+ char string |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `production` |
| `SMTP_HOST` | Email server | `smtp.gmail.com` |
| `SMTP_PORT` | Email port | `587` |
| `SMTP_USER` | Email username | - |
| `SMTP_PASSWORD` | Email password | - |

### Generating SECRET_KEY

```bash
# Python method
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL method
openssl rand -base64 32
```

---

## 💾 Database Setup

### Option 1: Managed Database (Recommended)

Use a managed PostgreSQL service:
- **Replit**: Built-in PostgreSQL
- **AWS RDS**: Managed PostgreSQL
- **Google Cloud SQL**: Managed PostgreSQL
- **DigitalOcean**: Managed Databases
- **Heroku Postgres**: Managed PostgreSQL

---

### Option 2: Self-Hosted PostgreSQL

1. **Install PostgreSQL 16:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql-16

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

2. **Create database:**
```bash
sudo -u postgres psql

CREATE DATABASE erikerp;
CREATE USER erikuser WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE erikerp TO erikuser;
\q
```

3. **Configure connection:**
```bash
export DATABASE_URL="postgresql://erikuser:secure-password@localhost:5432/erikerp"
```

---

### Database Migrations

ERIK ERP uses SQLAlchemy with automatic table creation:

```python
# Tables are created automatically on first run
# No manual migrations needed
```

For schema changes, the app will automatically update tables on startup.

---

## ✅ Post-Deployment

### Step 1: Verify Deployment

```bash
# Check health
curl https://your-domain.com/health

# Expected response:
{"status": "healthy"}
```

---

### Step 2: Create Super Admin Account

Access your app and register the first account:

1. Go to `https://your-domain.com/register`
2. Enter company details
3. First user automatically becomes admin
4. Upgrade to `super_admin` via database:

```sql
UPDATE users SET role = 'super_admin' WHERE email = 'admin@yourcompany.com';
```

---

### Step 3: Configure Settings

1. Login as super admin
2. Go to **Settings**
3. Configure:
   - Email templates
   - Tax rates (if different from Zambia)
   - Leave types
   - Salary components

---

### Step 4: Test Core Features

- [ ] Create employee
- [ ] Create department
- [ ] Create chart of accounts
- [ ] Create journal entry
- [ ] Create product
- [ ] Create sales order
- [ ] Run payroll
- [ ] Generate reports

---

## 📊 Monitoring & Maintenance

### Application Monitoring

**Recommended Tools:**
- **Sentry** - Error tracking
- **New Relic** - Performance monitoring
- **Datadog** - Infrastructure monitoring

**Setup Sentry (Example):**
```bash
pip install sentry-sdk[fastapi]
```

```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://xxxxx@sentry.io/xxxxx",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)
```

---

### Database Backups

**Automated Backups (PostgreSQL):**

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="erikerp_backup_$DATE.sql"

pg_dump -U erikuser erikerp > "$BACKUP_DIR/$FILENAME"

# Compress
gzip "$BACKUP_DIR/$FILENAME"

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**Restore from Backup:**
```bash
gunzip erikerp_backup_20251104_100000.sql.gz
psql -U erikuser erikerp < erikerp_backup_20251104_100000.sql
```

---

### Log Management

**Backend Logs:**
```bash
# View logs in production
tail -f /var/log/erikerp/app.log

# With Docker
docker-compose logs -f backend

# With systemd
journalctl -u erikerp -f
```

---

### Performance Optimization

1. **Enable Gzip Compression:**
```python
# main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

2. **Add Database Connection Pooling:**
```python
# database.py
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20
)
```

3. **Enable Caching:**
```python
# Install Redis
pip install redis

# Use for session caching
```

---

## 🐛 Troubleshooting

### Issue: 502 Bad Gateway

**Cause**: Backend not running or port mismatch

**Solution:**
```bash
# Check if backend is running
ps aux | grep uvicorn

# Check logs
journalctl -u erikerp -n 100

# Restart service
systemctl restart erikerp
```

---

### Issue: Database Connection Failed

**Cause**: Incorrect DATABASE_URL or database not running

**Solution:**
```bash
# Test database connection
psql $DATABASE_URL

# Check PostgreSQL status
systemctl status postgresql

# Verify credentials in environment
echo $DATABASE_URL
```

---

### Issue: High Memory Usage

**Cause**: Too many workers or connection pool too large

**Solution:**
```bash
# Reduce workers
gunicorn -w 2 ...  # Instead of -w 4

# Reduce connection pool
# In database.py: pool_size=5, max_overflow=10
```

---

### Issue: Slow API Responses

**Cause**: Database queries not optimized

**Solution:**
```python
# Add database indexes
from sqlalchemy import Index

Index('idx_employee_company', Employee.company_id)
Index('idx_account_company', Account.company_id)

# Use eager loading
from sqlalchemy.orm import joinedload

employees = db.query(Employee)\
    .options(joinedload(Employee.department))\
    .all()
```

---

## 🔒 Security Checklist

Before going live, ensure:

- [ ] **HTTPS enabled** (SSL certificate)
- [ ] **Strong SECRET_KEY** (32+ characters, random)
- [ ] **Database backups** (automated)
- [ ] **Environment variables** (not hardcoded)
- [ ] **Firewall configured** (only necessary ports open)
- [ ] **Database credentials** (strong passwords)
- [ ] **CORS configured** (restrict origins in production)
- [ ] **Rate limiting** (prevent brute-force)
- [ ] **Audit logging** (enabled)
- [ ] **Regular updates** (security patches)

---

## 📞 Support

For deployment assistance:

- 📧 **Email**: support@erikerp.com
- 📚 **Docs**: [README.md](README.md)
- 🐛 **Issues**: GitHub Issues

---

## 📚 Additional Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [React Production Build](https://react.dev/learn/production-deployment)
- [Docker Documentation](https://docs.docker.com/)

---

**Good luck with your deployment! 🚀**

*If you encounter issues, check [Troubleshooting](#troubleshooting) or contact support.*

---

*Last updated: November 4, 2025*
