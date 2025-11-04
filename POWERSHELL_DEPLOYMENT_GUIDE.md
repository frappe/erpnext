# 🔵 دليل النشر عبر PowerShell من Windows

استخدام PowerShell النصي لنشر Kanaan ERP على السيرفر بشكل مؤتمت

---

## 📋 المتطلبات الأولية

### على جهازك (Windows)
1. **PowerShell 5.0+** (مدمج في Windows 10+)
2. **sshpass** مثبت (أو Git Bash)
3. **الوصول للسيرفر** (SSH مفتوح)

---

## ⚙️ خطوة 1: تثبيت sshpass

### **الطريقة الأولى: Chocolatey (الموصى به)**

```powershell
# 1. فتح PowerShell كـ Administrator
# 2. تشغيل الأمر التالي:

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 3. إغلاق وفتح PowerShell جديد
# 4. تثبيت sshpass:

choco install sshpass -y

# 5. التحقق:
sshpass -V
```

### **الطريقة الثانية: Git Bash (إذا كان مثبتاً)**

استخدم Git Bash مباشرة عبر PowerShell:

```powershell
# لا تحتاج لتثبيت شيء، استخدم مباشرة:
& "C:\Program Files\Git\usr\bin\sshpass.exe" -V
```

---

## 🧪 خطوة 2: اختبار الاتصال

```powershell
# اختبر الاتصال بالسيرفر
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 "echo 'SSH Connection OK!'"

# يجب أن ترى النتيجة:
# SSH Connection OK!
```

إذا فشل، تحقق من:
- ✅ IP صحيح: `45.159.160.5`
- ✅ اسم المستخدم صحيح: `esplzswx`
- ✅ كلمة المرور صحيحة: `q0Ju50iFb+m^6k]$`
- ✅ السيرفر متصل بالإنترنت

---

## 🚀 خطوة 3: استخدام سكريبت النشر

### **الطريقة الأولى: استخدام السكريبت المرفق**

```powershell
# 1. اذهب إلى مجلد المشروع
cd C:\xampp\htdocs\kanaanerpgaza-develop

# 2. قم بتشغيل سكريبت النشر:
# مع عرض السجلات (موصى به في البداية)
.\deploy-server.ps1 -ShowLogs:$true

# أو بدون سجلات (أسرع)
.\deploy-server.ps1 -ShowLogs:$false

# أو مع خيارات مخصصة
.\deploy-server.ps1 -ServerHost "45.159.160.5" -Username "esplzswx" -ShowLogs:$true
```

### **الطريقة الثانية: أوامر يدوية**

إذا لم تريد استخدام السكريبت:

```powershell
# 1. الاتصال بالسيرفر
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5

# 2. بعد الاتصال، نفذ الأوامر التالية:
cd /home/esplzswx/kanaanerpgaza-develop
git pull origin main
docker-compose down
docker-compose up -d
docker-compose logs -f
```

---

## 📊 معاملات السكريبت

```powershell
.\deploy-server.ps1 `
    -ServerHost "45.159.160.5" `        # عنوان السيرفر
    -Username "esplzswx" `               # اسم المستخدم
    -Password "q0Ju50iFb+m^6k]$" `      # كلمة المرور
    -RemotePath "/home/esplzswx/kanaanerpgaza-develop" `  # مسار المشروع
    -ShowLogs:$true `                   # عرض السجلات
    -NoDowntime:$false                  # عدم وقف الخدمات
```

### شرح المعاملات:

| المعامل | القيمة الافتراضية | الشرح |
|--------|-----------------|-------|
| `-ServerHost` | 45.159.160.5 | عنوان IP أو اسم النطاق |
| `-Username` | esplzswx | اسم المستخدم SSH |
| `-Password` | محدد مسبقاً | كلمة المرور (اختياري، مخزن في السكريبت) |
| `-RemotePath` | /home/esplzswx/... | مسار المشروع على السيرفر |
| `-ShowLogs` | $true | عرض السجلات الحية |
| `-NoDowntime` | $false | لا توقف للخدمات (نشر بدون انقطاع) |

---

## 🎯 سيناريوهات الاستخدام الشائعة

### **السيناريو 1: النشر البسيط (موصى به للبداية)**

```powershell
cd C:\xampp\htdocs\kanaanerpgaza-develop
.\deploy-server.ps1
```

