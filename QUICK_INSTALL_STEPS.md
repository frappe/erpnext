# ⚡ خطوات التثبيت السريعة - Kanaan ERP

**نسخة مختصرة وسريعة لتثبيت التطبيق**

---

## 🔐 بيانات الاتصال بالسيرفر

```
Host: 45.159.160.5
Username: esplzswx
Password: q0Ju50iFb+m^6k]$
SSH Port: 22
```

---

## 🚀 التثبيت السريع (15-20 دقيقة)

### **1️⃣ الاتصال بالسيرفر**
```bash
ssh esplzswx@45.159.160.5
# أو من Windows PowerShell:
# sshpass -p 'q0Ju50iFb+m^6k]$' ssh -o StrictHostKeyChecking=no esplzswx@45.159.160.5
```

### **2️⃣ تحديث النظام**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl wget git python3.10 python3-pip nodejs npm
```

### **3️⃣ تثبيت Docker (اختياري)**
```bash
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker esplzswx
sudo systemctl restart docker
```

### **4️⃣ تثبيت قاعدة البيانات و Redis**
```bash
sudo apt install -y mariadb-server redis-server
sudo systemctl start mariadb redis-server
sudo systemctl enable mariadb redis-server
```

### **5️⃣ إعداد قاعدة البيانات**
```bash
mysql -u root -p
```

ثم الصق في MySQL:
```sql
CREATE DATABASE kanaan_erpnext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'erpnext'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON kanaan_erpnext.* TO 'erpnext'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### **6️⃣ استنساخ وتثبيت المشروع**
```bash
cd /home/esplzswx
git clone https://github.com/your-repo/kanaanerpgaza-develop.git
cd kanaanerpgaza-develop

# نسخ البيئة
cp .env.example .env

# تثبيت المتطلبات
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm ci && npm run build
```

### **7️⃣ بدء التطبيق**
```bash
# الخيار A: مع Docker (الأسهل)
docker-compose up -d

# الخيار B: بدون Docker
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 --workers 4 wsgi:application &
sudo systemctl start nginx
```

### **8️⃣ الوصول للتطبيق**
```
🌐 http://45.159.160.5
👤 Username: Administrator
🔑 Password: admin
```

---

## 📋 أوامر مهمة

```bash
# عرض حالة الخدمات
docker-compose ps

# عرض السجلات
docker-compose logs -f

# إعادة تشغيل
docker-compose restart

# إيقاف
docker-compose down

# بدء مجددًا
docker-compose up -d
```

---

## ⚠️ استكشاف الأخطاء

| المشكلة | الحل |
|--------|------|
| لا يعمل SSH | تحقق من IP والبيانات |
| منفذ مشغول | `sudo lsof -i :8080` ثم `sudo kill -9 PID` |
| خطأ قاعدة البيانات | تحقق من `DB_HOST` و `DB_USER` في `.env` |
| بطء الأداء | `docker stats` لمراقبة الموارد |

---

للمزيد من التفاصيل: انظر `MANUAL_SERVER_INSTALLATION.md`