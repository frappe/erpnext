# 🚀 دليل نشر Kanaan ERP على Railway.com

## مقدمة
هذا الدليل يشرح كيفية نشر تطبيق **Kanaan ERP** على منصة **Railway.com** بخطوات بسيطة وسهلة.

---

## 📋 المتطلبات الأساسية

1. **حساب GitHub** - للربط مع Repository
2. **حساب Railway.com** - https://railway.app (مجاني مع بعض الحدود)
3. **Git** - مثبت على جهازك
4. **بيانات المشروع** - Repository على GitHub

---

## 🔐 الخطوة 1: إعداد GitHub Repository

### 1.1 Push المشروع إلى GitHub
```bash
# إذا لم تكن قد أضفت Remote بعد
git remote add origin https://github.com/YOUR-USERNAME/kanaanerpgaza-develop.git
git branch -M main
git push -u origin main
```

### 1.2 التأكد من وجود الملفات المطلوبة
تأكد من أن المجلد الجذر يحتوي على:
- ✅ `Dockerfile` - تعريف صورة Docker
- ✅ `railway.json` - تكوين Railway
- ✅ `.env.example` - متغيرات البيئة
- ✅ `docker-entrypoint.sh` - سكريبت البدء
- ✅ `requirements.txt` - المكتبات الـ Python
- ✅ `package.json` - المكتبات الـ Node.js

---

## 🎯 الخطوة 2: إنشاء مشروع على Railway

### 2.1 الدخول إلى Railway
1. اذهب إلى https://railway.app
2. سجّل الدخول أو أنشئ حسابًا
3. اضغط على **"New Project"**

### 2.2 ربط Repository
```
1. اختر: "Deploy from GitHub"
2. اختر Repository: kanaanerpgaza-develop
3. اختر Branch: main
4. اضغط "Deploy"
```

---

## ⚙️ الخطوة 3: إضافة قاعدة البيانات والخدمات

### 3.1 إضافة قاعدة بيانات MariaDB
```
1. في لوحة Railway، اضغط "Add"
2. اختر "Database"
3. اختر "MariaDB"
4. اضغط "Deploy"
```

### 3.2 إضافة Redis (اختياري لكن مهم)
```
1. في لوحة Railway، اضغط "Add"
2. اختر "Database"
3. اختر "Redis"
4. اضغط "Deploy"
```

---

## 🔧 الخطوة 4: تكوين متغيرات البيئة

### 4.1 في لوحة Railway:
اذهب إلى **Variables** وأضف التالي:

#### ✅ متغيرات قاعدة البيانات
```
# Railway يوفرها تلقائياً عند ربط قاعدة بيانات
DATABASE_URL=mysql://user:password@host:port/database
REDIS_URL=redis://:password@host:port
```

#### ✅ متغيرات Frappe/ERPNext
```
FRAPPE_ENV=production
SITE_NAME=localhost
SECRET_KEY=your-secret-key-here-change-this
ENCRYPTION_KEY=your-encryption-key-here-change-this
DEBUG=false

# القيم الافتراضية (سيتم تغييرها تلقائياً)
DB_HOST=railway-db-host
DB_PORT=3306
DB_NAME=kanaan_erpnext
DB_USER=erpnext
DB_PASSWORD=secure_password_here

REDIS_CACHE=redis://host:6379
REDIS_QUEUE=redis://host:6379
```

### 4.2 تعيين المتغيرات
Railway توفر المتغيرات تلقائياً:
- `DATABASE_URL` ← من MariaDB
- `REDIS_URL` ← من Redis (اختياري)

#### الطريقة الصحيحة لـ Railway:

```bash
# 1. Railway توفر DATABASE_URL كـ:
# mysql://user:pass@host:port/dbname

# 2. سننقل هذه إلى متغيرات Frappe كـ:
DB_HOST=${DATABASE_URL_HOSTNAME}
DB_USER=${DATABASE_URL_USERNAME}
DB_PASSWORD=${DATABASE_URL_PASSWORD}
DB_NAME=${DATABASE_URL_DATABASE}
```

**لكن Railway توفر معاينة أفضل، استخدم UI الخاص بها!**

---

## 🚀 الخطوة 5: تشغيل التطبيق

### 5.1 الأوامر المطلوبة

في Railway، ستحتاج إلى:

#### أ) تهيئة قاعدة البيانات (تُشغّل مرة واحدة):
```bash
bench setup requirements
bench setup build
```

