# 🚀 خطوات التثبيت اليدوي لتطبيق Kanaan ERP على السيرفر

دليل شامل لتثبيت تطبيق Kanaan ERP يدويًا على السيرفر خطوة بخطوة

---

## 📊 معلومات السيرفر

| المعلومة | القيمة |
|---------|--------|
| **IP Address** | 45.159.160.5 |
| **Username** | esplzswx |
| **Password** | q0Ju50iFb+m^6k]$ |
| **SSH Port** | 22 |
| **Project Path** | /home/esplzswx/kanaanerpgaza-develop |
| **الوصول للتطبيق** | http://45.159.160.5 |

---

## 🔑 المتطلبات الأساسية

- **نظام التشغيل**: Linux (Ubuntu 20.04 أو أحدث)
- **Python**: 3.10+
- **Node.js**: 18+
- **Git**
- **Docker و Docker Compose**
- **MySQL/MariaDB** أو **PostgreSQL**
- **Redis**

---

## 📝 الخطوات التفصيلية

### **الخطوة 1️⃣: الاتصال بالسيرفر عبر SSH**

من جهازك على Windows، استخدم PowerShell:

```powershell
# من Windows PowerShell
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5

# أو من أي جهاز Linux/Mac
ssh esplzswx@45.159.160.5
# ثم أدخل كلمة المرور عند الطلب
```

**بعد الاتصال الناجح، ستظهر لك واجهة السيرفر:**
```
esplzswx@server:~$
```

---

### **الخطوة 2️⃣: تحديث نظام التشغيل**

```bash
# تحديث قوائم الحزم
sudo apt update

# ترقية الحزم المثبتة
sudo apt upgrade -y

# تثبيت الأدوات الأساسية
sudo apt install -y build-essential curl wget git
```

---

### **الخطوة 3️⃣: تثبيت Python وأدواته**

```bash
# تثبيت Python 3.10+
sudo apt install -y python3.10 python3-pip python3-dev

# التحقق من الإصدار
python3 --version

# ترقية pip
sudo pip3 install --upgrade pip setuptools wheel
```

---

### **الخطوة 4️⃣: تثبيت Node.js و npm**

```bash
# تثبيت Node.js 18+
sudo apt install -y nodejs npm

# التحقق من الإصدار
node --version
npm --version

# ترقية npm
sudo npm install -g npm@latest
```

---

### **الخطوة 5️⃣: تثبيت Docker و Docker Compose**

```bash
# تثبيت Docker
sudo apt install -y docker.io

# إضافة المستخدم الحالي إلى مجموعة Docker
sudo usermod -aG docker esplzswx

# تثبيت Docker Compose
sudo apt install -y docker-compose

# التحقق من الإصدارات
docker --version
docker-compose --version

# إعادة تشغيل الخدمة
sudo systemctl restart docker
```

---

### **الخطوة 6️⃣: تثبيت MySQL/MariaDB**

اختر أحد الخيارين:

#### **الخيار A: MariaDB (الموصى به)**
```bash
sudo apt install -y mariadb-server mariadb-client

# بدء الخدمة
sudo systemctl start mariadb
sudo systemctl enable mariadb

# تأمين التثبيت (اختياري)
sudo mysql_secure_installation
```

#### **الخيار B: MySQL 8.0**
```bash
sudo apt install -y mysql-server mysql-client

# بدء الخدمة
sudo systemctl start mysql
sudo systemctl enable mysql
```

---

### **الخطوة 7️⃣: تثبيت Redis**

```bash
# تثبيت Redis
sudo apt install -y redis-server redis-tools

# بدء الخدمة
sudo systemctl start redis-server
sudo systemctl enable redis-server

# التحقق من الحالة
redis-cli ping
# يجب أن يرجع: PONG
```

---

### **الخطوة 8️⃣: استنساخ مشروع Kanaan ERP**

```bash
# الانتقال إلى المجلد الرئيسي
cd /home/esplzswx

# استنساخ المستودع
git clone https://github.com/your-repo/kanaanerpgaza-develop.git

# الانتقال إلى مجلد المشروع
cd kanaanerpgaza-develop

# التحقق من محتوى المشروع
ls -la
```

**المشاريع المتوقعة:**
```
.
├── erpnext/              # مشروع ERPNext الرئيسي
├── tests/                # اختبارات التطبيق
├── Dockerfile            # ملف بناء Docker
├── docker-compose.yml    # ملف تشغيل الخدمات
├── requirements.txt      # متطلبات Python
├── package.json          # متطلبات Node.js
└── playwright.config.js  # إعدادات الاختبارات
```

---

### **الخطوة 9️⃣: إعداد متغيرات البيئة**

```bash
# نسخ ملف البيئة النموذجي
cp .env.example .env

# تحرير الملف (اختياري - إذا أردت تغيير الإعدادات)
nano .env
```

