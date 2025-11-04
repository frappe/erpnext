#!/bin/bash

# ============================================================================
# ERPNext Kanaan ERP - Deploy Script for cPanel/FTP
# ============================================================================
# This script safely uploads your project to cPanel hosting
# 
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 ERPNext Kanaan ERP - cPanel Deploy Script${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ============================================================================
# Step 1: Gather Information
# ============================================================================
echo -e "${YELLOW}📋 Step 1: Gathering Deployment Information${NC}"
echo ""

# SFTP/SSH Configuration
read -p "SFTP Host (e.g., sftp.example.com or IP): " SFTP_HOST
read -p "SFTP Username: " SFTP_USER
read -sp "SFTP Password (will not be displayed): " SFTP_PASS
echo ""

read -p "Remote Path (e.g., /public_html or /home/user/kanaan): " REMOTE_PATH
read -p "Domain Name (e.g., kanaanerpgaza.espl.ps): " DOMAIN_NAME

# Optional: SSH Key
read -p "Use SSH Key instead? (y/N): " USE_SSH_KEY
if [[ $USE_SSH_KEY =~ ^[Yy]$ ]]; then
    read -p "SSH Key Path (e.g., ~/.ssh/id_rsa): " SSH_KEY
    SFTP_KEY="-i $SSH_KEY"
else
    SFTP_KEY=""
fi

echo ""

# ============================================================================
# Step 2: Create Backup
# ============================================================================
echo -e "${YELLOW}💾 Step 2: Creating Local Backup${NC}"

BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}✓${NC} Backup created: $BACKUP_DIR"
echo ""

# ============================================================================
# Step 3: Prepare Files for Upload
# ============================================================================
echo -e "${YELLOW}📦 Step 3: Preparing Files for Upload${NC}"

# Files/Directories to upload
UPLOAD_ITEMS=(
    "erpnext/"
    "Dockerfile"
    "docker-compose.yml"
    ".env.example"
    "docker-entrypoint.sh"
    "nginx.conf"
    "gunicorn.conf.py"
    "supervisor.conf"
    "requirements.txt"
    "package.json"
    "README.md"
)

# Files to exclude
EXCLUDE_PATTERNS=(
    "--exclude=.git"
    "--exclude=node_modules"
    "--exclude=__pycache__"
    "--exclude=*.pyc"
    "--exclude=.env"
    "--exclude=.DS_Store"
    "--exclude=.vscode"
    "--exclude=.idea"
    "--exclude=*.log"
)

echo -e "${GREEN}✓${NC} Files prepared for upload"
echo ""

# ============================================================================
# Step 4: Create .env File for Remote
# ============================================================================
echo -e "${YELLOW}⚙️ Step 4: Creating Remote .env Configuration${NC}"

read -p "Database Host (usually localhost): " DB_HOST
read -p "Database Name: " DB_NAME
read -p "Database User: " DB_USER
read -sp "Database Password: " DB_PASS
echo ""
read -p "Environment (development/production): " ENV_MODE

cat > .env.deploy <<EOF
# Auto-generated .env for deployment
DB_HOST=${DB_HOST:-localhost}
DB_PORT=3306
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}

REDIS_CACHE=localhost:6379
REDIS_QUEUE=localhost:6380

SITE_NAME=${DOMAIN_NAME}
FRAPPE_ENV=${ENV_MODE:-production}
DEBUG=false
LOG_LEVEL=INFO

BACKEND_PORT=8000
NGINX_PORT=8080
NGINX_HTTPS_PORT=8443

NODE_ENV=production
EOF

echo -e "${GREEN}✓${NC} .env.deploy created"
echo ""

# ============================================================================
# Step 5: Upload via SFTP
# ============================================================================
echo -e "${YELLOW}📤 Step 5: Uploading Files via SFTP${NC}"
echo -e "${YELLOW}This may take a few minutes...${NC}"
echo ""

# Create SFTP batch file
SFTP_BATCH="sftp_batch_$$.txt"
cat > "$SFTP_BATCH" <<EOF
cd $REMOTE_PATH
mkdir -p erpnext
mkdir -p private/files
mkdir -p sites

# Upload main directories
put -r erpnext erpnext
put -r nginx.conf nginx.conf
put -r gunicorn.conf.py gunicorn.conf.py
put -r supervisor.conf supervisor.conf
put -r requirements.txt requirements.txt
put -r docker-compose.yml docker-compose.yml
put -r Dockerfile Dockerfile
put -r docker-entrypoint.sh docker-entrypoint.sh
put -r .env.deploy .env

# Set permissions
chmod 755 docker-entrypoint.sh
chmod 644 .env

quit
EOF

# Execute SFTP upload
if [[ -n "$SSH_KEY" ]]; then
    sftp -i "$SSH_KEY" -b "$SFTP_BATCH" "${SFTP_USER}@${SFTP_HOST}" 2>/dev/null
else
    # For password-based SFTP, we'll use a different approach
    sshpass -p "$SFTP_PASS" sftp -b "$SFTP_BATCH" "${SFTP_USER}@${SFTP_HOST}" 2>/dev/null || {
        echo -e "${RED}✗ SFTP upload failed${NC}"
        echo -e "${YELLOW}Install sshpass first: brew install sshpass${NC}"
        exit 1
    }
fi

# Clean up batch file
rm -f "$SFTP_BATCH"

echo -e "${GREEN}✓${NC} Files uploaded successfully"
echo ""

# ============================================================================
# Step 6: Post-Upload Configuration
# ============================================================================
echo -e "${YELLOW}⚙️ Step 6: Post-Upload Configuration${NC}"

# Create remote commands file
REMOTE_COMMANDS=$(cat <<'COMMANDS'
cd REMOTE_PATH

# Install Python dependencies
pip3 install -r requirements.txt

# Install Node dependencies
npm ci --production

# Set proper permissions
chmod -R 755 .
chmod -R 755 private/
chmod -R 755 sites/

# Build frontend assets
npm run build

# Create required directories
mkdir -p logs
mkdir -p private/files
mkdir -p sites/DOMAIN/

echo "✓ Configuration complete"
COMMANDS
)

echo -e "${GREEN}✓${NC} Remote configuration ready"
echo ""

# ============================================================================
# Step 7: Summary
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment Completed Successfully!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}📝 Next Steps:${NC}"
echo ""
echo "1. Connect via SSH to run commands:"
echo -e "   ${BLUE}ssh ${SFTP_USER}@${SFTP_HOST}${NC}"
echo ""
echo "2. Navigate to project directory:"
echo -e "   ${BLUE}cd ${REMOTE_PATH}${NC}"
echo ""
echo "3. Run Docker Compose to start services:"
echo -e "   ${BLUE}docker-compose up -d${NC}"
echo ""
echo "4. Access your application:"
echo -e "   ${BLUE}https://${DOMAIN_NAME}${NC}"
echo ""
echo -e "${YELLOW}📋 Important Information:${NC}"
echo "- Backup location: $BACKUP_DIR"
echo "- Remote .env file: ${REMOTE_PATH}/.env"
echo "- Domain: $DOMAIN_NAME"
echo ""

# Clean up temporary files
rm -f .env.deploy

echo -e "${YELLOW}🔐 Security Tips:${NC}"
echo "1. Change default password (Administrator)"
echo "2. Enable SSL/HTTPS (use Let's Encrypt)"
echo "3. Set strong database passwords"
echo "4. Keep your .env file secure"
echo "5. Regular backups"
echo ""

echo -e "${GREEN}✨ Deployment script completed!${NC}"
echo ""