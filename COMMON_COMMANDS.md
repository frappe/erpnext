# 📚 الأوامر الشائعة والمهمة - Kanaan ERP

قائمة بأهم الأوامر المستخدمة أثناء التثبيت والتشغيل والصيانة

---

## 🔗 الاتصال بالسيرفر

### من Windows PowerShell
```powershell
# الاتصال الأساسي
sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5

# الاتصال مع الاحتفاظ بالاتصال مفتوح
ssh -o ServerAliveInterval=60 esplzswx@45.159.160.5

# نسخ ملف من المحلي للسيرفر
scp C:\local\file.txt esplzswx@45.159.160.5:/home/esplzswx/

# نسخ ملف من السيرفر للمحلي
scp esplzswx@45.159.160.5:/home/esplzswx/file.txt C:\local\
```

### من Linux/Mac
```bash
# الاتصال البسيط
ssh esplzswx@45.159.160.5

# مع حفظ كلمة المرور في Keychain
ssh-add ~/.ssh/id_rsa
ssh esplzswx@45.159.160.5
```

---

## 📦 تثبيت المتطلبات

### تحديث النظام
```bash
sudo apt update                    # تحديث قائمة الحزم
sudo apt upgrade -y                # ترقية جميع الحزم
sudo apt autoremove -y             # حذف الحزم غير المستخدمة
sudo apt autoclean                 # تنظيف الكاش
```

### تثبيت الأدوات الأساسية
```bash
sudo apt install -y build-essential curl wget git
sudo apt install -y python3.10 python3-pip python3-dev
sudo apt install -y nodejs npm
sudo apt install -y mariadb-server mariadb-client
sudo apt install -y redis-server redis-tools
sudo apt install -y docker.io docker-compose nginx
```

### إضافة المستخدم لمجموعة Docker (بدون sudo)
```bash
sudo usermod -aG docker $USER
sudo usermod -aG docker esplzswx
newgrp docker                      # تفعيل المجموعة الجديدة
```

---

## 🚀 إدارة التطبيق مع Docker

### بدء وإيقاف الخدمات
```bash
cd /home/esplzswx/kanaanerpgaza-develop

# بدء جميع الخدمات
docker-compose up -d                   # بدء في الخلفية
docker-compose up                      # بدء مع عرض السجلات

# إيقاف الخدمات
docker-compose down                    # إيقاف بدون حذف البيانات
docker-compose down -v                 # إيقاف وحذف البيانات (تحذير!)

# إعادة تشغيل
docker-compose restart                 # إعادة تشغيل جميع الخدمات
docker-compose restart backend         # إعادة تشغيل خدمة محددة
```

### مراقبة الخدمات
```bash
# حالة الخدمات
docker-compose ps                      # قائمة بحالة الخدمات
docker-compose ps --services           # أسماء الخدمات فقط

# السجلات
docker-compose logs                    # جميع السجلات
docker-compose logs -f                 # السجلات الحية (متابعة مستمرة)
docker-compose logs backend            # سجلات خدمة محددة
docker-compose logs -f --tail=100      # آخر 100 سطر مع المتابعة
docker-compose logs backend -f --tail=50

# الموارد
docker stats                           # استخدام CPU والذاكرة
docker stats --no-stream               # لقطة واحدة
```

### الدخول إلى الحاويات
```bash
# الدخول إلى bash
docker-compose exec backend bash       # الدخول لـ backend
docker-compose exec database bash      # الدخول لـ database

# تشغيل أمر مباشر
docker-compose exec backend ls -la     # تشغيل أمر واحد
docker-compose exec database mysql -u erpnext -p kanaan_erpnext
```

### إدارة الصور والحاويات
```bash
# قائمة الصور
docker images                          # جميع الصور
docker images kanaan*                  # صور معينة

# حذف الصور والحاويات
docker system prune                    # تنظيف الموارد غير المستخدمة
docker system prune -a                 # حذف شامل
docker image rm image-name             # حذف صورة
docker container rm container-id       # حذف حاوية
```

---

## 🗄️ إدارة قاعدة البيانات

### الاتصال والعمليات الأساسية
```bash
# الاتصال بـ MySQL مباشرة
mysql -u erpnext -p kanaan_erpnext    # من السيرفر
mysql -h 127.0.0.1 -u erpnext -p kanaan_erpnext  # مع IP

# الاتصال عبر Docker
docker-compose exec database mysql -u erpnext -p kanaan_erpnext
```

