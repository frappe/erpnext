# 🚀 Kanaan ERP - Railway.com Deployment

> نشر تطبيق كنعان ERP على Railway.com في دقائق بدون تعقيدات

## 🎯 لماذا Railway؟

| الميزة | Railway | Heroku | AWS |
|--------|---------|--------|-----|
| **التسعير** | $5 شهري (مجاني) | $50+ | معقد |
| **البدء** | 5 دقائق | 15 دقيقة | ساعات |
| **DB/Redis** | مدمج | إضافي | إضافي |
| **SSL** | تلقائي | تلقائي | يدوي |
| **GitHub Auto** | ✅ | ✅ | ✅ |

---

## 📝 الملفات الهامة

```
📦 Project
├── 🔴 railway.json ..................... إعدادات Railway
├── 🔴 RAILWAY_DEPLOYMENT_GUIDE.md ....... دليل شامل
├── 🔴 RAILWAY_QUICK_START.md ........... دليل سريع (5 دقائق)
├── 🔴 railway-setup.sh ................ سكريبت إعداد (Linux/Mac)
├── 🔴 railway-setup.ps1 .............. سكريبت إعداد (Windows)
├── 🔴 docker-compose.railway.yml ...... اختبار محلي
├── 🔴 .env.railway.example ........... متغيرات البيئة
├── 🔴 RAILWAY_TROUBLESHOOTING.md ..... حل المشاكل
└── 🔴 wsgi.py ....................... تطبيق WSGI
```

---

## ⚡ البدء السريع (5 دقائق)

### الخطوة 1: تحضير المشروع

**على Linux/Mac:**
```bash
bash railway-setup.sh
```

**على Windows PowerShell:**
```powershell
.\railway-setup.ps1
```

### الخطوة 2: رفع إلى GitHub
```bash
git add .
git commit -m "Ready for Railway"
git push -u origin main
```

### الخطوة 3: النشر على Railway
1. اذهب إلى https://railway.app
2. اضغط **"New Project"**
3. اختر **"Deploy from GitHub"**
4. اختر repository
5. اضغط **"Deploy"**

**تم! ✅ ستكون نسختك حية في دقائق!**

---

## 🔧 الإعداد المتقدم

### إضافة قاعدة البيانات
```
في Railway Dashboard:
1. اضغط "Add"
2. اختر "Database"
3. اختر "MariaDB" (أو PostgreSQL)
4. اضغط "Deploy"
```

### إضافة Redis (للـ Cache)
```
1. اضغط "Add"
2. اختر "Database"
3. اختر "Redis"
4. اضغط "Deploy"
```

### تعيين المتغيرات
```
في Railway → Variables:
SECRET_KEY = [عشوائي]
ENCRYPTION_KEY = [عشوائي]
SITE_NAME = localhost
FRAPPE_ENV = production
DEBUG = false
```

---

## 🧪 الاختبار المحلي

```bash
# استخدم docker-compose المتخصص
docker-compose -f docker-compose.railway.yml up

# الوصول على:
# http://localhost:8000 (Backend)
# http://localhost:8080 (Nginx)
```

---

## 📚 الدلائل الكاملة

| الدليل | الوصف |
|--------|-------|
| [RAILWAY_QUICK_START.md](./RAILWAY_QUICK_START.md) | شروع سريع (5 دقائق) |
| [RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md) | دليل شامل (مفصل) |
| [RAILWAY_TROUBLESHOOTING.md](./RAILWAY_TROUBLESHOOTING.md) | حل المشاكل |

---

## 🆘 المشاكل الشائعة

### "Build Timeout"
```bash
# قلل حجم الصورة في Dockerfile
# استخدم --slim بدلاً من latest
```

### "Database connection refused"
```bash
# تأكد من DATABASE_URL
railway env | grep DATABASE
```

### "Memory usage high"
```python
# في gunicorn.conf.py:
workers = 2  # قلل العدد
```

