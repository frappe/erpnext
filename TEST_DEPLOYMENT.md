# 🧪 Testing Deployment Setup

Follow these steps to test your deployment infrastructure.

---

## 📋 Pre-Test Checklist

- [ ] sshpass is installed (`sshpass -V` returns version)
- [ ] PowerShell is closed and reopened after sshpass install
- [ ] You're in: `c:\xampp\htdocs\kanaanerpgaza-develop`
- [ ] `deploy-server.ps1` file exists
- [ ] Internet connection is active

---

## 🧪 Test 1: Verify sshpass Installation

```powershell
sshpass -V
```

**Expected output:**
```
sshpass 1.10 (C) 2006-2015 Shachar Shemesh
```

**If not found:**
```powershell
choco install sshpass -y
```

---

## 🧪 Test 2: Test SSH Connection

```powershell
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 "echo 'SSH Works!'"
```

**Expected output:**
```
SSH Works!
```

**If fails:**
- Check internet connection
- Verify IP: 45.159.160.5
- Verify username: esplzswx
- Verify password: q0Ju50iFb+m^6k]$
- Check if server is online

---

## 🧪 Test 3: Test Docker Connection

```powershell
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 "docker-compose ps"
```

**Expected output:**
```
NAME                COMMAND                  SERVICE      STATUS      PORTS
kanaanerpgaza-db-1  docker-entrypoint.sh ... mariadb     Up About... 3306/tcp
kanaanerpgaza-redis-1  docker-entrypoint.sh ... redis      Up About... 6379/tcp
...
```

**If fails:**
- Docker services might not be running
- Check: `docker-compose logs`

---

## 🧪 Test 4: Test Full Deployment (Dry Run)

This will show what the deployment script will do WITHOUT actually deploying:

```powershell
# Show deployment script contents
Get-Content .\deploy-server.ps1 -Head 100
```

---

## 🧪 Test 5: Run Actual Deployment

### **First Time: With Logs** (To see what's happening)

```powershell
cd C:\xampp\htdocs\kanaanerpgaza-develop
.\deploy-server.ps1 -ShowLogs:$true
```

**This will:**
- Take 5-10 minutes
- Show real-time output
- Display Docker logs at the end
- Exit with success message

**Expected final output:**
```
[+] Deployment successful!

[*] Access the application at:
    http://45.159.160.5

[*] Login credentials:
    Username: Administrator
    Password: admin
```

### **Subsequent: Without Logs** (Faster)

```powershell
.\deploy-server.ps1 -ShowLogs:$false
```

**This will:**
- Take 3-5 minutes
- Show status messages only
- No logs displayed
- Faster execution

---

## 📊 What Happens During Deployment

### **Stage 1: Verification** (30 sec)
```
[+] Verifying prerequisites...
[+] sshpass found
[+] Testing connection...
[+] Connection successful
```

### **Stage 2: Update** (1-2 min)
```
[+] Updating dependencies...
[*] Installing pip packages...
[*] Installing npm packages...
[*] Building frontend...
```

### **Stage 3: Docker** (1-2 min)
```
[+] Stopping old services...
[+] Starting Docker services...
[*] Waiting for services...
[+] Services started
```

### **Stage 4: Logs** (Optional)
```
[+] Displaying logs...
(Real-time log stream - Ctrl+C to exit)
```

### **Stage 5: Completion** (30 sec)
```
[+] Deployment successful!
[*] Access at: http://45.159.160.5
```

---

## ✅ Success Criteria

Your deployment test was successful when:

- [ ] ✅ sshpass installed
- [ ] ✅ SSH connection test passes ("SSH Works!")
- [ ] ✅ Docker connection test passes (shows containers)
- [ ] ✅ Deployment script runs without errors
- [ ] ✅ Application accessible at http://45.159.160.5
- [ ] ✅ Can login with Administrator/admin

**Estimated total time: 20-30 minutes**

---

## 🔍 Troubleshooting During Test

