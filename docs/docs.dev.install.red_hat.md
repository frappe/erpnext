---
{
	"_label": "ERPNext Pre-requisites for Red Hat systems (CentOS, Fedora)"
}
---
#### If not root user
`sudo su`

#### Installing Pre-Requisites

	cd ~
	yum update python -y
	yum install python-setuptools MySQL-python httpd mysql mysql-server mysql-devel git memcached ntp vim -y
	easy_install pip
	pip install pytz python-dateutil jinja2 markdown2 termcolor python-memcached requests chardet dropbox google-api-python-client pygeoip
	service httpd start
	service mysqld start
	service ntpd start
	mysqladmin -u root password [NEW PASSWORD]

#### memcached

1. `vim /etc/sysconfig/memcached`
1. change user to the apache user, change the cache size if desired (depending on available memory), save the file
1. `service memcached start`

#### set services to run when machine starts

	chkconfig --level 2345 mysql on
	chkconfig --level 2345 httpd on
	chkconfig --level 2345 memcached on
	chkconfig --level 2345 ntpd on

#### Other useful programs

wget http://packages.sw.be/rpmforge-release/rpmforge-release-0.5.2-2.el6.rf.x86_64.rpm
rpm -i http://packages.sw.be/rpmforge-release/rpmforge-release-0.5.2-2.el6.rf.x86_64.rpm
yum install htop screen -y

--

#### CPanel Users

If you are using CPanel, you are likely to face perl dependency issues when installing git. To install git in this case, follow this procedure:

1. `vim /etc/yum.conf`, remove perl* from exclude list and save the file
1. `yum install git -y`
1. `vim /etc/yum.conf`, add perl* back to exclude list and save the file

> source: [http://forums.cpanel.net/f5/upcp-errors-due-dependeny-problems-centos-6-3-not-upgraded-centos-6-4-a-332102.html](http://forums.cpanel.net/f5/upcp-errors-due-dependeny-problems-centos-6-3-not-upgraded-centos-6-4-a-332102.html)

CPanel users should follow these steps to set the apache configuration for ERPNext:

1. `vim /etc/httpd/conf/includes/post_virtualhost_2.conf`
1. add the line `Include [PATH TO ERPNEXT CONF FILE]` (example: /var/www/erpnext.conf) and save the file
1. `vim [PATH TO ERPNEXT CONF FILE]`, set the apache configuration for ERPNext and save it
1. `service httpd restart`

*The mysql root password may be found at* `/root/.my.cnf`