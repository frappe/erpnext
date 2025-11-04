# ============================================================================
# Railway Setup Script for Windows PowerShell
# ============================================================================

Write-Host "`n╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🚀 Railway.com Setup Script for Kanaan ERP (PowerShell)           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# ============================================================================
# 1. Check Prerequisites
# ============================================================================
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Blue

try {
    $null = git --version 2>&1
    Write-Host "✅ Git found" -ForegroundColor Green
} catch {
    Write-Host "❌ Git is not installed" -ForegroundColor Red
    exit 1
}

if (Test-Path "Docker") {
    Write-Host "✅ Docker found" -ForegroundColor Green
} else {
    Write-Host "⚠️  Docker is not found (optional for local testing)" -ForegroundColor Yellow
}

# ============================================================================
# 2. Validate Files
# ============================================================================
Write-Host "`n[2/5] Validating required files..." -ForegroundColor Blue

$requiredFiles = @(
    "Dockerfile",
    "railway.json",
    "docker-entrypoint.sh",
    "requirements.txt",
    "package.json",
    "gunicorn.conf.py"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file found" -ForegroundColor Green
    } else {
        Write-Host "❌ $file not found" -ForegroundColor Red
        exit 1
    }
}

# ============================================================================
# 3. Create .env file
# ============================================================================
Write-Host "`n[3/5] Creating .env file..." -ForegroundColor Blue

if (Test-Path ".env") {
    $response = Read-Host "⚠️  .env already exists. Overwrite? (y/n)"
    if ($response -ne "y") {
        Write-Host "⏭️  Skipping .env creation" -ForegroundColor Yellow
    }
} else {
    # Create .env file
    @"
# Frappe Configuration
FRAPPE_ENV=production
DEBUG=false
SITE_NAME=localhost
SECRET_KEY=change-this-secret-key-to-something-random
ENCRYPTION_KEY=change-this-encryption-key-to-something-random

# Database Configuration (Railway provides these)
DATABASE_URL_HOSTNAME=db
DATABASE_URL_PORT=3306
DATABASE_URL_DATABASE=kanaan_erpnext
DATABASE_URL_USERNAME=erpnext
DATABASE_URL_PASSWORD=secure_password

# Redis Configuration
REDIS_URL=redis://redis:6379

# Node Configuration
NODE_ENV=production
NODE_OPTIONS=--max-old-space-size=2048

# Python Configuration
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Application Settings
ALLOW_HOSTS=localhost,127.0.0.1,*.railway.app
LOG_LEVEL=info
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ .env file created" -ForegroundColor Green
}

# ============================================================================
# 4. Initialize Git
# ============================================================================
Write-Host "`n[4/5] Initializing Git repository..." -ForegroundColor Blue

if (!(Test-Path ".git")) {
    Write-Host "⚠️  No .git directory found" -ForegroundColor Yellow
    $response = Read-Host "Do you want to initialize Git? (y/n)"
    if ($response -eq "y") {
        git init | Out-Null
        git add . | Out-Null
        git commit -m "Initial commit for Railway deployment" | Out-Null
        Write-Host "✅ Git initialized" -ForegroundColor Green
    }
} else {
    Write-Host "✅ Git repository exists" -ForegroundColor Green
    
    try {
        $remoteUrl = git config --get remote.origin.url 2>&1
        if ($remoteUrl) {
            Write-Host "✅ Remote 'origin' exists: $remoteUrl" -ForegroundColor Green
        }
    } catch {
        $gitUrl = Read-Host "Enter GitHub repository URL (e.g., https://github.com/user/repo)"
        git remote add origin $gitUrl | Out-Null
        Write-Host "✅ Remote 'origin' added" -ForegroundColor Green
    }
}

# ============================================================================
# 5. Display Next Steps
# ============================================================================
Write-Host "`n[5/5] Displaying next steps..." -ForegroundColor Blue

Write-Host "`n✅ Setup completed successfully!`n" -ForegroundColor Green

Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    📋 NEXT STEPS                                   ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "1️⃣  Push to GitHub:" -ForegroundColor Cyan
Write-Host "   git push -u origin main`n" -ForegroundColor Yellow

Write-Host "2️⃣  Go to Railway Dashboard:" -ForegroundColor Cyan
Write-Host "   https://railway.app`n" -ForegroundColor Yellow

Write-Host "3️⃣  Create new project:" -ForegroundColor Cyan
Write-Host "   New Project → Deploy from GitHub → Select Repository`n" -ForegroundColor Yellow

Write-Host "4️⃣  Add Database:" -ForegroundColor Cyan
Write-Host "   Add Service → Database → MariaDB`n" -ForegroundColor Yellow

Write-Host "5️⃣  Add Redis (optional):" -ForegroundColor Cyan
Write-Host "   Add Service → Database → Redis`n" -ForegroundColor Yellow

Write-Host "6️⃣  Configure Environment Variables:" -ForegroundColor Cyan
Write-Host "   See railway.json for configuration`n" -ForegroundColor Yellow

Write-Host "7️⃣  Monitor Deployment:" -ForegroundColor Cyan
Write-Host "   Watch logs in Railway Dashboard`n" -ForegroundColor Yellow

Write-Host "📚 More info: See RAILWAY_DEPLOYMENT_GUIDE.md`n" -ForegroundColor Cyan

Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║              🎯 IMPORTANT: Secure Your Secrets!                    ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Magenta

Write-Host "Change these values in Railway Dashboard Variables:" -ForegroundColor Yellow
Write-Host "  • SECRET_KEY → Random 32+ character string" -ForegroundColor White
Write-Host "  • ENCRYPTION_KEY → Random 32+ character string`n" -ForegroundColor White

Write-Host "Generate random keys (copy paste in Terminal):" -ForegroundColor Yellow
Write-Host "[Convert]::ToBase64String((1..32 | ForEach-Object {Get-Random -Maximum 256})) | Out-Host`n" -ForegroundColor Cyan

Write-Host "Done! 🎉`n" -ForegroundColor Green