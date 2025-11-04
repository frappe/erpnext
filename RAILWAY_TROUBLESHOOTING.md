# 🔧 Railway Deployment - Troubleshooting Guide

استخدم هذا الدليل لحل المشاكل الشائعة عند نشر على Railway.com

---

## 📋 جدول المحتويات

1. [مشاكل البناء (Build)](#مشاكل-البناء)
2. [مشاكل التشغيل (Runtime)](#مشاكل-التشغيل)
3. [مشاكل قاعدة البيانات](#مشاكل-قاعدة-البيانات)
4. [مشاكل الـ Performance](#مشاكل-الـ-performance)
5. [مشاكل الـ Networking](#مشاكل-الـ-networking)

---

## 🏗️ مشاكل البناء

### ❌ Build Timeout (البناء يستغرق وقتاً طويلاً)

**الأعراض:**
```
Build failed after 45 minutes
```

**الحلول:**
```bash
# 1. تقليل حجم الـ Docker image
# في Dockerfile:
FROM python:3.10-slim  # ✅ استخدم slim بدلاً من latest

# 2. تحسين التخزين المؤقت
# في railway.json:
{
  "buildCommand": "npm ci --prefer-offline && pip install -q -r requirements.txt"
}

# 3. تقليل المكتبات غير الضرورية
# في requirements.txt:
# احذف المكتبات المستخدمة فقط في التطوير
```

### ❌ Build fails: "npm: not found"

**الأعراض:**
```
sh: npm: not found
```

**الحل:**
```bash
# تأكد من تثبيت Node في Dockerfile
RUN apt-get install -y --no-install-recommends \
    nodejs \
    npm
```

### ❌ Build fails: "Could not find Python"

**الأعراض:**
```
E: Unable to locate package python3.10-dev
```

**الحل:**
```bash
# استخدم صورة Python رسمية
FROM python:3.10-slim  # ✅ بدلاً من البناء من الصفر
```

---

## 🚀 مشاكل التشغيل

### ❌ Application crashes: "ModuleNotFoundError"

**الأعراض:**
```
ModuleNotFoundError: No module named 'frappe'
```

**الحلول:**

```bash
# 1. تأكد من requirements.txt
cat requirements.txt | grep frappe

# 2. تأكد من buildCommand في railway.json
"buildCommand": "pip install -q -r requirements.txt"

# 3. تفقد الـ Logs
railway logs

# 4. أضفها يدوياً إذا لزم
railway run pip install frappe-framework
```

### ❌ Application crashes: "Address already in use"

**الأعراض:**
```
OSError: [Errno 48] Address already in use
```

**الحل:**
```bash
# في railway.json، استخدم PORT من البيئة
{
  "deploy": {
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT --config gunicorn.conf.py wsgi:application"
  }
}

# أو في gunicorn.conf.py:
port = os.environ.get('PORT', '8000')
bind = [f'0.0.0.0:{port}']
```

### ❌ "Connection refused" لقاعدة البيانات

**الأعراض:**
```
Can't connect to MySQL server on 'db' (111)
```

**الحلول:**

```bash
# 1. تأكد من متغيرات قاعدة البيانات
railway env | grep DATABASE

# 2. انتظر قليلاً لبدء قاعدة البيانات
# في docker-entrypoint.sh، زيادة wait time:
sleep 5

# 3. تحقق من اتصال قاعدة البيانات
railway run mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SELECT 1"

# 4. تحقق من status قاعدة البيانات في Dashboard
```

### ❌ "ECONNREFUSED" للـ Redis

**الأعراض:**
```
Error: connect ECONNREFUSED 127.0.0.1:6379
```

**الحل:**
```bash
# 1. تأكد من متغير REDIS_URL
railway env | grep REDIS

# 2. في docker-entrypoint.sh:
redis-cli -h $REDIS_HOST ping

# 3. إعادة تشغيل Redis service من Dashboard
```

---

## 🗄️ مشاكل قاعدة البيانات

### ❌ "database does not exist"

**الأعراض:**
```
Database 'kanaan_erpnext' doesn't exist
```

**الحلول:**

```bash
# 1. إنشاء قاعدة بيانات
railway run bash
# ثم داخل الـ container:
mysql -h $DB_HOST -u root -p$DB_ROOT_PASSWORD -e "CREATE DATABASE $DB_NAME;"
mysql -h $DB_HOST -u root -p$DB_ROOT_PASSWORD -e "GRANT ALL ON $DB_NAME.* TO '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';"

# 2. أو استخدم Frappe bench:
railway run bench new-site --mariadb-root-password $DB_ROOT_PASSWORD localhost
```

### ❌ "Permission denied" لقاعدة البيانات

**الأعراض:**
```
Access denied for user 'erpnext'@'%' to database
```

**الحل:**
```bash
# من MariaDB service:
GRANT ALL PRIVILEGES ON kanaan_erpnext.* TO 'erpnext'@'%' IDENTIFIED BY 'password';
FLUSH PRIVILEGES;
```

### ❌ "Tables not created"

**الأعراض:**
```
Table 'kanaan_erpnext.tabUser' doesn't exist
```

**الحل:**
```bash
# شغّل database migrations:
railway run bench migrate

# أو للموقع الأول:
railway run bench migrate --site localhost
```

---

## ⚡ مشاكل الـ Performance

### ❌ "Memory usage too high"

**الأعراض:**
```
Application killed due to OOM
```

**الحلول:**

```python
# في gunicorn.conf.py:
workers = 2  # تقليل العدد

# في railway.json:
"NODE_OPTIONS": "--max-old-space-size=1024"  # تقليل الـ Memory
```

### ❌ "CPU usage 100%"

**الأعراض:**
- التطبيق بطيء جداً
- Requests تستغرق وقتاً طويلاً

**الحلول:**

```bash
# 1. تحقق من الـ Logs
railway logs | grep slow

# 2. قلل عدد الـ Workers
workers = max(2, cpu_count() - 1)

# 3. استخدم Production Build
NODE_ENV=production

# 4. تفعيل التخزين المؤقت
REDIS_CACHE=redis://...
```

### ❌ "Disk space full"

**الأعراض:**
```
No space left on device
```

**الحل:**
```bash
# استخدم خدمة External Storage من Railway
# أو قلل حجم السجلات:
LOG_LEVEL=warning  # بدلاً من debug
```

---

## 🌐 مشاكل الـ Networking

### ❌ "Cannot reach application"

**الأعراض:**
```
Connection timeout to railway domain
```

**الحلول:**

```bash
# 1. تحقق من Health Check
curl https://your-app.railway.app/api/health

# 2. تحقق من porta الصحيح
railway logs | grep "listening on"

# 3. تأكد من ALLOW_HOSTS
ALLOW_HOSTS=your-domain.railway.app,localhost

# 4. تحقق من CORS إذا لزم الحال
```

### ❌ "SSL/TLS error"

**الأعراض:**
```
SSL certificate verification failed
```

**الحل:**
```bash
# Railway توفر SSL تلقائياً
# اذهب إلى Railway Dashboard → Settings → Custom Domain
# وتأكد من SSL مفعّل
```

### ❌ "Cross-origin requests blocked"

**الأعراض:**
```
CORS policy: No 'Access-Control-Allow-Origin' header
```

**الحل:**
```python
# في Frappe settings أو wsgi.py:
response.headers['Access-Control-Allow-Origin'] = '*'
response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'
```

---

## 🆘 نصائح للتشخيص

### 1. اعرض السجلات الحية
```bash
railway logs -f
```

### 2. شاهد متغيرات البيئة
```bash
railway env
```

### 3. شغّل أوامر داخل Container
```bash
railway run bash
```

### 4. فحص الـ Network
```bash
railway run ping -c 2 db
railway run redis-cli -h redis ping
```

### 5. استعادة النسخة السابقة
```
في Railway Dashboard:
Deployments → اختر النسخة السابقة → Restore
```

---

## 📞 الحصول على المساعدة

إذا لم تجد الحل:

1. **اقرأ الـ Logs بعناية** - قد تجد الخطأ فيها
2. **جرّب محلياً أولاً** - استخدم `docker-compose.railway.yml`
3. **اتصل بـ Railway Support** - من Dashboard
4. **اسأل في المجتمع** - GitHub Discussions أو Frappe Forum

---

## ✅ قائمة تحقق قبل الإبلاغ عن خطأ

- [ ] تم قراءة السجلات بالكامل
- [ ] تم فحص متغيرات البيئة
- [ ] تم اختبار البناء محلياً
- [ ] تم التأكد من إصدارات المكتبات
- [ ] تم فحص الـ Network Connectivity
- [ ] تم التحقق من أذونات قاعدة البيانات

---

**آخر تحديث:** 2024
**التوفر:** جميع الأوقات ✅