### أوامر SQL مهمة
```sql
-- عرض جميع قواعد البيانات
SHOW DATABASES;

-- عرض الجداول
USE kanaan_erpnext;
SHOW TABLES;

-- عرض حجم قاعدة البيانات
SELECT table_schema "Database",
ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) "Size in MB"
FROM information_schema.TABLES
GROUP BY table_schema;

-- عرض المستخدمين
SELECT user, host FROM mysql.user;

-- إعادة تعيين كلمة المرور
ALTER USER 'erpnext'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;

-- النسخ الاحتياطي السريع
FLUSH TABLES WITH READ LOCK;
EXIT;
```

### النسخ الاحتياطي والاستعادة
```bash
# نسخ احتياطي كاملة
mysqldump -u erpnext -p kanaan_erpnext > backup_$(date +%Y%m%d_%H%M%S).sql

# نسخ احتياطي عبر Docker
docker-compose exec database mysqldump -u erpnext -p kanaan_erpnext > backup.sql

# استعادة من النسخة الاحتياطية
mysql -u erpnext -p kanaan_erpnext < backup.sql

# نسخ احتياطي مضغوطة
mysqldump -u erpnext -p kanaan_erpnext | gzip > backup.sql.gz

# استعادة من مضغوطة
gunzip < backup.sql.gz | mysql -u erpnext -p kanaan_erpnext
```

---

## 🔴 إدارة Redis

### الأوامر الأساسية
```bash
# اختبر الاتصال
redis-cli ping                         # يجب أن يرجع PONG

# عرض المفاتيح
redis-cli KEYS "*"                     # جميع المفاتيح
redis-cli KEYS "session:*"             # مفاتيح معينة

# إدارة البيانات
redis-cli GET key_name                 # قراءة مفتاح
redis-cli SET key_name value           # كتابة مفتاح
redis-cli DEL key_name                 # حذف مفتاح
redis-cli FLUSHALL                     # حذف جميع البيانات

# الإحصائيات
redis-cli INFO                         # معلومات عامة
redis-cli INFO memory                  # معلومات الذاكرة
redis-cli DBSIZE                       # عدد المفاتيح

# المراقبة
redis-cli MONITOR                      # مراقبة الأوامر الحية
```

### نسخ احتياطي من Redis
```bash
# نسخ احتياطي يدوية
redis-cli BGSAVE                       # نسخ احتياطية في الخلفية

# موقع النسخة الاحتياطية
ls -la /var/lib/redis/dump.rdb

# نسخ الملف
cp /var/lib/redis/dump.rdb /backup/redis_backup.rdb
```

---

## 📁 إدارة الملفات والمجلدات

### التنقل والقائمة
```bash
cd /home/esplzswx/kanaanerpgaza-develop   # الانتقال
pwd                                       # مسار المجلد الحالي
ls -la                                    # قائمة الملفات
ls -lh                                    # مع أحجام مقروءة
du -sh *                                  # حجم المجلدات
```

### نسخ والملفات
```bash
# نسخ
cp -r source_dir dest_dir                # نسخ مجلد كامل
cp file.txt file_backup.txt              # نسخ ملف

# نقل/إعادة تسمية
mv old_name.txt new_name.txt             # إعادة تسمية
mv file.txt /new/path/                   # نقل

# حذف
rm file.txt                              # حذف ملف
rm -r directory/                         # حذف مجلد
```

### الصلاحيات والملكية
```bash
# تغيير الصلاحيات
chmod 755 file.txt                       # قراءة وتنفيذ للجميع
chmod 644 file.txt                       # قراءة فقط
chmod +x script.sh                       # جعل الملف قابل للتنفيذ

# تغيير الملكية
chown esplzswx:esplzswx file.txt         # تغيير المالك
chown -R esplzswx:esplzswx directory/    # لمجلد كامل
```

---

## 🔍 البحث والعثور

```bash
# البحث عن ملفات
find . -name "*.py"                      # ملفات Python
find . -type f -name "*.log"             # ملفات السجلات
find . -mtime -7                         # ملفات عدّلت آخر 7 أيام

# البحث عن محتوى
grep -r "text" .                         # البحث في جميع الملفات
grep -n "function" file.py               # مع أرقام الأسطر
grep -i "case" .                         # عدم تمييز الحالة

# العد
grep -c "error" log.txt                  # عد مرات الظهور
```

---

## 📊 المراقبة والأداء