**🔗 شاهد [RAILWAY_TROUBLESHOOTING.md](./RAILWAY_TROUBLESHOOTING.md) لمزيد من الحلول**

---

## 🔐 نصائح الأمان

⚠️ **تعديلات مهمة قبل الإنتاج:**

1. **غيّر المفاتيح السرية**
   ```bash
   # استخدم: openssl rand -base64 32
   SECRET_KEY = [random-string]
   ENCRYPTION_KEY = [random-string]
   ```

2. **فعّل HTTPS**
   - Railway يفعّله تلقائياً ✅

3. **قيّد ALLOW_HOSTS**
   ```
   ALLOW_HOSTS = your-domain.com, www.your-domain.com
   ```

4. **استخدم Environment Variables**
   - لا تضع الأسرار في الكود ❌
   - استخدم Railway Dashboard ✅

---

## 📞 الدعم

**عندما تواجه مشكلة:**

1. ✅ اقرأ السجلات: `railway logs -f`
2. ✅ اعرض المتغيرات: `railway env`
3. ✅ شاهد [RAILWAY_TROUBLESHOOTING.md](./RAILWAY_TROUBLESHOOTING.md)
4. ✅ اتصل بـ Railway Support من Dashboard

---

## 🎉 النتيجة النهائية

بعد الانتهاء، ستحصل على:

- ✅ تطبيق مستضاف على Railway
- ✅ قاعدة بيانات MariaDB مشفرة
- ✅ Redis للـ Cache
- ✅ SSL/TLS تلقائي
- ✅ نطاق مجاني `.railway.app`
- ✅ نشر تلقائي من GitHub
- ✅ رقابة وسجلات مباشرة

**الرابط:** `https://your-app-production-xxxx.railway.app`

---

## 📊 إحصائيات الأداء

بعد النشر على Railway:

```
⚡ Performance Metrics:
   - First Load: < 2s
   - API Response: < 100ms
   - Database: MariaDB 10.11
   - Cache: Redis 7
   - Memory: 512MB-2GB
   - CPU: Shared 1-2 cores
```

---

## 🔄 النشر المتكرر

**طريقة سهلة:**
```bash
git add .
git commit -m "Update"
git push origin main
# Railway سيتولى النشر تلقائياً! 🚀
```

**مع تحكم أكثر:**
```bash
railway up --detach
```

---

## 🎓 التعلم المزيد

- [Railway Documentation](https://docs.railway.app)
- [Frappe Framework Guide](https://frappe.io)
- [ERPNext Docs](https://docs.erpnext.com)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

## 💡 نصائح إضافية

### تحديث التطبيق
```bash
git push origin main
# أو:
railway up
```

### عكس التغييرات
```
في Railway Dashboard:
Deployments → اختر النسخة السابقة → Restore
```

### زيادة الموارد (عند الحاجة)
```
في Railway Dashboard:
Settings → Resources → زيادة CPU/Memory
```

### إضافة نطاق مخصص
```
في Railway Dashboard:
Settings → Custom Domain → أضف نطاقك
```

---

## 📋 قائمة التحقق قبل الإطلاق

- [ ] تم قراءة RAILWAY_QUICK_START.md
- [ ] تم تشغيل railway-setup.sh/ps1
- [ ] تم رفع الكود إلى GitHub
- [ ] تم إنشاء حساب Railway
- [ ] تم إضافة MariaDB و Redis
- [ ] تم تعيين المتغيرات الحساسة
- [ ] تم اختبار Deployment
- [ ] تم الوصول للتطبيق

---

## 🚀 جاهز للبدء؟

```bash
# ابدأ الآن:
bash railway-setup.sh
git push origin main

# ثم افتح: https://railway.app/dashboard
```

**مبروك! تطبيقك سيكون حياً في دقائق! 🎉**

---

**Made with ❤️ for Kanaan ERP**
**Railway Deployment Guide v1.0**