# 🖥️ cPanel Deployment Guide - ERPNext Kanaan ERP

دليل شامل لنشر ERPNext على استضافة cPanel عبر SFTP/SSH

---

## 📋 جدول المحتويات

1. [المتطلبات](#المتطلبات)
2. [الطريقة الأولى: استخدام السكريبت (سهل)](#الطريقة-الأولى-استخدام-السكريبت)
3. [الطريقة الثانية: رفع يدوي عبر FTP](#الطريقة-الثانية-رفع-يدوي-عبر-ftp)
4. [الطريقة الثالثة: SSH Command Line](#الطريقة-الثالثة-ssh-command-line)
5. [تكوين البيئة على cPanel](#تكوين-البيئة-على-cpanel)
6. [تشغيل التطبيق](#تشغيل-التطبيق)
7. [المراقبة والصيانة](#المراقبة-والصيانة)
8. [استكشاف الأخطاء](#استكشاف-الأخطاء)

---

## 🔧 المتطلبات

### على جهازك المحلي:
- Git
- SSH/SFTP Client (أو استخدم WinSCP على Windows)
- FTP Client (مثل FileZilla)
- Terminal/Command Line

### على الخادم (cPanel):
- ✅ SSH Access
- ✅ Python 3.8+
- ✅ Node.js 14+
- ✅ MySQL/MariaDB
- ✅ Redis (اختياري لكن موصى به)
- ✅ Docker (اختياري - للتطبيقات الحديثة)

---

## 🚀 الطريقة الأولى: استخدام السكريبت (سهل)

### الخطوة 1: تحضير السكريبت

```bash
# على جهازك المحلي
cd c:\xampp\htdocs\kanaanerpgaza-develop

# تحميل السكريبت
# الملف موجود بالفعل: deploy.sh
```

### الخطوة 2: تشغيل السكريبت

**على Windows (باستخدام Git Bash أو WSL):**
```bash
chmod +x deploy.sh
./deploy.sh
```

**على Mac/Linux:**
```bash
chmod +x deploy.sh
./deploy.sh
```

### الخطوة 3: متابعة السكريبت

السكريبت سيطلب منك:
```
1. SFTP Host (مثل: sftpssh user@kanaanerpgaza.espl.ps
cd public_html
git clone https://...
npm ci
docker-compose up -d
.kanaanerpgaza.espl.ps)
2. SFTP Username
3. SFTP Password
4. Remote Path (مثل: /public_html)
5. Domain Name (mثل: kanaanerpgaza.espl.ps)
6. Database Details
7. Environment Mode (production/development)
```

**ستكون لديك خيارات بسيطة تتابع معك! ✅**

---

## 📤 الطريقة الثانية: رفع يدوي عبر FTP

### الخطوة 1: استخدام FileZilla (سهل جداً)

1. **تحميل FileZilla:**
   - اذهب إلى: https://filezilla-project.org/download.php
   - حمّل النسخة المناسبة لنظام التشغيل

2. **إدخال بيانات الوصول:**
   ```
   Host: sftp://your-domain.com  (أو IP)
   Username: cpanel_username
   Password: cpanel_password
   Port: 22 (إذا كنت تستخدم SFTP)
   ```

3. **الاتصال:**
   - اضغط "Quickconnect"
   - ستظهر الملفات على يمين الشاشة

4. **رفع الملفات:**
   - **المجلدات الرئيسية:**
     - `erpnext/` → `/public_html/erpnext/`
     - `docker-compose.yml` → `/public_html/`
     - `Dockerfile` → `/public_html/`
   
   - **ملفات الإعدادات:**
     - `.env.example` → `.env` (بعد التعديل)
     - `docker-entrypoint.sh` → `/public_html/`
     - `nginx.conf` → `/public_html/`
     - `requirements.txt` → `/public_html/`

5. **تعيين الأذونات:**
   - انقر يميناً على الملفات
   - اختر "File Attributes"
   - اضبط الأذونات:
     - Directories: 755
     - Files: 644
     - Scripts: 755

---

## 💻 الطريقة الثالثة: SSH Command Line

### الخطوة 1: الاتصال عبر SSH

```bash
# على Terminal/PowerShell
ssh user@your-domain.com
```

### الخطوة 2: استنساخ المشروع مباشرة

```bash
# الانتقال إلى المجلد
cd public_html

# استنساخ من GitHub (إذا كان المشروع علي GitHub)
git clone https://github.com/your-username/kanaanerpgaza.git .

# أو تحميل ملف ZIP ثم فك الضغط
wget https://github.com/your-username/kanaanerpgaza/archive/main.zip
unzip main.zip
```

### الخطوة 3: تثبيت المتطلبات

```bash
# تثبيت Python dependencies
pip3 install -r requirements.txt

# تثبيت Node dependencies
npm ci --production

# بناء الأصول
npm run build
```

### الخطوة 4: إعداد قاعدة البيانات

```bash
# إنشاء قاعدة بيانات جديدة (عبر cPanel أو MySQL CLI)
mysql -u root -p

# داخل MySQL:
CREATE DATABASE kanaan_erpnext;
CREATE USER 'erpnext'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON kanaan_erpnext.* TO 'erpnext'@'localhost';
FLUSH PRIVILEGES;
exit;
```

---

## ⚙️ تكوين البيئة على cPanel

### الخطوة 1: إنشاء ملف .env

```bash
# على الخادم (عبر SSH)
cd public_html

# نسخ الملف النموذجي
cp .env.example .env

# تعديل الملف بمحرر nano
nano .env
```

### الخطوة 2: ملء البيانات

```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=kanaan_erpnext
DB_USER=erpnext
DB_PASSWORD=your-strong-password
DB_ROOT_PASSWORD=your-root-password

# Redis
REDIS_CACHE=localhost:6379
REDIS_QUEUE=localhost:6380

# Site Configuration
SITE_NAME=kanaanerpgaza.espl.ps
FRAPPE_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Ports
BACKEND_PORT=8000
NGINX_PORT=80
NGINX_HTTPS_PORT=443

# Node
NODE_ENV=production
```

### الخطوة 3: حفظ الملف

```
اضغط: Ctrl + X
اختر: Y (نعم)
اضغط: Enter
```

---

## 🚀 تشغيل التطبيق

### الخيار 1: استخدام Docker Compose (الأفضل)

```bash
# التأكد من تثبيت Docker
docker --version
docker-compose --version

# تشغيل جميع الخدمات
docker-compose up -d

# التحقق من الحالة
docker-compose ps
```

### الخيار 2: بدون Docker (إذا كان غير متوفر)

```bash
# تشغيل Gunicorn
gunicorn --config gunicorn.conf.py wsgi:application &

# تشغيل Nginx (اختياري)
sudo systemctl start nginx

# تشغيل Redis
redis-server --daemonize yes

# تشغيل Worker
bench worker --queue long,default,short &

# تشغيل Scheduler
bench schedule &
```

---

## 📊 تكوين Apache/Nginx على cPanel

### في cPanel (EasyApache):

1. **إضافة Proxy:**
   ```apache
   ProxyPreserveHost On
   ProxyPass / http://127.0.0.1:8000/
   ProxyPassReverse / http://127.0.0.1:8000/
   ```

2. **تفعيل mod_proxy:**
   - اذهب إلى WHM
   - اختر EasyApache 4
   - تأكد من تفعيل `mod_proxy`

3. **SSL/HTTPS:**
   - اذهب إلى AutoSSL
   - فعّل الشهادة التلقائية

---

## 🔍 المراقبة والصيانة

### عرض السجلات

```bash
# سجلات Docker
docker-compose logs -f

# سجلات Gunicorn
tail -f /home/username/public_html/logs/gunicorn.log

# سجلات Nginx
tail -f /var/log/nginx/error.log
```

### النسخ الاحتياطية

```bash
# تصدير قاعدة البيانات
mysqldump -u erpnext -p kanaan_erpnext > backup_$(date +%Y%m%d).sql

# حفظ الملفات
tar -czf files_backup_$(date +%Y%m%d).tar.gz private/files/

# نقل النسخة الاحتياطية إلى جهازك
scp user@server:~/backup_*.sql .
```

### إعادة التشغيل

```bash
# إعادة تشغيل Docker
docker-compose restart

# أو إعادة خدمة معينة
docker-compose restart backend
```

---

## 🆘 استكشاف الأخطاء

### المشكلة: "Connection refused on port 8000"

```bash
# تحقق من حالة الخدمة
docker-compose ps

# قد تحتاج إلى إعادة التشغيل
docker-compose restart backend

# تحقق من الأخطاء
docker-compose logs backend
```

### المشكلة: "Database connection error"

```bash
# تحقق من بيانات .env
cat .env | grep DB_

# اختبر الاتصال
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D $DB_NAME

# إعادة تشغيل قاعدة البيانات
docker-compose restart db
```

### المشكلة: "Port already in use"

```bash
# غير المنفذ في .env
# مثل: BACKEND_PORT=8001

# أو تحقق من العملية المستخدمة
lsof -i :8000

# اقتل العملية إن لزم
kill -9 <PID>
```

### المشكلة: "High Memory Usage"

```bash
# قلل عدد Workers في gunicorn.conf.py
# من: workers = 4
# إلى: workers = 2

# أو قلل من redis cache
docker-compose down
docker-compose up -d
```

---

## 📝 Troubleshooting Checklist

- [ ] تحقق من ssh access
- [ ] تحقق من Python version (3.8+)
- [ ] تحقق من Node.js version (14+)
- [ ] اختبر MySQL connection
- [ ] فعّل Redis (إن أمكن)
- [ ] تحقق من الأذونات (755 للمجلدات، 644 للملفات)
- [ ] تحقق من .env file
- [ ] تحقق من Docker installation
- [ ] تحقق من Port availability
- [ ] راجع السجلات الكاملة

---

## 🔗 روابط مفيدة

- 📖 [Frappe Bench Installation](https://frappeframework.com)
- 📖 [Docker Documentation](https://docs.docker.com)
- 🖥️ [cPanel Documentation](https://docs.cpanel.net)
- 💬 [Frappe Community](https://discuss.frappe.io)

---

## ✅ Checklist ما قبل الإطلاق

- [ ] قاعدة البيانات تعمل
- [ ] .env file معروّف
- [ ] الملفات مرفوعة بشكل كامل
- [ ] الأذونات صحيحة
- [ ] Docker Compose يعمل
- [ ] التطبيق يستجيب على الرابط
- [ ] SSL/HTTPS مفعّل
- [ ] النسخ الاحتياطية معدّة
- [ ] المراقبة مفعّلة

---

## 🎯 الخطوات التالية

1. **قم بتشغيل deploy.sh** (الطريقة الأسهل)
2. **أو اتبع الطرق اليدوية** حسب تفضيلك
3. **تحقق من تشغيل التطبيق**
4. **عيّن نطاقك الإضافية**
5. **فعّل SSL**
6. **قم برعاية النسخ الاحتياطية**

---

**تم آخر تحديث:** 2024
**إصدار:** ERPNext v15.85.1