**المتغيرات الأساسية في `.env`:**
```env
# قاعدة البيانات
DB_HOST=localhost
DB_NAME=kanaan_erpnext
DB_USER=erpnext
DB_PASSWORD=secure_password
DB_PORT=3306

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# تكوين التطبيق
FRAPPE_ENV=production
SECRET_KEY=your-secret-key
DEBUG=false

# الموقع
SITE_NAME=45.159.160.5
```

---

### **الخطوة 🔟: إنشاء قاعدة البيانات والمستخدم**

#### إذا كنت تستخدم **MariaDB/MySQL**:

```bash
# الاتصال بـ MySQL
mysql -u root -p

# أو بدون كلمة المرور إذا لم تضع واحدة
mysql -u root
```

**بعد الدخول إلى MySQL، نفذ الأوامر التالية:**

```sql
-- إنشاء قاعدة البيانات
CREATE DATABASE kanaan_erpnext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- إنشاء المستخدم
CREATE USER 'erpnext'@'localhost' IDENTIFIED BY 'secure_password';

-- منح الصلاحيات
GRANT ALL PRIVILEGES ON kanaan_erpnext.* TO 'erpnext'@'localhost';

-- تطبيق التغييرات
FLUSH PRIVILEGES;

-- التحقق
SHOW DATABASES;
SHOW GRANTS FOR 'erpnext'@'localhost';

-- الخروج
EXIT;
```

---

### **الخطوة 1️⃣1️⃣: تثبيت متطلبات Python**

```bash
# الانتقال إلى مجلد المشروع
cd /home/esplzswx/kanaanerpgaza-develop

# إنشاء بيئة افتراضية (اختياري لكن موصى به)
python3 -m venv venv

# تفعيل البيئة الافتراضية
source venv/bin/activate

# تثبيت المتطلبات
pip install -r requirements.txt

# ترقية Frappe Bench (إذا لزم الأمر)
pip install frappe-bench --upgrade
```

---

### **الخطوة 1️⃣2️⃣: تثبيت متطلبات Node.js**

```bash
# تثبيت المكتبات
npm ci  # أفضل من npm install للإنتاج

# أو
npm install

# بناء الواجهة الأمامية
npm run build
```

---

### **الخطوة 1️⃣3️⃣: بدء التطبيق باستخدام Docker Compose**

#### **الخيار A: بدء جميع الخدمات**

```bash
# من مجلد المشروع
cd /home/esplzswx/kanaanerpgaza-develop

# بدء جميع الخدمات في الخلفية
docker-compose up -d

# التحقق من حالة الخدمات
docker-compose ps

# عرض السجلات
docker-compose logs -f
```

**الخدمات التي ستبدأ:**
```
✅ Nginx (Web Server) - Port 8080
✅ Gunicorn (Python Backend) - Port 8000
✅ MariaDB (Database) - Port 3306
✅ Redis (Cache) - Port 6379
✅ Redis Queue - Port 6380
✅ Node.js WebSocket Server
✅ Scheduler & Queue Workers
```

#### **الخيار B: بدء الخدمات بدون Docker**

إذا لم تستخدم Docker:

```bash
# تفعيل البيئة الافتراضية
source venv/bin/activate

# بدء Gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 wsgi:application &

# بدء Celery Worker (في terminal منفصل)
celery -A erpnext worker -l info &

# بدء Celery Beat (في terminal منفصل)
celery -A erpnext beat -l info &

# بدء Nginx (يجب تشغيل بصلاحيات root)
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

### **الخطوة 1️⃣4️⃣: التحقق من التطبيق**

```bash
# اختبر الاتصال بـ Nginx
curl http://localhost:8080

# اختبر الاتصال بـ Backend
curl http://localhost:8000

# اختبر قاعدة البيانات
mysql -u erpnext -p kanaan_erpnext -e "SHOW TABLES;"

# اختبر Redis
redis-cli ping
```

---

### **الخطوة 1️⃣5️⃣: تهيئة قاعدة البيانات (إن لزم الأمر)**

إذا كنت تستخدم Docker:

```bash
# الدخول إلى حاوية Backend
docker-compose exec backend bash

# تشغيل الترحيلات
python manage.py migrate

# إنشاء مستخدم بيانات
python manage.py createsuperuser
```

---

### **الخطوة 1️⃣6️⃣: الوصول للتطبيق**

بعد اتمام جميع الخطوات، يمكنك الوصول للتطبيق عبر:

```
🌐 الرابط: http://45.159.160.5
📧 اسم المستخدم: Administrator
🔑 كلمة المرور: admin
🌍 اللغة: العربية (RTL)
```

---

## 🔧 الأوامر المفيدة أثناء التشغيل

### **مراقبة الخدمات**

```bash
# عرض حالة الخدمات
docker-compose ps

# عرض السجلات الحية
docker-compose logs -f

# عرض سجلات خدمة محددة
docker-compose logs -f backend
docker-compose logs -f database
docker-compose logs -f redis

# استخدام top لمراقبة الموارد
docker stats
```

### **إعادة تشغيل الخدمات**

```bash
# إعادة تشغيل جميع الخدمات
docker-compose restart

