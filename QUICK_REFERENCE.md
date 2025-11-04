# ⚡ QUICK REFERENCE - Kanaan ERP Deployment

## 🚀 One-Command Deployment (After Setup)

```powershell
cd C:\xampp\htdocs\kanaanerpgaza-develop
.\deploy-server.ps1
```

**Time:** 3-5 minutes  
**Result:** Full deployment with Docker restart

---

## 📋 Setup (One-time only)

1. Open PowerShell **as Administrator**
2. Run these 3 commands:

```powershell
# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; [Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install sshpass
choco install sshpass -y

# Test SSH
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 "echo OK"
```

**Expected output:** `OK` ✅

3. **Close and reopen PowerShell** (normal, non-admin)

---

## 🎮 Common Commands

| Task | Command |
|------|---------|
| **Full Deployment** | `.\deploy-server.ps1` |
| **Deploy without logs** | `.\deploy-server.ps1 -ShowLogs:$false` |
| **Deploy no downtime** | `.\deploy-server.ps1 -NoDowntime:$true` |
| **View logs only** | `sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "docker-compose logs -f"` |
| **Check Docker status** | `sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "docker-compose ps"` |
| **SSH terminal** | `sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5` |

---

## 🔑 Credentials

- **Host:** 45.159.160.5
- **User:** esplzswx
- **Pass:** q0Ju50iFb+m^6k]$
- **Path:** /home/esplzswx/kanaanerpgaza-develop

---

## 🌐 Access Application

- **URL:** http://45.159.160.5
- **Username:** Administrator
- **Password:** admin

---

## 📂 Deployment Methods

1. **PowerShell SSH** ⭐ (Recommended)
   ```powershell
   .\deploy-server.ps1
   ```

2. **VS Code SFTP** (Development)
   - Install SFTP extension
   - Right-click file → Upload

3. **Manual SSH** (Debugging)
   - Use sshpass commands above

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| sshpass not found | `choco install sshpass -y` then close/reopen PowerShell |
| Connection refused | Check IP: 45.159.160.5, User: esplzswx, Pass: q0Ju50iFb+m^6k]$ |
| Cannot run script | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Docker won't start | `sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "docker-compose logs"` |

---

## 📚 Documentation

- `DEPLOYMENT_READY.md` - Full setup guide
- `DEPLOYMENT_COMPARISON.md` - Method comparison
- `SSH_SETUP_GUIDE.md` - Detailed SSH setup
- `deploy-server.ps1` - The deployment script
- `QUICK_REFERENCE.md` - This file

---

## ✅ Deployment Steps (Automated)

The `deploy-server.ps1` script automatically:

1. ✅ Verifies SSH connectivity
2. ✅ Updates Python packages
3. ✅ Updates npm packages
4. ✅ Builds frontend
5. ✅ Stops old Docker services
6. ✅ Starts new Docker services
7. ✅ Shows live logs (optional)

**Manual time:** 30+ minutes  
**Script time:** 3-5 minutes ⚡

---

## 🎯 Typical Day Workflow

```
Morning:
  └─ Edit files in VS Code
     └─ SFTP auto-uploads
     
When ready to test:
  └─ .\deploy-server.ps1 -ShowLogs:$false
  └─ Wait 3-5 minutes
  └─ Test at http://45.159.160.5
  
If needed:
  └─ View logs: sshpass -p '...' ssh ... "docker-compose logs"
  └─ Or SSH terminal and troubleshoot
```

---

## ⏱️ Time Estimates

| Task | Time |
|------|------|
| Setup (first time) | 15 min |
| SSH test | 1 min |
| Deploy (full) | 3-5 min |
| Deploy (no rebuild) | 1-2 min |

---

## 💾 Backup Commands

```powershell
# Backup database
sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "cd /home/esplzswx/kanaanerpgaza-develop && docker-compose exec db mysqldump -u root -p'password' --all-databases > backup.sql"

# Backup files
sshpass -p 'q0Ju50iFb+m^6k]$' scp -r esplzswx@45.159.160.5:/home/esplzswx/kanaanerpgaza-develop/erpnext ./backup_erpnext
```

---

## 🔐 Security Reminders

⚠️ **Keep these safe:**
- `.vscode/sftp.json` (has credentials)
- `deploy-server.ps1` (has credentials)
- SSH commands with password

✅ **Best practice:**
- Use environment variables for secrets
- Consider SSH key pairs for production
- Rotate passwords periodically

---

**Version:** 2.0  
**Last Updated:** 2024  
**Status:** ✅ Production Ready