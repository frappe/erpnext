# 🐳 Docker Quick Start - ERPNext Kanaan ERP

دليل سريع لتشغيل التطبيق محلياً باستخدام Docker

---

## 📋 المتطلبات

```bash
# تحقق من وجود Docker
docker --version

# تحقق من وجود Docker Compose
docker-compose --version
```

إذا لم تكن مثبتاً:
- [تثبيت Docker Desktop](https://www.docker.com/products/docker-desktop)

---

## ⚡ البدء السريع (3 خطوات فقط)

### 1️⃣ نسخ ملف البيئة

```bash
cp .env.example .env
```

### 2️⃣ تشغيل التطبيق

```bash
docker-compose up -d
```

### 3️⃣ الوصول إلى التطبيق

```
🌐 المتصفح: http://localhost:8080
📧 اسم المستخدم: Administrator
🔑 كلمة المرور: admin
```

---

## 🎯 الأوامر الأساسية

### عرض حالة الخدمات

```bash
# عرض جميع الحاويات
docker-compose ps

# يجب أن ترى:
# ✅ kanaan-db (database)
# ✅ kanaan-redis-cache
# ✅ kanaan-redis-queue
# ✅ kanaan-backend
# ✅ kanaan-nginx
# ✅ kanaan-queue-worker
# ✅ kanaan-scheduler
```

### عرض السجلات

```bash
# جميع السجلات
docker-compose logs -f

# سجلات خدمة معينة فقط
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f db

# آخر 100 سطر
docker-compose logs --tail=100
```

### الدخول إلى الحاوية

```bash
# دخول إلى backend bash
docker-compose exec backend bash

# تشغيل أمر مباشرة
docker-compose exec backend python manage.py

# الخروج
exit
```

### إعادة التشغيل

```bash
# إعادة خدمة واحدة
docker-compose restart backend

# إعادة جميع الخدمات
docker-compose restart

# إيقاف كل شيء
docker-compose stop

# حذف وبدء من جديد
docker-compose down
docker-compose up -d
```

---

## 🔧 تشخيص المشاكل الشائعة

### المشكلة: الخدمات لم تبدأ

```bash
# عرض الأخطاء
docker-compose logs

# حاول:
docker-compose down -v
docker-compose up -d --build
```

### المشكلة: الموارد غير كافية

```bash
# تقليل الـ workers في docker-compose.yml
# غير: workers: multiprocessing.cpu_count() * 2 + 1
# إلى: workers: 2
```

### المشكلة: Port مشغول

```bash
# غير الـ port في .env أو docker-compose.yml
NGINX_PORT=8888  # بدل 8080

# ثم أعد التشغيل
docker-compose restart nginx
```

### المشكلة: قاعدة البيانات لا تستجيب

```bash
# إعادة تشغيل قاعدة البيانات
docker-compose restart db

# انتظر 10 ثوان وتحقق
docker-compose ps

# يجب أن تكون healthy
```

---

## 💾 النسخ الاحتياطية والاستعادة

### عمل نسخة احتياطية

```bash
# تصدير قاعدة البيانات
docker-compose exec db mysqldump -uerpnext -p kanaan_erpnext > backup.sql

# حفظ الملفات
docker cp kanaan-backend:/app/private/files ./backup/
docker cp kanaan-backend:/app/sites ./backup/
```

### استعادة من نسخة احتياطية

```bash
# استيراد قاعدة البيانات
docker-compose exec -T db mysql -uerpnext -p kanaan_erpnext < backup.sql

# استعادة الملفات
docker cp backup/files/. kanaan-backend:/app/private/files/
docker cp backup/sites/. kanaan-backend:/app/sites/
```

---

## 📊 المراقبة والأداء

### عرض استخدام الموارد

```bash
# CPU و Memory و Network
docker stats

# مثال:
# CONTAINER                CPU %   MEM USAGE / LIMIT
# kanaan-backend          2.5%    450MiB / 8GiB
# kanaan-db               1.2%    200MiB / 8GiB
```

### عرض حجم الصور والحاويات

```bash
# حجم الصور
docker images

# حجم الحاويات
docker ps -s
```

### تنظيف الموارد غير المستخدمة

```bash
# حذف الحاويات المتوقفة
docker container prune

# حذف الصور غير المستخدمة
docker image prune

# حذف كل شيء (تحذير!)
docker system prune -a
```

---

## 🔐 الأمان

### تغيير كلمات المرور الافتراضية

```bash
# في .env
DB_PASSWORD=your-strong-password
DB_ROOT_PASSWORD=your-root-password
ENCRYPTION_KEY=your-encryption-key
```

### تعطيل Debug Mode

```bash
# في .env
DEBUG=false
LOG_LEVEL=INFO  # بدل DEBUG
```

### فعّل HTTPS (اختياري)

```bash
# توليد شهادة SSL ذاتية التوقيع
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# أضف إلى docker-compose.yml
# volumes:
#   - ./cert.pem:/etc/nginx/cert.pem
#   - ./key.pem:/etc/nginx/key.pem
```

---

## 🚀 نصائح الأداء

### 1. استخدم جزء Docker - لا تستخدم volumes للملفات الثابتة

```yaml
# ❌ بطيء على Windows/Mac
volumes:
  - ./erpnext:/app

# ✅ أسرع
volumes:
  - app_data:/app  # named volume
```

### 2. زيادة عدد Redis connections

```env
# في .env
REDIS_CACHE=redis-cache:6379
```

### 3. استخدم production build

```bash
# بدل development
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📱 الوصول من أجهزة أخرى

### من نفس الشبكة

```
http://your-machine-ip:8080
```

```bash
# اكتشف IP الخاص بك
# Windows
ipconfig

# Mac/Linux
ifconfig
```

### عبر الإنترنت (غير آمن - للتطوير فقط)

```bash
# استخدم ngrok
ngrok http 8080
```

---

## 🔄 التحديثات والصيانة

### تحديث الصور

```bash
# سحب أحدث الصور
docker-compose pull

# إعادة البناء
docker-compose up -d --build
```

### تنظيف السجلات

```bash
# حذف السجلات القديمة
docker logs --tail 0 -f kanaan-backend > /dev/null
```

---

## 📚 الموارد الإضافية

- [Docker Documentation](https://docs.docker.com)
- [Docker Compose Documentation](https://docs.docker.com/compose)
- [Frappe Documentation](https://frappeframework.com)
- [ERPNext Documentation](https://docs.erpnext.com)

---

## ❓ أسئلة متكررة

**س: هل يمكنني استخدام هذا في الإنتاج؟**
ج: نعم، لكن يفضل استخدام منصات مخصصة مثل Render أو Railway

**س: كيف أنسخ احتياطي من قاعدة البيانات؟**
ج: استخدم الأمر المذكور أعلاه في قسم "النسخ الاحتياطية"

**س: كيف أزيد حد المدة الزمنية للطلبات؟**
ج: غير `proxy_read_timeout` في nginx.conf

**س: كيف أستخدم HTTPS محلياً؟**
ج: اتبع الخطوات في قسم "الأمان"

---

**تم آخر تحديث:** 2024
**الإصدار:** Docker Compose v2.0+