# إعادة تشغيل خدمة محددة
docker-compose restart backend
docker-compose restart database

# إيقاف الخدمات
docker-compose down

# بدء الخدمات مجددًا
docker-compose up -d
```

### **نسخ احتياطي واستعادة**

```bash
# نسخ احتياطي من قاعدة البيانات
docker-compose exec database mysqldump -u erpnext -p kanaan_erpnext > backup.sql

# استعادة قاعدة البيانات
docker-compose exec database mysql -u erpnext -p kanaan_erpnext < backup.sql

# نسخ احتياطي من الملفات
tar -czf kanaan-backup.tar.gz /home/esplzswx/kanaanerpgaza-develop
```

---

## 🛠️ استكشاف الأخطاء والمشاكل

### **المشكلة: فشل الاتصال بقاعدة البيانات**

```bash
# تحقق من حالة خدمة MariaDB
sudo systemctl status mariadb

# اختبر الاتصال
mysql -u erpnext -p kanaan_erpnext -e "SELECT 1;"

# تحقق من متغيرات البيئة
cat .env | grep DB_
```

### **المشكلة: منفذ مشغول (Port Already in Use)**

```bash
# ابحث عن العملية التي تستخدم المنفذ
sudo lsof -i :8080
sudo lsof -i :8000

# إيقف العملية
sudo kill -9 PID

# أو غير المنفذ في docker-compose.yml
```

### **المشكلة: الأداء بطيء**

```bash
# تحقق من استخدام الموارد
docker stats

# قلل عدد workers
# عدّل في docker-compose.yml

# تحقق من حجم السجلات
docker system prune -a

# امسح الكاش
redis-cli FLUSHALL
```

### **المشكلة: SSL Certificate Errors**

```bash
# إذا كنت تستخدم Let's Encrypt
sudo certbot certonly --standalone -d 45.159.160.5

# أو في Docker:
docker-compose exec certbot certbot certonly --standalone -d your-domain
```

---

## 📊 فحص صحة النظام

```bash
# سكريبت للفحص الشامل
#!/bin/bash
echo "=== System Health Check ==="
echo ""
echo "✓ Disk Space:"
df -h /

echo ""
echo "✓ Memory Usage:"
free -h

echo ""
echo "✓ Docker Services:"
docker-compose ps

echo ""
echo "✓ Database Connection:"
mysql -u erpnext -p kanaan_erpnext -e "SELECT 'Connected' as Status;"

echo ""
echo "✓ Redis Status:"
redis-cli ping

echo ""
echo "✓ Web Server:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080

echo ""
echo "=== Check Complete ==="
```

احفظ هذا الملف بـ `health-check.sh` ونفذه:
```bash
chmod +x health-check.sh
./health-check.sh
```

---

## 🔐 تأمين السيرفر

```bash
# تحديث جدار الحماية
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp
sudo ufw enable

# تفعيل SSH Key Authentication (بدلاً من Password)
ssh-keygen -t rsa -b 4096

# نسخ المفتاح العام إلى السيرفر
ssh-copy-id -i ~/.ssh/id_rsa.pub esplzswx@45.159.160.5

# تعطيل كلمة المرور في SSH (اختياري)
sudo nano /etc/ssh/sshd_config
# ابحث عن: PasswordAuthentication yes
# غيرها إلى: PasswordAuthentication no
# احفظ واخرج
sudo systemctl restart ssh
```

---

## 📈 خطوات بعد التثبيت

1. **تحديث البيانات الأساسية**
   - أضف العملاء والمنتجات
   - أعد إعدادات الشركة

2. **إعداد النسخ الاحتياطية**
   - أعد جدول للنسخ الاحتياطية اليومية
   - احفظ النسخ في مكان آمن

3. **المراقبة المستمرة**
   - ضع نبيهات على الأداء
   - تابع سجلات الأخطاء

4. **التطوير والتحديثات**
   - شغّل الاختبارات
   - نفّذ التحديثات بانتظام

---

## 📞 جهات الاتصال والدعم

| الموضوع | الطريقة |
|--------|--------|
| **المساعدة التقنية** | البحث في الوثائق أو GitHub Issues |
| **البلاغات عن الأخطاء** | فتح Issue في المستودع |
| **الأسئلة العامة** | المنتدى أو Discussions |

---

## ✅ قائمة التحقق النهائية

```
✅ تحديث النظام
✅ تثبيت Python و Node.js
✅ تثبيت Docker و Docker Compose
✅ تثبيت قاعدة البيانات و Redis
✅ استنساخ المشروع
✅ إعداد متغيرات البيئة
✅ إنشاء قاعدة البيانات
✅ تثبيت متطلبات Python و npm
✅ بدء الخدمات
✅ الوصول للتطبيق
✅ تأمين السيرفر
```

---

**آخر تحديث:** 2024  
**الحالة:** ✅ جاهز للإنتاج  
**اللغة:** العربية والإنجليزية