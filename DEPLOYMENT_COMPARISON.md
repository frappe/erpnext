# 📊 Deployment Methods Comparison - Kanaan ERP

This guide compares the three deployment approaches for your cPanel-hosted ERPNext application.

---

## 🎯 Quick Comparison Table

| Feature | VS Code SFTP | PowerShell SSH | Manual SSH |
|---------|-------------|----------------|-----------|
| **Setup Time** | 5 min | 15 min | 20 min |
| **Automation** | ❌ Manual uploads | ✅ Fully automated | ❌ Manual commands |
| **File Sync** | ✅ Auto on save | ✅ Included | ❌ Manual |
| **Docker Restart** | ❌ Manual | ✅ Automatic | ❌ Manual |
| **Logs Viewing** | ❌ Manual SSH | ✅ Included | ✅ Included |
| **Build Process** | ❌ Manual | ✅ Automatic | ❌ Manual |
| **Dependency Install** | ❌ Manual | ✅ Automatic | ❌ Manual |
| **Skill Level Required** | Beginner | Intermediate | Advanced |
| **Best For** | Development | Continuous Deployment | Debugging |
| **Speed** | 🐢 Slow | 🚀 Fast | 🐇 Medium |

---

## 📝 Detailed Comparison

### **1️⃣ VS Code SFTP Upload**

#### Overview
Simple file synchronization using the SFTP protocol through VS Code. Perfect for development work where you're editing files locally.

#### Setup Steps
1. Install "SFTP" extension in VS Code
2. Configuration already in `.vscode/sftp.json`
3. Files auto-upload on save

#### Workflow
```
Edit file locally → Save → SFTP auto-uploads to server
```

#### Pros ✅
- Very easy to set up
- Real-time file synchronization
- No command-line needed
- Perfect for live development
- Visual feedback in VS Code
- Can upload individual files or folders

#### Cons ❌
- Must restart Docker manually after uploads
- Must run `npm run build` manually
- Must install dependencies manually
- No automation for deployment steps
- Slow for large file transfers
- Not suitable for CI/CD

#### Commands Reference
```powershell
# Manual rebuild after uploading
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 << 'EOF'
cd /home/esplzswx/kanaanerpgaza-develop
source /home/esplzswx/virtualenv/kanaanerpgaza-develop/3.12/bin/activate
pip install -r requirements.txt
npm ci --production
npm run build
docker-compose restart
EOF
```

#### Best For
- 👨‍💻 **Active development**
- 🔧 **Quick testing**
- 📝 **Minor file edits**

#### Time to Deploy
- First time: 5 minutes
- Subsequent: 2-30 minutes (depends on what changed)

---

### **2️⃣ PowerShell SSH Deployment (RECOMMENDED)**

#### Overview
Fully automated deployment script that handles everything from dependency installation to Docker restart. This is the professional approach for production deployments.

#### Setup Steps
1. Install Chocolatey (one-time)
2. Install sshpass via Chocolatey
3. Run `deploy-server.ps1`

#### Workflow
```
.\deploy-server.ps1 → Automated 6-step deployment
```

#### Complete Automation Steps
1. ✅ Verify SSH connectivity
2. ✅ Activate virtual environment
3. ✅ Install Python dependencies (`pip install`)
4. ✅ Install npm packages (`npm ci`)
5. ✅ Build frontend assets (`npm run build`)
6. ✅ Stop old Docker services (optional)
7. ✅ Start new Docker services
8. ✅ Display live logs (optional)

#### Pros ✅
- **FULLY AUTOMATED** - No manual steps
- Handles all deployment steps
- Deterministic and repeatable
- Fast and efficient
- Can be scheduled with Windows Task Scheduler
- Perfect for CI/CD integration
- Logs all actions
- Error handling and rollback capability
- Production-ready

#### Cons ❌
- Requires sshpass installation (one-time)
- Takes ~2-5 minutes to complete
- Stops services during deployment (unless `-NoDowntime` flag used)
- Credentials hardcoded in script (security consideration)

#### Usage Examples
```powershell
# Standard deployment
.\deploy-server.ps1

# Quick deployment without logs
.\deploy-server.ps1 -ShowLogs:$false

# No downtime deployment
.\deploy-server.ps1 -NoDowntime:$true

# With specific parameters
.\deploy-server.ps1 -ServerHost "45.159.160.5" -Username "esplzswx" -ShowLogs:$true
```

#### Script Features
- **Color-coded output** for easy reading
- **Error detection** at each step
- **Automatic retry** on transient failures
- **Graceful degradation** if optional features unavailable
- **Docker status display** after restart
- **Access URL provided** at the end

#### Time to Deploy
- First time: 15 minutes (including sshpass install)
- Subsequent: 3-5 minutes

#### Best For
- 🚀 **Production deployments**
- 🔄 **Continuous integration**
- 🤖 **Scheduled deployments**
- 👥 **Team environments**

---

### **3️⃣ Manual SSH Commands**

#### Overview
Direct SSH commands for advanced users who need complete control and understand each deployment step.

#### Setup Steps
1. Install Git for Windows or sshpass
2. Learn SSH commands
3. Execute commands manually

#### Workflow
```
sshpass -p 'password' ssh ... → Execute each command manually
```

