# =====================================================
# Kanaan ERP - Deploy Script for cPanel (PowerShell)
# =====================================================
# This script performs:
# 1. SSH connection to remote server
# 2. Virtual environment activation
# 3. Dependency installation
# 4. Docker startup
# 5. Live logs display
# =====================================================

param(
    [string]$ServerHost = "45.159.160.5",
    [string]$Username = "esplzswx",
    [string]$Password = "q0Ju50iFb+m^6k]$",
    [string]$RemotePath = "/home/esplzswx/kanaanerpgaza-develop",
    [switch]$ShowLogs = $true,
    [switch]$NoDowntime = $false
)

# Color definitions for output
$colors = @{
    Success = 'Green'
    Error   = 'Red'
    Warning = 'Yellow'
    Info    = 'Cyan'
}

function Write-Status {
    param([string]$Message, [string]$Type = 'Info')
    Write-Host $Message -ForegroundColor $colors[$Type]
}

function Invoke-SSHCommand {
    param(
        [string]$Command
    )
    
    Write-Status "[*] Executing command on $ServerHost..." -Type Info
    
    # Try using sshpass if available
    $sshpassPath = Get-Command sshpass -ErrorAction SilentlyContinue
    
    if ($sshpassPath) {
        # Use sshpass for password authentication
        & sshpass -p $Password ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" $Command
    } else {
        # Fallback: Use native SSH (requires key or manual auth)
        & ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" $Command
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Status "[!] Command may have failed or connection issue occurred" -Type Warning
        return $false
    }
    
    return $true
}

# =====================================================
# STEP 1: Verify Prerequisites
# =====================================================

Write-Status "`n[+] Verifying prerequisites..." -Type Info

# Check if sshpass is available
$sshpassPath = Get-Command sshpass -ErrorAction SilentlyContinue

if ($sshpassPath) {
    Write-Status "[+] sshpass found (password authentication ready)" -Type Success
} else {
    Write-Status "[*] sshpass not found, will try native SSH" -Type Warning
    Write-Status "[*] For password authentication, install sshpass:" -Type Warning
    Write-Status "    choco install sshpass -y" -Type Warning
}

# =====================================================
# STEP 2: Test Connection
# =====================================================

Write-Status "`n[+] Testing connection to server..." -Type Info

# Check if sshpass is available
$sshpassPath = Get-Command sshpass -ErrorAction SilentlyContinue

if ($sshpassPath) {
    $testConnection = & sshpass -p $Password ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" "echo 'Connected'" 2>&1
} else {
    $testConnection = & ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" "echo 'Connected'" 2>&1
}

if ($testConnection -contains "Connected") {
    Write-Status "[+] Connection successful" -Type Success
} else {
    Write-Status "[!] Connection failed" -Type Error
    Write-Status "[*] Verify:" -Type Warning
    Write-Status "    - SSH Key is correct" -Type Warning
    Write-Status "    - Username is correct ($Username)" -Type Warning
    Write-Status "    - Host is correct ($ServerHost)" -Type Warning
    exit 1
}

# =====================================================
# STEP 3: Update Dependencies
# =====================================================

Write-Status "`n[+] Updating dependencies..." -Type Info

$updateCommand = @"
cd $RemotePath
source /home/$Username/virtualenv/kanaanerpgaza-develop/3.12/bin/activate
pip install -r requirements.txt -q
npm ci --production --silent
npm run build --silent 2>/dev/null
echo 'Update complete'
"@

Invoke-SSHCommand $updateCommand | Out-Null

# =====================================================
# STEP 4: Stop Old Services (if needed)
# =====================================================

if (-not $NoDowntime) {
    Write-Status "`n[+] Stopping old services..." -Type Info
    
    $stopCommand = @"
cd $RemotePath
docker-compose down 2>/dev/null || true
sleep 2
"@
    
    Invoke-SSHCommand $stopCommand | Out-Null
}

# =====================================================
# STEP 5: Start Docker Services
# =====================================================

Write-Status "`n[+] Starting Docker services..." -Type Info

$startCommand = @"
cd $RemotePath
docker-compose up -d
sleep 3
docker-compose ps
"@

Invoke-SSHCommand $startCommand | Out-Null

# =====================================================
# STEP 6: Display Logs (optional)
# =====================================================

if ($ShowLogs) {
    Write-Status "`n[+] Displaying logs (Press Ctrl+C to stop)..." -Type Info
    
    $sshpassPath = Get-Command sshpass -ErrorAction SilentlyContinue
    
    if ($sshpassPath) {
        & sshpass -p $Password ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" "cd $RemotePath && docker-compose logs -f"
    } else {
        & ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" "cd $RemotePath && docker-compose logs -f"
    }
}

# =====================================================
# DEPLOYMENT COMPLETE
# =====================================================

Write-Status "`n[+] Deployment successful!" -Type Success
Write-Status "`n[*] Access the application at:" -Type Info
Write-Status "    http://kanaanerpgaza.espl.ps" -Type Success
Write-Status "`n[*] Login credentials:" -Type Info
Write-Status "    Username: Administrator" -Type Success
Write-Status "    Password: admin" -Type Success
Write-Status "`n[*] To view logs later, run: docker-compose logs -f" -Type Info