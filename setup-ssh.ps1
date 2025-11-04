# =====================================================
# SSH Setup Script for Windows
# =====================================================
# This script installs sshpass and verifies SSH connectivity
# Run with: .\setup-ssh.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host "SSH Setup for Kanaan ERP Deploy" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if running as admin
$isAdmin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544'
if (-not $isAdmin) {
    Write-Host "`n[!] This script requires Administrator privileges." -ForegroundColor Red
    Write-Host "[*] Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

# =====================================================
# Step 1: Check for Chocolatey
# =====================================================

Write-Host "`n[+] Checking for Chocolatey..." -ForegroundColor Green

$chocoPath = Get-Command choco -ErrorAction SilentlyContinue

if (-not $chocoPath) {
    Write-Host "[*] Chocolatey not found. Installing..." -ForegroundColor Yellow
    
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    
    Write-Host "[+] Chocolatey installed successfully" -ForegroundColor Green
} else {
    Write-Host "[+] Chocolatey found at: $($chocoPath.Source)" -ForegroundColor Green
}

# =====================================================
# Step 2: Install sshpass
# =====================================================

Write-Host "`n[+] Installing sshpass..." -ForegroundColor Green

choco install sshpass -y --force

# Verify installation
$sshpass = Get-Command sshpass -ErrorAction SilentlyContinue

if ($sshpass) {
    Write-Host "[+] sshpass installed successfully" -ForegroundColor Green
} else {
    Write-Host "[!] sshpass installation failed" -ForegroundColor Red
    exit 1
}

# =====================================================
# Step 3: Test SSH Connection
# =====================================================

Write-Host "`n[+] Testing SSH connection..." -ForegroundColor Green

$testCmd = sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 "echo 'SSH Connection Successful'" 2>&1

if ($testCmd -contains "SSH Connection Successful") {
    Write-Host "[+] SSH connection test PASSED!" -ForegroundColor Green
} else {
    Write-Host "[*] SSH connection test output:" -ForegroundColor Yellow
    Write-Host $testCmd -ForegroundColor Yellow
}

# =====================================================
# Step 4: Setup Complete
# =====================================================

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan

Write-Host "`n[+] You can now run the deployment script:" -ForegroundColor Green
Write-Host "    .\deploy-server.ps1" -ForegroundColor Cyan
Write-Host "`n[+] Or with specific options:" -ForegroundColor Green
Write-Host "    .\deploy-server.ps1 -ShowLogs:`$true" -ForegroundColor Cyan
Write-Host "    .\deploy-server.ps1 -NoDowntime:`$true" -ForegroundColor Cyan

Write-Host "`n[*] For more information, see: SSH_SETUP_GUIDE.md" -ForegroundColor Yellow