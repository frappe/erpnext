# 🔐 SSH Setup Guide for Windows - Kanaan ERP Deployment

This guide helps you set up SSH connectivity on Windows for the automated deployment script.

---

## 📋 Prerequisites

- Windows 10 or later
- PowerShell 5.0 or later
- Administrator access (for installing packages)

---

## 🔧 Installation Options

### **Option 1: Using Chocolatey (Recommended)**

If you have **Chocolatey** installed, this is the easiest option.

#### Step 1: Install sshpass via Chocolatey

```powershell
choco install sshpass -y
```

#### Step 2: Verify Installation

```powershell
sshpass -V
```

Expected output: `sshpass 1.10` (or similar)

---

### **Option 2: Using Git Bash SSH**

If you have **Git for Windows** installed, you can use its SSH directly.

#### Step 1: Add Git Bash to PATH (if not already there)

By default, Git Bash SSH is available at:
```
C:\Program Files\Git\usr\bin\ssh.exe
C:\Program Files\Git\usr\bin\sshpass.exe
```

#### Step 2: Verify

```powershell
& "C:\Program Files\Git\usr\bin\sshpass.exe" -V
```

---

### **Option 3: Manual Installation of sshpass**

If neither Chocolatey nor Git Bash is available:

#### Step 1: Download sshpass

Download from: https://github.com/adfadf/sshpass-win

Extract to: `C:\Windows\System32\` or any folder in your PATH

#### Step 2: Verify

```powershell
sshpass -V
```

---

## ✅ Verify SSH Connection

Once sshpass is installed, test the connection:

```powershell
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 "echo 'SSH Works!'"
```

**Expected output:** `SSH Works!`

---

## 🚀 Run Deployment Script

Once SSH is set up, run the deployment script:

```powershell
cd C:\xampp\htdocs\kanaanerpgaza-develop

# Run with logs
.\deploy-server.ps1 -ShowLogs:$true

# Run without logs (faster)
.\deploy-server.ps1 -ShowLogs:$false

# Run with no downtime (optional)
.\deploy-server.ps1 -NoDowntime:$true
```

---

## 📊 Script Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-ServerHost` | 45.159.160.5 | SSH server IP address |
| `-Username` | esplzswx | SSH username |
| `-Password` | *credentials* | SSH password (hardcoded in script) |
| `-RemotePath` | /home/esplzswx/kanaanerpgaza-develop | Remote project path |
| `-ShowLogs` | $true | Display Docker logs after deployment |
| `-NoDowntime` | $false | Skip stopping old services |

---

## 🐛 Troubleshooting

### Issue: "sshpass is not recognized"

**Solution:** Install sshpass as described above, then restart PowerShell.

### Issue: "Connection refused"

**Solution:** Check if:
- Server host is correct: `45.159.160.5`
- Username is correct: `esplzswx`
- Password is correct: `q0Ju50iFb+m^6k]$`
- Server is online and accepting SSH connections

Test directly:
```powershell
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 "uname -a"
```

### Issue: "Execution policy prevents running scripts"

**Solution:** Set execution policy (run PowerShell as Admin):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

---

## 🔒 Security Notes

⚠️ **IMPORTANT:** The FTP password is **hardcoded in the script file**.

To improve security:

1. **Option A:** Use environment variables
   ```powershell
   $env:SFTP_PASSWORD = "q0Ju50iFb+m^6k]$"
   ```

2. **Option B:** Use SSH key pairs instead of passwords (recommended)
   ```powershell
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
   ```

3. **Option C:** Store credentials in Windows Credential Manager
   ```powershell
   cmdkey /add:45.159.160.5 /user:esplzswx /pass:"q0Ju50iFb+m^6k]$"
   ```

---

## 📁 VS Code SFTP Integration

The `.vscode/sftp.json` file is configured for automatic file uploads:

1. **Install SFTP Extension** in VS Code:
   - Search for "SFTP" in extensions
   - Install by liximomo

2. **Right-click on files** → "Upload" to sync manually

3. **Or enable auto-upload:**
   - Changes will auto-upload on save
   - Check `.vscode/sftp.json` for upload settings

---

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify all credentials are correct
3. Test SSH connection manually
4. Review Docker logs on the server:
   ```bash
   ssh esplzswx@45.159.160.5
   cd /home/esplzswx/kanaanerpgaza-develop
   docker-compose logs -f
   ```

---

**Last Updated:** 2024  
**Status:** ✅ Ready for Production Deployment