هذا سيقوم بـ:
- ✅ الاتصال بالسيرفر
- ✅ إيقاف الخدمات القديمة
- ✅ تحديث الأكواد
- ✅ تثبيت المتطلبات
- ✅ بدء الخدمات الجديدة
- ✅ عرض السجلات الحية

### **السيناريو 2: النشر السريع (بدون سجلات)**

```powershell
.\deploy-server.ps1 -ShowLogs:$false
```

هذا أسرع للنشر الدوري المعروف أنه يعمل.

### **السيناريو 3: النشر بدون انقطاع**

```powershell
.\deploy-server.ps1 -NoDowntime:$true -ShowLogs:$true
```

هذا يحافظ على الخدمات تعمل أثناء التحديث (متقدم).

### **السيناريو 4: نشر إلى سيرفر مختلف**

```powershell
.\deploy-server.ps1 `
    -ServerHost "new.server.ip" `
    -Username "newuser" `
    -RemotePath "/path/to/project"
```

---

## 🔄 النشر الدوري المؤتمت

### إعداد مهمة Windows المجدولة

```powershell
# 1. فتح PowerShell كـ Administrator

# 2. إنشاء إجراء النشر
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "C:\xampp\htdocs\kanaanerpgaza-develop\deploy-server.ps1 -ShowLogs:`$false"

# 3. إنشاء وقت التشغيل (مثل الساعة 2 صباحاً يومياً)
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At 2:00AM

# 4. تسجيل المهمة
Register-ScheduledTask `
    -TaskName "Kanaan ERP Daily Deploy" `
    -Action $action `
    -Trigger $trigger `
    -RunLevel Highest

# 5. التحقق من تسجيل المهمة
Get-ScheduledTask -TaskName "Kanaan ERP Daily Deploy"
```

### إدارة المهام المجدولة

```powershell
# قائمة بالمهام
Get-ScheduledTask -TaskName "Kanaan*"

# تشغيل المهمة يدويًا
Start-ScheduledTask -TaskName "Kanaan ERP Daily Deploy"

# إيقاف المهمة
Stop-ScheduledTask -TaskName "Kanaan ERP Daily Deploy"

# حذف المهمة
Unregister-ScheduledTask -TaskName "Kanaan ERP Daily Deploy" -Confirm:$false
```

---

## 📝 كتابة سكريبت نشر مخصص

إذا أردت سكريبت مخصص:

```powershell
# انسخ الكود التالي في ملف: my-deploy.ps1

param(
    [string]$ServerHost = "45.159.160.5",
    [string]$Username = "esplzswx",
    [string]$Password = "q0Ju50iFb+m^6k]$"
)

function Write-Status {
    param([string]$Message, [string]$Color = "Green")
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

# 1. اختبر الاتصال
Write-Status "اختبار الاتصال بالسيرفر..." "Cyan"
sshpass -p $Password ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" "echo OK" | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Status "✓ الاتصال ناجح!" "Green"
} else {
    Write-Status "✗ فشل الاتصال!" "Red"
    exit 1
}

# 2. نفذ الأوامر على السيرفر
Write-Status "بدء النشر..." "Cyan"

$commands = @(
    "cd /home/esplzswx/kanaanerpgaza-develop",
    "git pull origin main",
    "docker-compose down",
    "docker-compose up -d",
    "docker-compose logs -f --tail=50"
)

$commandString = $commands -join "; "

sshpass -p $Password ssh -o StrictHostKeyChecking=no "$Username@$ServerHost" $commandString

if ($LASTEXITCODE -eq 0) {
    Write-Status "✓ النشر نجح!" "Green"
} else {
    Write-Status "✗ فشل النشر!" "Red"
    exit 1
}

Write-Status "انتهى النشر" "Green"
```

ثم شغله:
```powershell
.\my-deploy.ps1
```

---

## 🔒 أمان السكريبت

### ⚠️ تحذير: كلمة المرور في الملف

السكريبت يحتوي على كلمة مرور مكتوبة. لتحسين الأمان:

### **الطريقة الأولى: استخدام متغيرات البيئة**

```powershell
# عيّن المتغير
$env:DEPLOY_PASSWORD = "q0Ju50iFb+m^6k]$"