### **Issue: "sshpass: command not found"**
```powershell
# Solution: Reinstall and reopen PowerShell
choco install sshpass -y
# Close PowerShell completely
# Reopen PowerShell
sshpass -V  # Should work now
```

### **Issue: "Connection refused"**
```
Check:
- Internet connection is active
- Server IP is correct: 45.159.160.5
- Username is correct: esplzswx
- Password is correct: q0Ju50iFb+m^6k]$
- SSH port 22 is open (contact server admin)
```

### **Issue: "docker-compose: command not found"**
```
This means Docker isn't installed on server
Contact your server administrator
```

### **Issue: "Permission denied"**
```
The SSH user doesn't have Docker permissions
Usually needs: sudo usermod -aG docker esplzswx
Contact your server administrator
```

---

## 📈 Performance Monitoring

### **During Deployment**

```powershell
# In a separate PowerShell window, monitor real-time
sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "watch docker-compose ps"
```

### **After Deployment**

```powershell
# Check if everything is running
sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "docker-compose ps"
```

All containers should show: `Up X minutes`

---

## 🎯 Test Scenarios

### **Scenario 1: Quick Test** (5 minutes)
1. Test SSH connection
2. View Docker status
3. Skip full deployment

**Command:**
```powershell
sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "docker-compose ps"
```

### **Scenario 2: Full Test** (20-30 minutes)
1. Test SSH connection
2. Test Docker connection
3. Run full deployment with logs
4. Verify application works

**Commands:**
```powershell
# Test 1
sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "echo OK"

# Test 2
sshpass -p 'q0Ju50iFb+m^6k]$' ssh esplzswx@45.159.160.5 "docker-compose ps"

# Test 3
.\deploy-server.ps1 -ShowLogs:$true

# Test 4
# Open browser: http://45.159.160.5
# Login: Administrator / admin
```

### **Scenario 3: Production Test** (5 minutes)
```powershell
# Quick deployment without logs
.\deploy-server.ps1 -ShowLogs:$false

# Verify
.\deploy-server.ps1 -ServerHost "45.159.160.5" -ShowLogs:$false
```

---

## 📝 Test Log Template

Use this to document your test:

```
Date: ___________
Tester: ___________

Test 1: sshpass installation
  Result: ___________
  Time: ___________

Test 2: SSH connection
  Result: ___________
  Time: ___________

Test 3: Docker status
  Result: ___________
  Time: ___________

Test 4: Full deployment
  Result: ___________
  Time: ___________
  
Test 5: Application access
  URL: http://45.159.160.5
  Login: Administrator / admin
  Result: ___________

Notes:
___________________________________

Overall Result: ✅ PASS / ❌ FAIL
```

---

## 🎓 Understanding the Script Flow

```
START
  ↓
1. Check sshpass
  ├─ Found? Continue
  └─ Not found? Try fallback SSH
  ↓
2. Test SSH connection
  ├─ Success? Continue
  └─ Fail? Exit with error
  ↓
3. Update dependencies
  ├─ Run pip install
  ├─ Run npm install
  └─ Run npm build
  ↓
4. Stop old services (optional)
  └─ docker-compose down
  ↓
5. Start new services
  ├─ docker-compose up -d
  └─ Wait for services
  ↓
6. Show logs (optional)
  └─ docker-compose logs -f
  ↓
7. Display completion message
  ↓
END ✅
```

---

## 🚀 Ready? Let's Go!

**Steps to test now:**

1. Open PowerShell
2. Navigate to project:
   ```powershell
   cd C:\xampp\htdocs\kanaanerpgaza-develop
   ```
3. Run deployment:
   ```powershell
   .\deploy-server.ps1 -ShowLogs:$true
   ```
4. Wait for completion
5. Access app: http://45.159.160.5

---

## ✨ Pro Testing Tips

- 💡 Use `-ShowLogs:$false` for faster testing
- 💡 Keep SSH terminal open for live monitoring
- 💡 Test each command separately first
- 💡 Document any issues you find
- 💡 Note deployment times for baseline

---

**Expected total time: 20-30 minutes for full test**

**Good luck! 🚀**