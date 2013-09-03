---
{
	"_label": "Restoring From ERPNext Backup"
}
---

* Download backup files

		cd /tmp
		wget [DATABASE BACKUP FILE URL]
		wget [FILES BACKUP FILE URL]

* Suppose your backup files are downloaded at /tmp

		gunzip [DATABASE BACKUP FILE.sql.gz]
		tar xvf [FILES BACKUP.tar]

* Go to your ERPNext installation folder
* When restoring from database, the 'Administrator' user password gets reset to 'admin'. To set a better password when restoring, set admin_password variable in conf.py to the desired 'Administrator' user password.
* Restore database using:

		lib/wnf.py --install [DATABASE NAME] /tmp/[DATABASE BACKUP FILE.sql]

* Copy extracted files

		cp /tmp/[FILES BACKUP EXTRACTED FOLDER/---/public/files/*] [YOUR ERPNEXT INSTALLATION]/public/files/