# استخدم في السكريبت
sshpass -p $env:DEPLOY_PASSWORD ssh ...
```

### **الطريقة الثانية: استخدام SSH Keys (الأفضل)**

```powershell
# 1. إنشاء مفاتيح SSH
ssh-keygen -t rsa -b 4096 -f $env:USERPROFILE\.ssh\id_rsa

# 2. نسخ المفتاح العام للسيرفر
scp "$env:USERPROFILE\.ssh\id_rsa.pub" esplzswx@45.159.160.5:~/

# 3. على السيرفر (SSH إليه)
ssh esplzswx@45.159.160.5
cat ~/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 4. الآن استخدم SSH بدون كلمة مرور
ssh esplzswx@45.159.160.5 "echo OK"
```

### **الطريقة الثالثة: Windows Credential Manager**

```powershell
# حفظ بيانات الاعتماد
cmdkey /add:45.159.160.5 /user:esplzswx /pass:"q0Ju50iFb+m^6k]$"

# عرض بيانات الاعتماد المحفوظة
cmdkey /list:45.159.160.5

# حذف بيانات الاعتماد
cmdkey /delete:45.159.160.5
```

---

## 🐛 استكشاف الأخطاء

### المشكلة: "sshpass is not recognized"

```powershell
# الحل 1: تحقق من التثبيت
sshpass -V

# الحل 2: استخدم المسار الكامل
& "C:\Program Files (x86)\GNU\sshpass\sshpass.exe" -V

# الحل 3: أضفه إلى PATH
$env:Path += ";C:\Program Files (x86)\GNU\sshpass"
sshpass -V
```

### المشكلة: "Connection refused"

```powershell
# تحقق من:
# 1. IP صحيح
ping 45.159.160.5

# 2. المنفذ مفتوح
telnet 45.159.160.5 22

# 3. بيانات الاعتماد صحيحة
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -v esplzswx@45.159.160.5
```

### المشكلة: "Execution policy prevents running scripts"

```powershell
# اسمح بتنفيذ السكريبتات (من Admin PowerShell)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# أو للجلسة الحالية فقط
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
```

---

## 📊 نصائح لزيادة الكفاءة

### 1. إنشاء Batch File

```batch
@echo off
REM save as: deploy.bat
cd C:\xampp\htdocs\kanaanerpgaza-develop
powershell -ExecutionPolicy Bypass -File deploy-server.ps1 -ShowLogs:$false
pause
```

ثم شغله بـ: `deploy.bat`

### 2. إنشاء Shortcut

- انقر يمين على سطح المكتب → New → Shortcut
- الموقع: `powershell.exe -ExecutionPolicy Bypass -File "C:\xampp\htdocs\kanaanerpgaza-develop\deploy-server.ps1"`
- الاسم: "Deploy Kanaan ERP"

### 3. دمج مع نظام CI/CD

```yaml
# في GitHub Actions
- name: Deploy to Server
  run: |
    powershell -Command {
        $ScriptPath = "C:\xampp\htdocs\kanaanerpgaza-develop\deploy-server.ps1"
        & $ScriptPath -ShowLogs:$false
    }
```

---

## 📈 المراقبة المستمرة

### السجلات على السيرفر

```powershell
# مشاهدة السجلات الحية
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 `
    "cd /home/esplzswx/kanaanerpgaza-develop && docker-compose logs -f"

# سجلات خدمة محددة
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 `
    "docker-compose logs -f backend"
```

### سكريبت مراقبة دوري

```powershell
# save as: monitor.ps1

param([int]$IntervalSeconds = 300)  # كل 5 دقائق

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] Checking server status..."
    
    sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5 `
        "docker-compose ps" | Out-File "monitor-log.txt" -Append
    
    Start-Sleep -Seconds $IntervalSeconds
}
```

---

## ✅ قائمة التحقق

```
☑️ sshpass مثبت
☑️ الاتصال بالسيرفر يعمل
☑️ سكريبت النشر موجود
☑️ الصلاحيات للتنفيذ موجودة
☑️ بيانات الاعتماد صحيحة
☑️ Docker مثبت على السيرفر
☑️ قاعدة البيانات موجودة
☑️ النسخة الاحتياطية الأولى موجودة
```

---

**آخر تحديث:** 2024  
**الحالة:** ✅ جاهز للإنتاج  
**اللغة:** العربية والإنجليزية