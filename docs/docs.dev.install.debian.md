---
{
	"_label": "ERPNext Pre-requisites for Debian systems (Unbuntu)"
}
---
#### If not root user
`sudo su`

#### Installing Pre-Requisites

	cd ~
	apt-get install python python-setuptools python-mysqldb apache2 mysql-server libmysqlclient-dev git memcached -y
	easy_install pip
	pip install pytz python-dateutil jinja2 markdown2 termcolor python-memcached requests chardet dropbox google-api-python-client pygeoip
	a2enmod rewrite
	service apache2 start
	service mysql start
	memcached -d -l 127.0.0.1 -p 11211 -m 64 -u www-data 

> ```memcached -d -l 127.0.0.1 -p 11211 -m [64 or more mb of ram] -u apache ```

#### Other useful programs

	apt-get install ntp vim screen htop -y
	service ntpd start
