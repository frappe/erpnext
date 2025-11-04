#!/bin/bash
# ============================================================================
# Railway Setup Script for Kanaan ERP
# ============================================================================
# This script prepares the application for deployment on Railway.com

set -e

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  🚀 Railway.com Setup Script for Kanaan ERP                        ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 1. Check Prerequisites
# ============================================================================
echo -e "${BLUE}[1/6]${NC} Checking prerequisites..."

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Git found${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker is not installed (optional for local testing)${NC}"
fi

# ============================================================================
# 2. Validate Files
# ============================================================================
echo ""
echo -e "${BLUE}[2/6]${NC} Validating required files..."

REQUIRED_FILES=(
    "Dockerfile"
    "railway.json"
    "docker-entrypoint.sh"
    "requirements.txt"
    "package.json"
    "gunicorn.conf.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file found${NC}"
    else
        echo -e "${RED}❌ $file not found${NC}"
        exit 1
    fi
done

# ============================================================================
# 3. Create .env file
# ============================================================================
echo ""
echo -e "${BLUE}[3/6]${NC} Creating .env file..."

if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env already exists${NC}"
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏭️  Skipping .env creation${NC}"
    fi
fi

if [ ! -f ".env" ] || [[ $REPLY =~ ^[Yy]$ ]]; then
    cat > .env <<'ENVFILE'
# ============================================================================
# Kanaan ERP - Railway Deployment Configuration
# ============================================================================

# Frappe Configuration
FRAPPE_ENV=production
DEBUG=false
SITE_NAME=localhost
SECRET_KEY=change-this-secret-key-to-something-random
ENCRYPTION_KEY=change-this-encryption-key-to-something-random

# Database Configuration (Railway provides these)
# These will be filled by Railway from DATABASE_URL
DB_HOST=${DATABASE_URL_HOSTNAME}
DB_PORT=${DATABASE_URL_PORT}
DB_NAME=${DATABASE_URL_DATABASE}
DB_USER=${DATABASE_URL_USERNAME}
DB_PASSWORD=${DATABASE_URL_PASSWORD}

# Redis Configuration (Railway provides these)
REDIS_CACHE=${REDIS_URL}
REDIS_QUEUE=${REDIS_URL}

# Node Configuration
NODE_ENV=production
NODE_OPTIONS=--max-old-space-size=2048

# Python Configuration
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Application Settings
ALLOW_HOSTS=localhost,127.0.0.1,*.railway.app
LOG_LEVEL=info
MAX_POOL_SIZE=10
ENVFILE
    echo -e "${GREEN}✅ .env file created${NC}"
fi

# ============================================================================
# 4. Initialize Git (if needed)
# ============================================================================
echo ""
echo -e "${BLUE}[4/6]${NC} Initializing Git repository..."

if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  No .git directory found${NC}"
    read -p "Do you want to initialize Git? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git init
        git add .
        git commit -m "Initial commit for Railway deployment"
        echo -e "${GREEN}✅ Git initialized${NC}"
    fi
else
    echo -e "${GREEN}✅ Git repository exists${NC}"
    
    # Check if origin exists
    if git remote get-url origin &> /dev/null; then
        echo -e "${GREEN}✅ Remote 'origin' exists: $(git remote get-url origin)${NC}"
    else
        read -p "Enter GitHub repository URL (e.g., https://github.com/user/repo): " git_url
        git remote add origin "$git_url"
        echo -e "${GREEN}✅ Remote 'origin' added${NC}"
    fi
fi

# ============================================================================
# 5. Validate Docker Image
# ============================================================================
echo ""
echo -e "${BLUE}[5/6]${NC} Validating Docker configuration..."

if command -v docker &> /dev/null; then
    echo -e "${YELLOW}ℹ️  Testing Docker build (this may take a few minutes)...${NC}"
    if docker build -t kanaan-erp:test . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker build successful${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker build failed (non-critical)${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  Docker not available, skipping build test${NC}"
fi

# ============================================================================
# 6. Display Next Steps
# ============================================================================
echo ""
echo -e "${BLUE}[6/6]${NC} Displaying next steps..."
echo ""
echo -e "${GREEN}✅ Setup completed successfully!${NC}"
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    📋 NEXT STEPS                                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  Push to GitHub:"
echo -e "   ${YELLOW}git push -u origin main${NC}"
echo ""
echo "2️⃣  Go to Railway Dashboard:"
echo -e "   ${YELLOW}https://railway.app${NC}"
echo ""
echo "3️⃣  Create new project:"
echo -e "   ${YELLOW}New Project → Deploy from GitHub → Select Repository${NC}"
echo ""
echo "4️⃣  Add Database:"
echo -e "   ${YELLOW}Add Service → Database → MariaDB${NC}"
echo ""
echo "5️⃣  Add Redis (optional):"
echo -e "   ${YELLOW}Add Service → Database → Redis${NC}"
echo ""
echo "6️⃣  Configure Environment Variables:"
echo -e "   ${YELLOW}See railway.json for configuration${NC}"
echo ""
echo "7️⃣  Monitor Deployment:"
echo -e "   ${YELLOW}Watch logs in Railway Dashboard${NC}"
echo ""
echo "📚 More info: See RAILWAY_DEPLOYMENT_GUIDE.md"
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║              🎯 IMPORTANT: Secure Your Secrets!                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Change these values in Railway Dashboard Variables:"
echo "  • SECRET_KEY → Random 32+ character string"
echo "  • ENCRYPTION_KEY → Random 32+ character string"
echo ""
echo "Use: $(openssl rand -base64 32)"
echo ""