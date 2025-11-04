# 🚀 ERPNext Kanaan ERP - Deployment Guide

دليل النشر الشامل لتطبيق ERPNext Kanaan على أنظمة الاستضافة المختلفة

---

## 📋 جدول المحتويات

1. [المتطلبات الأساسية](#المتطلبات-الأساسية)
2. [النشر المحلي باستخدام Docker](#النشر-المحلي-باستخدام-docker)
3. [النشر على Render.com](#النشر-على-rendercom)
4. [النشر على Railway.app](#النشر-على-railwayapp)
5. [النشر على Heroku](#النشر-على-heroku)
6. [النشر على VPS مع cPanel](#النشر-على-vps-مع-cpanel)
7. [النشر على DigitalOcean App Platform](#النشر-على-digitalocean-app-platform)
8. [استكشاف الأخطاء والمشاكل الشائعة](#استكشاف-الأخطاء-والمشاكل-الشائعة)

---

## 🔧 المتطلبات الأساسية

### جميع الأنظمة
- Git
- Docker و Docker Compose (للنشر المحلي)
- MySQL/MariaDB أو PostgreSQL
- Redis
- Node.js 18+
- Python 3.10+

### التوثيق الأساسية
```
Username: Administrator
Password: admin
Timezone: Asia/Riyadh (أو اختر منطقتك الزمنية)
```

---

## 🐳 النشر المحلي باستخدام Docker

### 1️⃣ التحضير الأولي

```bash
# استنساخ المشروع
git clone <your-repository-url>
cd kanaanerpgaza-develop

# نسخ ملف البيئة
cp .env.example .env

# تعديل البيانات الحساسة (اختياري)
# nano .env
```

### 2️⃣ تشغيل التطبيق

```bash
# بدء جميع الخدمات
docker-compose up -d

# عرض السجلات
docker-compose logs -f

# التحقق من حالة الخدمات
docker-compose ps
```

### 3️⃣ الوصول إلى التطبيق

```
🌐 الرابط: http://localhost:8080
📧 اسم المستخدم: Administrator
🔑 كلمة المرور: admin
```

### 4️⃣ الأوامر المفيدة

```bash
# إيقاف التطبيق
docker-compose down

# حذف جميع البيانات (تحذير: لا يمكن التراجع عن هذا)
docker-compose down -v

# إعادة تشغيل خدمة معينة
docker-compose restart backend

# الوصول إلى Bash داخل الحاوية
docker-compose exec backend bash

# عرض سجلات خدمة معينة
docker-compose logs backend
```

---

## 🌐 النشر على Render.com

Render توفر منصة سهلة الاستخدام لنشر تطبيقات Docker.

### الخطوات:

1. **إنشاء حساب على Render**
   - اذهب إلى [render.com](https://render.com)
   - سجل باستخدام GitHub

2. **ربط المشروع**
   ```bash
   # تأكد من أن لديك ملف render.yaml في المشروع
   git add render.yaml
   git commit -m "Add Render deployment config"
   git push
   ```

3. **النشر عبر Render Dashboard**
   - اذهب إلى Render Dashboard
   - اضغط "New" → "Blueprint"
   - اختر المشروع من GitHub
   - اضغط "Create New Blueprint Instance"

4. **تكوين المتغيرات البيئية**
   - في Render Dashboard، اذهب إلى "Environment"
   - أضف المتغيرات المطلوبة من `.env.example`

5. **المراقبة**
   ```
   - عرض السجلات: Logs في Dashboard
   - معدل الأداء: Metrics في Dashboard
   ```

### التكلفة المقدرة:
- **Free tier**: تطبيق واحد بدون قاعدة بيانات
- **Starter**: $7/شهر للقاعدة + $12/شهر للتطبيق

---

## 🚄 النشر على Railway.app

Railway توفر منصة حديثة وسهلة التوسع.

### الخطوات:

1. **إنشاء حساب على Railway**
   - اذهب إلى [railway.app](https://railway.app)
   - سجل باستخدام GitHub

2. **إنشاء مشروع جديد**
   - اضغط "New Project"
   - اختر "Deploy from GitHub repo"
   - اختر المشروع الخاص بك

3. **إضافة الخدمات**
   ```bash
   # Railway ستكتشف تلقائياً:
   # - Dockerfile
   # - railway.json
   ```

4. **تكوين المتغيرات البيئية**
   - اذهب إلى "Variables" في مشروعك
   - أضف المتغيرات من `.env.example`

5. **النشر التلقائي**
   ```
   - أي push إلى main branch سيؤدي إلى إعادة نشر تلقائية
   ```

### الوصول إلى التطبيق:
```
🌐 الرابط: https://your-project.railway.app
```

### التكلفة المقدرة:
- **$5/شهر**: بدل شهري (شامل لجميع الخدمات)

---

## 📦 النشر على Heroku (Legacy)

ملاحظة: Heroku أوقفت الـ free tier منذ نوفمبر 2022

### المتطلبات:
```bash
# تثبيت Heroku CLI
brew tap heroku/brew && brew install heroku  # على macOS
# أو من: https://devcenter.heroku.com/articles/heroku-cli
```

### الخطوات:

1. **تسجيل الدخول**
```bash
heroku login
```

2. **إنشاء تطبيق جديد**
```bash
heroku create kanaan-erpnext
```

3. **إضافة خدمات البيانات**
```bash
# قاعدة البيانات
heroku addons:create heroku-postgresql:standard-0 -a kanaan-erpnext

# Redis
heroku addons:create heroku-redis:premium-0 -a kanaan-erpnext
```

4. **تعيين المتغيرات البيئية**
```bash
heroku config:set \
  FRAPPE_ENV=production \
  SITE_NAME=kanaan-erpnext.herokuapp.com \
  DEBUG=false \
  -a kanaan-erpnext
```

5. **النشر**
```bash
git push heroku main
```

6. **تشغيل الخدمات**
```bash
# تشغيل العامل والمجدول
heroku ps:scale worker=1 scheduler=1 -a kanaan-erpnext
```

### المراقبة:
```bash
# عرض السجلات
heroku logs --tail -a kanaan-erpnext

# معلومات الأداء
heroku metrics -a kanaan-erpnext
```

---

## 🖥️ النشر على VPS مع cPanel

إذا قمت بترقية حسابك إلى VPS

### المتطلبات:
- SSH Access
- cPanel/WHM
- Python 3.10+
- Node.js 18+
- MySQL/MariaDB

### الخطوات:

1. **الاتصال عبر SSH**
```bash
ssh user@your-vps-ip
```

2. **تثبيت المتطلبات**
```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Python و Node
sudo apt install -y python3.10 python3-pip nodejs npm git

# تثبيت Frappe Bench
sudo pip3 install frappe-bench

# تثبيت MySQL/MariaDB
sudo apt install -y mariadb-server

# تثبيت Redis
sudo apt install -y redis-server
```

3. **استنساخ المشروع**
```bash
cd /home/username/public_html
git clone <your-repository-url> kanaan
cd kanaan
```

4. **تثبيت Dependencies**
```bash
pip install -r requirements.txt
npm ci
```

5. **إنشاء قاعدة البيانات**
```bash
# في MySQL
mysql -u root -p
CREATE DATABASE kanaan_erpnext;
CREATE USER 'erpnext'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON kanaan_erpnext.* TO 'erpnext'@'localhost';
FLUSH PRIVILEGES;
```

6. **تشغيل التطبيق**
```bash
# باستخدام Gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 wsgi:application &

# أو باستخدام Supervisor لتشغيل مستمر
# انسخ supervisor.conf إلى /etc/supervisor/conf.d/
sudo systemctl restart supervisor
```

7. **تكوين Nginx/Apache**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

8. **تفعيل SSL**
```bash
sudo certbot certonly --standalone -d your-domain.com
```

---

## 🌊 النشر على DigitalOcean App Platform

### الخطوات:

1. **إنشاء حساب على DigitalOcean**
   - اذهب إلى [digitalocean.com](https://digitalocean.com)
   - سجل واضف بطاقة ائتمان

2. **ربط GitHub**
   - اذهب إلى App Platform
   - اضغط "Create App"
   - اختر "GitHub" وربط حسابك

3. **تحديد المشروع**
   - اختر المشروع من GitHub
   - اختر branch (main)

4. **تكوين الخدمات**
   - اضغط "Edit" وأضف:
     - Web Service (Dockerfile)
     - PostgreSQL Database
     - Redis Database

5. **تعيين المتغيرات**
   - أضف من `.env.example`

6. **النشر**
   - اضغط "Deploy"

---

## 🔍 استكشاف الأخطاء والمشاكل الشائعة

### المشكلة: فشل الاتصال بقاعدة البيانات

```bash
# تحقق من وجود قاعدة البيانات
mysql -u root -p -e "SHOW DATABASES;"

# تحقق من متغيرات البيئة
echo $DB_HOST
echo $DB_NAME
echo $DB_USER

# اختبر الاتصال
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D $DB_NAME
```

### المشكلة: مشاكل في الأداء

```bash
# قلل عدد الـ workers
gunicorn --workers 2 --threads 4 wsgi:application

# تحقق من استخدام الذاكرة
docker stats

# قلل حجم الصور
npm run build:production
```

### المشكلة: SSL Certificate Errors

```bash
# للـ Render/Railway: يتم التعامل معه تلقائياً

# للـ VPS: استخدم Let's Encrypt
sudo certbot certonly --standalone -d your-domain.com
```

### المشكلة: Black Screen/White Screen

```bash
# تفعيل Debug Mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# عرض السجلات
docker-compose logs -f backend
```

---

## 📊 مقارنة الأنظمة

| المنصة | الإعداد | التكلفة | الأداء | الدعم |
|--------|--------|--------|--------|--------|
| **Render** | سهل جداً | $7+/شهر | جيد جداً | ممتاز |
| **Railway** | سهل جداً | $5+/شهر | ممتاز | جيد |
| **Heroku** | سهل | $25+/شهر | متوسط | جيد |
| **DigitalOcean** | متوسط | $12+/شهر | ممتاز | ممتاز |
| **VPS + cPanel** | صعب | $10+/شهر | متغير | تقني |

---

## ✅ Checklist ما قبل النشر

- [ ] جميع المتغيرات البيئية معرّفة
- [ ] قاعدة البيانات تعمل
- [ ] Redis يعمل
- [ ] الملفات الثابتة مُبنية (npm run build)
- [ ] تم اختبار الاتصالات
- [ ] SSL/HTTPS مُفعّل
- [ ] النسخ الاحتياطية مُعدّة
- [ ] المراقبة/السجلات مُفعّلة

---

## 🆘 الدعم والمساعدة

للمزيد من المساعدة:

- 📖 [Frappe Documentation](https://frappeframework.com)
- 📖 [ERPNext Documentation](https://docs.erpnext.com)
- 🐛 [GitHub Issues](https://github.com/frappe/erpnext/issues)
- 💬 [Community Forum](https://discuss.frappe.io)

---

**تم آخر تحديث:** 2024
**الإصدار:** ERPNext v15.85.1
**الإطار:** Frappe v15