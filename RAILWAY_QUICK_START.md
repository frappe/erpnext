# 🚀 Railway Deployment - Quick Start (5 دقائق)

## الخطوة 1: تحضير المشروع (1 دقيقة)

```bash
# شغّل سكريبت الإعداد
bash railway-setup.sh

# أو على Windows (استخدم WSL أو Git Bash)
bash railway-setup.sh
```

## الخطوة 2: رفع إلى GitHub (2 دقيقة)

```bash
# تأكد من وجود remote
git remote -v

# إذا لم يكن هناك remote، أضفه:
git remote add origin https://github.com/YOUR-USERNAME/kanaanerpgaza-develop.git

# رفع الكود
git add .
git commit -m "Ready for Railway deployment"
git push -u origin main
```

## الخطوة 3: نشر على Railway (2 دقيقة)

### 3.1 الدخول إلى Railway
1. اذهب إلى https://railway.app
2. اضغط **"New Project"**
3. اختر **"Deploy from GitHub"**
4. اختر repository: `kanaanerpgaza-develop`
5. اضغط **"Deploy"**

### 3.2 إضافة المخدومات (Services)
بعد أن يبدأ البناء، أضف:

```
1. Add Service → Database → MariaDB
2. Add Service → Database → Redis
```

## الخطوة 4: تكوين المتغيرات

اذهب إلى **Variables** في Railway وحدّث:

```
SECRET_KEY = [عشوائي 32 حرف]
ENCRYPTION_KEY = [عشوائي 32 حرف]

# أو استخدم:
openssl rand -base64 32
```

## 🎉 تم! 

سيكون تطبيقك متاحاً على:
```
https://kanaan-erp-production-xxxx.railway.app
```

---

## 🔗 الروابط المهمة

- [Railway Dashboard](https://railway.app/dashboard)
- [Documentation الكاملة](./RAILWAY_DEPLOYMENT_GUIDE.md)
- [Railway Docs](https://docs.railway.app)

---

## ⚠️ نصائح مهمة

| المشكلة | الحل |
|--------|------|
| الـ Build يفشل | شاهل الـ Logs في Railway Dashboard |
| تطبيق لا يبدأ | تأكد من DATABASE_URL و REDIS_URL |
| الصور لا تظهر | شغّل `bench build --force` |
| الـ Memory عالي | قلل عدد Workers في gunicorn.conf.py |

---

## 🆘 استكشاف الأخطاء

```bash
# اعرض السجلات الحية
railway logs

# شاهد المتغيرات
railway env

# شاهل الحالة
railway status
```

**حظ موفق! 🎊**