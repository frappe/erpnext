# Project Repository Configuration

## Project Information
- **Name**: ERPNext (كنعان ERP - Kanaan ERP)
- **Repository**: c:\xampp\htdocs\kanaanerpgaza-develop
- **Type**: Enterprise Resource Planning System
- **Framework**: Frappe Framework v15 + ERPNext v15.85.1
- **Language**: Python (Backend) + JavaScript (Frontend)
- **Status**: ✅ Running (Docker Compose)

## Testing Framework Configuration
- **Target Framework**: **Playwright** (Default)
- **Language**: TypeScript
- **Location**: `tests/e2e/`
- **Test Pattern**: `*.spec.ts`
- **Version**: Playwright ≥ v1.44

## Application Access
- **Frontend**: http://localhost:8080
- **Default Credentials**: 
  - Username: Administrator
  - Password: admin
- **Language**: Arabic (RTL Support)

## Docker Services Status
All services deployed and running:
- ✅ Nginx (Frontend Proxy) - Port 8080
- ✅ Gunicorn (Backend API) - Port 8000
- ✅ MariaDB (Database) - Port 3306
- ✅ Redis Cache - Port 6379
- ✅ Redis Queue - Port 6380
- ✅ Node.js WebSocket Server
- ✅ Scheduler & Queue Workers

## Key Files
- **Backend**: `erpnext/` directory
- **Config**: `pyproject.toml`, `package.json`
- **Package Manager**: npm/yarn
- **Python Version**: 3.14.0+

## Development Notes
- Tests should target the running application at http://localhost:8080
- Use stable selectors (data-testid, ARIA roles, text content)
- Follow Page Object Model (POM) pattern for Playwright tests
- All tests must be deterministic and idempotent
- Use Frappe/ERPNext selectors where possible (e.g., `[data-doctype]`, `[data-docstatus]`)

## Test Execution Commands
```bash
# Run all E2E tests
npx playwright test tests/e2e/ --reporter=line

# Run specific test
npx playwright test tests/e2e/<test-name>.spec.ts

# Run in debug mode
npx playwright test --debug

# Update snapshots
npx playwright test --update-snapshots
```

## Deployment Configuration
- **Deployment Methods:** 
  - 🚀 **Railway.com** (Recommended) - Easiest & Fastest
  - ⚙️ PowerShell SSH Script via `deploy-server.ps1`
  - 📦 Docker Compose (Local/VPS)
  - 🌐 Cloud Platforms (Heroku, Render, DigitalOcean)

## Deployment Credentials
- **Host:** 45.159.160.5
- **Username:** esplzswx
- **Port:** 22 (SFTP/SSH)
- **Remote Path:** /home/esplzswx/kanaanerpgaza-develop
- **Virtual Environment:** /home/esplzswx/virtualenv/kanaanerpgaza-develop/3.12/

## Deployment Files
- **Script:** `deploy-server.ps1` - Automated PowerShell deployment
- **SFTP Config:** `.vscode/sftp.json` - VS Code file sync
- **Setup Script:** `setup-ssh.ps1` - Automated SSH setup
- **Documentation:** 
  - `DEPLOYMENT_READY.md` - Full guide
  - `DEPLOYMENT_COMPARISON.md` - Method comparison
  - `SSH_SETUP_GUIDE.md` - SSH setup instructions
  - `QUICK_REFERENCE.md` - Quick commands

## Deployment Process
```
1. Install sshpass (one-time)
2. Configure SSH credentials (done)
3. Run: .\deploy-server.ps1
4. Automation handles: pip, npm, build, Docker restart
5. Access at: http://45.159.160.5
```

## Quick Deployment
```powershell
cd c:\xampp\htdocs\kanaanerpgaza-develop
.\deploy-server.ps1 -ShowLogs:$false
```

## Docker Deployment Configuration
- **Docker Support**: ✅ Fully Configured
- **Docker Compose**: ✅ Multi-service setup (7 services + Railway variant)
- **Deployment Platforms**: 
  - 🚀 **Railway.app** (RECOMMENDED) - Easiest, fastest, best free tier
  - ✅ Render.com (render.yaml)
  - ✅ Heroku (Procfile)
  - ✅ DigitalOcean App Platform (docker-compose.yml)
  - ✅ VPS with cPanel (docker-entrypoint.sh + nginx.conf)
- **CI/CD Pipeline**: ✅ GitHub Actions Workflow + Railway Auto-Deploy

## Docker Files Created
| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build for production |
| `docker-compose.yml` | 7 services setup |
| `.dockerignore` | Optimize image size |
| `.env.example` | Environment variables |
| `docker-entrypoint.sh` | Startup script |
| `nginx.conf` | Reverse proxy config |
| `gunicorn.conf.py` | WSGI server config |
| `supervisor.conf` | Process manager |
| `requirements.txt` | Python dependencies |
| `DEPLOYMENT_GUIDE.md` | Complete guide |
| `DOCKER_QUICKSTART.md` | Quick start |

## Local Development with Docker
```bash
# Quick start
cp .env.example .env
docker-compose up -d
# Access at http://localhost:8080
```

## Railway.com Deployment (NEW ✨)
- **Status**: ✅ Fully Configured & Ready
- **Quick Start**: `bash railway-setup.sh`
- **Documentation**: See RAILWAY_DEPLOYMENT_GUIDE.md
- **Features**:
  - ✅ One-click deployment from GitHub
  - ✅ Automatic SSL/TLS
  - ✅ Built-in PostgreSQL & Redis
  - ✅ GitHub Actions integration
  - ✅ Free tier with $5 monthly credit
  - ✅ Automatic rollback support
  - ✅ Health checks & monitoring

### Railway Deployment Files
| File | Purpose |
|------|---------|
| `railway.json` | Railway configuration (Build, Deploy, Env vars) |
| `RAILWAY_DEPLOYMENT_GUIDE.md` | Complete deployment guide (Arabic/English) |
| `RAILWAY_QUICK_START.md` | 5-minute quick start guide |
| `railway-setup.sh` | Automated project setup script |
| `docker-compose.railway.yml` | Local testing similar to Railway |
| `.env.railway.example` | Environment variables template |
| `RAILWAY_TROUBLESHOOTING.md` | Common issues & solutions |
| `.github/workflows/railway-deploy.yml` | GitHub Actions auto-deploy |
| `wsgi.py` | WSGI app for Gunicorn |

### Railway Setup Commands
```bash
# Quick start
bash railway-setup.sh

# Test locally
docker-compose -f docker-compose.railway.yml up

# Deploy to Railway
git push origin main
# Railway auto-deploys via GitHub integration
```

### Railway Environment Variables
Configured in `railway.json`:
- Database: AUTO (MariaDB from Railway)
- Redis: AUTO (Redis from Railway)
- Python: PYTHONUNBUFFERED=1
- Node: NODE_ENV=production
- App: FRAPPE_ENV=production, DEBUG=false

---
*Last Updated: 2024*
*Configuration by: QA & Deployment Team*
*Status: Railway Deployment Ready ✅ | All Methods Supported ✅*