#### ب) أوامر البدء الأساسية:
في `railway.json`:
```json
{
  "deploy": {
    "startCommand": "gunicorn --config gunicorn.conf.py wsgi:application"
  }
}
```

### 5.2 متابعة السجلات
```
في Railway Dashboard:
1. اختر Service الخاص بك
2. اضغط "Logs"
3. شاهد السجلات الحية
```

---

## 🔒 الخطوة 6: تكوين النطاق (Domain)

### 6.1 النطاق المؤقت من Railway
عند النشر، ستحصل على رابط مثل:
```
https://kanaanerpgaza-develop-production.up.railway.app
```

### 6.2 ربط نطاق مخصص (اختياري)
```
1. في Railway → Settings → Custom Domain
2. أدخل نطاقك: example.com
3. حدّث DNS records:
   CNAME → your-railway-domain.railway.app
```

---

## 📊 الخطوة 7: المراقبة والصيانة

### 7.1 التحقق من صحة التطبيق
```bash
curl https://your-railway-domain.railway.app/api/health
```

### 7.2 المراقبة
Railway توفر:
- ✅ Logs - السجلات
- ✅ Metrics - المقاييس (CPU, Memory)
- ✅ Deployments - السجل
- ✅ Environment - المتغيرات

### 7.3 إعادة النشر
```bash
git push origin main
# Railway تعيد النشر تلقائياً!
```

---

## ⚠️ المشاكل الشائعة والحلول

### ❌ المشكلة: قاعدة البيانات لم تنشأ
**الحل:**
```bash
# قم بتشغيل أوامر التهيئة يدويًا:
railway run bench new-site \
  --mariadb-root-password password \
  --admin-password admin \
  --no-mariadb-socket \
  localhost
```

### ❌ المشكلة: Redis غير متصل
**الحل:**
```bash
# تأكد من متغيرات REDIS:
REDIS_CACHE=redis://... 
REDIS_QUEUE=redis://...
```

### ❌ المشكلة: الصور لا تظهر
**الحل:**
```bash
# تأكد من تثبيت ملفات Static:
bench build --force
```

### ❌ المشكلة: Memory العالي
**الحل:**
في `gunicorn.conf.py`:
```python
workers = 2  # قلل العدد للـ Plans الأصغر
```

---

## 📱 إعدادات التوسع (Scaling)

### التخطيط المناسب
```
Free Tier:
- ✅ 5$ رصيد شهري مجاني
- ✅ PostgreSQL أو MySQL صغير
- ❌ حدود في الذاكرة والـ CPU

Pro Plan:
- ✅ دفع حسب الاستخدام ($5+/شهر)
- ✅ خوادم أقوى
- ✅ 100GB بيانات شهرياً
```

---

## 📚 ملفات مهمة

| الملف | الوصف |
|------|-------|
| `railway.json` | إعدادات Railway (Build, Deploy, Health Checks) |
| `Dockerfile` | بناء صورة التطبيق |
| `.env.example` | قالب متغيرات البيئة |
| `docker-entrypoint.sh` | سكريبت تهيئة البدء |
| `gunicorn.conf.py` | إعدادات Gunicorn |
| `requirements.txt` | المكتبات الـ Python |
| `package.json` | المكتبات الـ Node.js |

---

## 🔗 الروابط المهمة

- 📖 [Railway Documentation](https://docs.railway.app)
- 🐳 [Docker Documentation](https://docs.docker.com)
- 🍵 [Frappe Framework](https://frappe.io)
- 📦 [ERPNext](https://erpnext.com)
- 🔧 [ERPNext Docker Debian (مثال)](https://github.com/pipech/erpnext-docker-debian)

---

## ✅ قائمة التحقق النهائية

- [ ] تم دفع الكود إلى GitHub
- [ ] تم إنشاء حساب Railway
- [ ] تم ربط Repository
- [ ] تم إضافة MariaDB
- [ ] تم إضافة Redis
- [ ] تم تعيين متغيرات البيئة
- [ ] تم تشغيل Deployment
- [ ] تم التحقق من الـ Logs
- [ ] تم الوصول للتطبيق عبر الرابط

---

## 🆘 الدعم والمساعدة

إذا واجهت مشاكل:

1. **تحقق من Logs في Railway Dashboard**
2. **اقرأ Railway Documentation**
3. **شاهد ERPNext Docker Examples**
4. **تواصل مع فريق الدعم**

---

**آخر تحديث:** 2024
**الحالة:** جاهز للإنتاج ✅