### استخدام الموارد
```bash
# المراقبة الحية
top                                      # عرض العمليات
htop                                     # واجهة أفضل (إذا كانت مثبتة)
free -h                                  # الذاكرة
df -h                                    # مساحة القرص
iostat                                   # I/O الإحصائيات

# معلومات النظام
uname -a                                 # معلومات النظام
lsb_release -a                           # إصدار Ubuntu
uptime                                   # وقت التشغيل
```

### تحليل السجلات
```bash
# عرض آخر أسطر
tail -f /var/log/syslog                  # متابعة مستمرة
tail -50 /var/log/error.log              # آخر 50 سطر

# البحث عن الأخطاء
grep ERROR /var/log/*.log
grep -i failed /var/log/auth.log

# إحصائيات السجلات
wc -l /var/log/syslog                    # عدد الأسطر
```

---

## 🔧 صيانة دورية

### تنظيف والتحديث
```bash
# تنظيف الملفات المؤقتة
rm -rf /tmp/*                            # ملفات مؤقتة
docker system prune                      # تنظيف Docker

# حذف السجلات القديمة
find /var/log -name "*.gz" -delete       # السجلات المضغوطة

# ترقية الحزم
sudo apt update && sudo apt upgrade -y

# إعادة تشغيل النظام (إن لزم)
sudo reboot
```

### النسخ الاحتياطية المنتظمة
```bash
# نسخة احتياطية يومية من المشروع
tar -czf kanaan-backup-$(date +%Y%m%d).tar.gz /home/esplzswx/kanaanerpgaza-develop/

# نسخة احتياطية من قاعدة البيانات
mysqldump -u erpnext -p kanaan_erpnext | gzip > db-backup-$(date +%Y%m%d).sql.gz

# نقل النسخة للتخزين
scp kanaan-backup-*.tar.gz esplzswx@45.159.160.5:/backup/
```

---

## 🛡️ الأمان

### إدارة المستخدمين
```bash
# إضافة مستخدم جديد
sudo useradd -m -s /bin/bash newuser     # مستخدم عادي
sudo useradd -m -s /bin/bash -G sudo newuser  # مع صلاحيات sudo

# تغيير كلمة المرور
sudo passwd esplzswx

# إزالة مستخدم
sudo userdel newuser
sudo userdel -r newuser                  # مع حذف المجلد الرئيسي
```

### جدار الحماية
```bash
# تفعيل وإدارة UFW
sudo ufw enable                          # تفعيل
sudo ufw disable                         # تعطيل
sudo ufw status                          # الحالة

# السماح بالمنافذ
sudo ufw allow 22/tcp                    # SSH
sudo ufw allow 80/tcp                    # HTTP
sudo ufw allow 443/tcp                   # HTTPS
sudo ufw allow 3306/tcp                  # MySQL

# رفض المنافذ
sudo ufw deny 22/tcp                     # رفض SSH
```

---

## 🐛 استكشاف الأخطاء

### أوامر التشخيص
```bash
# اختبر الاتصال بالانترنت
ping 8.8.8.8                             # Google DNS
curl https://www.google.com              # HTTP connection

# اختبر المنافذ
netstat -tulpn | grep LISTEN             # المنافذ المفتوحة
lsof -i :8080                            # من يستخدم المنفذ 8080
telnet localhost 3306                    # اختبر اتصال MySQL

# اختبر الخدمات
systemctl status docker                  # حالة Docker
systemctl status mariadb                 # حالة قاعدة البيانات
systemctl status redis-server            # حالة Redis
```

### معالجة الأخطاء الشائعة
```bash
# تحقق من المجال والـ DNS
nslookup 45.159.160.5
host 45.159.160.5

# اختبر استجابة المخدم
curl -I http://localhost:8080            # رؤوس الاستجابة فقط
curl -v http://localhost:8080            # مع التفاصيل الكاملة

# اختبر الاتصال بقاعدة البيانات
mysql -u erpnext -p -e "SELECT 1;"
```

---

## 📝 ملاحظات هامة

- **الحفظ دائماً**: احتفظ بنسخ احتياطية منتظمة
- **الأمان أولاً**: استخدم كلمات مرور قوية وجدار حماية
- **التوثيق**: احتفظ بسجل للتغييرات والتحديثات
- **المراقبة**: تابع السجلات والأداء بانتظام
- **التحديثات**: طبّق التحديثات الأمنية بسرعة

---

**آخر تحديث:** 2024  
**الحالة:** ✅ شامل ومختبر  
**الاستخدام:** للرجوع السريع أثناء العمل