#### Complete Manual Process
```bash
# 1. Connect
ssh esplzswx@45.159.160.5

# 2. Navigate and activate
cd /home/esplzswx/kanaanerpgaza-develop
source /home/esplzswx/virtualenv/kanaanerpgaza-develop/3.12/bin/activate

# 3. Update dependencies
pip install -r requirements.txt
npm ci --production

# 4. Build frontend
npm run build

# 5. Restart Docker
docker-compose down
docker-compose up -d

# 6. View logs
docker-compose logs -f
```

#### Pros ✅
- Full control over each step
- Can debug individual commands
- Perfect for learning
- No dependency on scripts
- Can inspect server state between steps
- Useful for troubleshooting

#### Cons ❌
- Manual and error-prone
- Takes 10-15 minutes
- Easy to forget steps
- No automation benefits
- Not repeatable
- Poor for teams
- No version control

#### Time to Deploy
- First time: 20-30 minutes
- Subsequent: 15-20 minutes (still manual)

#### Best For
- 🔍 **Troubleshooting**
- 📚 **Learning**
- 🐛 **Debugging issues**

---

## 🚀 Quick Start Recommendations

### **For Development Work:**
1. ✅ Use **VS Code SFTP** for daily editing
2. ✅ Use **PowerShell SSH** when ready to test deployment
3. ✅ Use **Manual SSH** only if debugging

### **For Production Deployment:**
1. ✅ Use **PowerShell SSH** every time
2. ✅ Schedule with Windows Task Scheduler
3. ✅ Monitor logs in real-time

### **For Team Environments:**
1. ✅ Use **PowerShell SSH** in CI/CD pipeline
2. ✅ Use **VS Code SFTP** for local development
3. ✅ Use **Manual SSH** only in emergencies

---

## 🔄 Typical Development Workflow

```
Daily Development:
  ↓
1. Edit files locally in VS Code
2. SFTP auto-syncs to server
3. Test changes manually if needed
4. When ready: Run .\deploy-server.ps1
5. Verify deployment at http://kanaanerpgaza.espl.ps
  ↓
Production Deployment:
  ↓
1. Run .\deploy-server.ps1 -NoDowntime:$true
2. Monitor logs: .\deploy-server.ps1 -ShowLogs:$true
3. Verify all services running
4. Test application functionality
  ↓
Done! ✅
```

---

## 🛠️ Detailed Setup Instructions

### **VS Code SFTP Setup**

```
1. Install "SFTP" extension (by liximomo)
   - Open VS Code
   - Ctrl+Shift+X (Extensions)
   - Search "SFTP"
   - Click Install

2. Configuration complete!
   - .vscode/sftp.json already configured
   - Files will auto-sync on save

3. To upload file:
   - Right-click file → Upload
   - Or Ctrl+Alt+U

4. To view on server:
   - Files accessible at: /home/esplzswx/kanaanerpgaza-develop
```

### **PowerShell SSH Setup**

```powershell
# Step 1: Open PowerShell as Admin
# Windows+X → Windows PowerShell (Admin)

# Step 2: Install Chocolatey (if not installed)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Step 3: Install sshpass
choco install sshpass -y

# Step 4: Close and reopen PowerShell
# Step 5: Navigate to project
cd C:\xampp\htdocs\kanaanerpgaza-develop

# Step 6: Run deployment
.\deploy-server.ps1
```

---

## 🔒 Security Considerations

### SFTP
- ✅ Password encrypted over SSH
- ✅ Secure file transfer
- ✅ No credentials in config (removed after connection)

### PowerShell SSH
- ⚠️ Credentials hardcoded in script
- Recommendations:
  - Keep script file safe (not in git)
  - Use environment variables for sensitive data
  - Consider SSH key-based authentication instead

### Manual SSH
- ⚠️ Credentials visible in command history
- Recommendations:
  - Use SSH key authentication
  - Clear bash history after use
  - Don't share commands with credentials

---

## 📊 Performance Comparison

| Task | SFTP | SSH Deploy | Manual SSH |
|------|------|-----------|-----------|
| File upload (100 files) | 2-3 min | Included | Manual |
| Dependency install | Manual | 1 min | 1 min |
| Build frontend | Manual | 1 min | 1 min |
| Docker restart | Manual | 1 min | 1 min |
| Total deployment | N/A | 3-5 min | 10-15 min |

---

## 🎓 Learning Path

### **Beginner**
1. Start with VS Code SFTP
2. Manually run commands to understand process
3. Graduate to PowerShell SSH

### **Intermediate**
1. Use PowerShell SSH for deployments
2. Understand each automation step
3. Customize script if needed

### **Advanced**
1. Integrate with CI/CD pipeline
2. Use SSH key pairs
3. Implement zero-downtime deployments

---

## 📞 Troubleshooting

### **SFTP Issues**
- [See `.vscode/sftp.json` config]
- Check network connection
- Verify credentials

### **SSH Issues**
- [See SSH_SETUP_GUIDE.md]
- Test connection manually
- Check sshpass installation

### **Docker Issues**
- [Connect manually via SSH]
- Run: `docker-compose logs`
- Check disk space: `df -h`

---

## 🎯 Recommendation Summary

**For this project, use:**

```
┌─────────────────────────────────────┐
│  Development:  VS Code SFTP         │
│  Deploy:       PowerShell SSH       │
│  Debug:        Manual SSH           │
└─────────────────────────────────────┘
```

**Expected workflow:**
1. Edit files → SFTP syncs
2. When ready → Run PowerShell script
3. Monitor → View logs in real-time
4. Done! ✅

---

**Last Updated:** 2024  
**Status:** ✅ All methods tested and ready