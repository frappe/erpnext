---
{
	"_label": "How to Install ERPNext",
	"_toc": [
		"docs.dev.install.red_hat",
		"docs.dev.install.debian"
	]
}
---

> These are instructions that will help you to install ERPNext on your Unix like system (Linux / Ubuntu / MacOS) using the Terminal. If you are looking at easier ways to evaluate ERPNext, [see this page](docs.user.intro.try.html).

### ERPNext Installer (Beta)

Install ERPNext in one command!

1. Switch to root user using `sudo su`
1. create a folder where you want to install erpnext
1. go to the new folder
1. `wget https://gist.github.com/anandpdoshi/5991402/raw/5b3b451720a8575f8708e58a640b9a760d048392/install_erpnext.py`
1. `python install_erpnext.py`

> If you are installing on your server for deployment, remember to change Administrator's password!

> If you get stuck, post your questions at [ERPNext Developer Forum](https://groups.google.com/forum/#!forum/erpnext-developer-forum)

--
> [Server Setup Tips](http://plusbryan.com/my-first-5-minutes-on-a-server-or-essential-security-for-linux-servers)

> [MySQL configuration file - my.cnf](MySQL-configuration-file)

> [Some Useful Aliases](Some-Useful-Aliases)

---
### Upgrade / run latest patches

1. Backup your database!
1. go to Setup > Update This Application [under Update Manager]
1. click on 'Get Latest Updates'

> [Restoring from ERPNext backup](Restoring-From-ERPNext-Backup)

---
### Step by step instructions

1. You will need some linux background to be able to install this on your system.
1. These are high-level instructions and by no means cover every installation issue.

### Pre-requisites:

* any unix based os
* python 2.6+ (python 3+ not supported)
* apache
* mysql 5+
* git
* python libraries:
    * python MySQLdb
    * pytz
    * jinja2
    * markdown2
    * dateutil
    * termcolor
    * python-memcached
    * requests
    * chardet
    * pygeoip
    * dropbox
    * google-api-python-client
* memcached

## Fresh Installation

### Steps: [using terminal]

#### Get the Install Script

Download the standard install script and install. This script will:

- Create `app` and `lib` folders.
- Clone the code repositories for `wnframework` and `erpnext` from GitHub. It is important to clone the repositories from GitHub rather than just downloading the code, because this will help you in upgrading the system.
- Create the database.
- Create a default `erpnext.conf` Apache configuration file for ERPnext.
- Create the standard wnframework configuration file `conf.py`
- Build the `public` folder from which the ERPNext client application will be served via Apache and CGI.

**Instructions**

1. ensure mysql service is running
1. create a folder where you want to install erpnext
1. go to the new folder
1. `wget https://github.com/webnotes/erpnext/blob/master/install_erpnext.py`
1. `python install_erpnext.py`

#### Setup Apache

1. check your apache/httpd user and group. Most often it is either `apache` or `_www`. This can be found in its conf file.
1. run `chown -R apache:apache *` or `chown -R _www:_www *`. This will make the erpnext folder accessible to apache webserver.
1. create erpnext.conf file in erpnext folder and paste a modified version of apache configuration file as shown in the example below. (You will need to change the values in square brackets)
    * For debian systems, `sudo ln -s [PATH TO ERPNEXT INSTALLATION]/erpnext.conf /etc/apache2/sites-enabled/erpnext.conf`
    * For redhat systems, `sudo ln -s [PATH TO ERPNEXT INSTALLATION]/erpnext.conf /etc/httpd/conf.d/erpnext.conf`
1. restart apache service
1. if firewall exists, run
```
iptables -I INPUT 1 -p tcp --dport 8080 -j ACCEPT
service iptables save
```

### Setup Schueduler

1. setup cron using `crontab -e` and enter the following and then save it:
```
*/3 * * * * cd [PATH TO ERPNEXT INSTALLATION] && python lib/wnf.py --run_scheduler >> /var/log/erpnext-sch.log 2>&1
0 */6 * * * cd [PATH TO ERPNEXT INSTALLATION] && python lib/wnf.py --backup >> /var/log/erpnext-backup.log 2>&1
```

### Start

1. go to erpnext folder and run `lib/wnf.py --domain localhost:8080`
1. start your browser and go to http://localhost:8080
1. login as user: Administrator and password: admin

> If you are installing on your server for deployment, remember to change Administrator's password!

### What to write in apache configuration file? 

	Listen 8080
	NameVirtualHost *:8080
	<VirtualHost *:8080>
		ServerName localhost
		DocumentRoot [PATH TO ERPNEXT INSTALLATION]/public/
		
		AddHandler cgi-script .cgi .xml .py
		AddType application/vnd.ms-fontobject .eot
		AddType font/ttf .ttf
		AddType font/otf .otf
		AddType application/x-font-woff .woff

		<Directory [PATH TO ERPNEXT INSTALLATION]/public/>
			# directory specific options
			Options -Indexes +FollowSymLinks +ExecCGI
		
			# directory's index file
			DirectoryIndex web.py
			
			AllowOverride all
			Order Allow,Deny
			Allow from all

			# rewrite rule
			RewriteEngine on
			RewriteCond %{REQUEST_FILENAME} !-f
			RewriteCond %{REQUEST_FILENAME} !-d
			RewriteCond %{REQUEST_FILENAME} !-l
			RewriteRule ^([^/]+)$ /web.py?page=$1 [QSA,L]		
		</Directory>
	</VirtualHost>
