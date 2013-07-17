#!/usr/bin/env python
from __future__ import unicode_literals
import os, sys

apache_user = None
is_redhat = is_debian = None
root_password = None

def install(install_path=None):
	install_pre_requisites()
	
	if not install_path:
		install_path = os.getcwd()
	install_erpnext(install_path)
	
	post_install(install_path)
	
def install_pre_requisites():
	global is_redhat, is_debian
	is_redhat, is_debian = validate_install()
	if is_redhat:
		install_using_yum()
	elif is_debian:
		install_using_apt()
		
	install_python_modules()
	
	print "-"*80
	print "Pre-requisites Installed"
	print "-"*80

def validate_install():
	import platform

	# check os
	operating_system = platform.system()
	print "Operating System =", operating_system
	if operating_system != "Linux":
		raise Exception, "Sorry! This installer works only for Linux based Operating Systems"
	
	# check python version
	python_version = sys.version.split(" ")[0]
	print "Python Version =", python_version
	if not (python_version and int(python_version.split(".")[0])==2 and int(python_version.split(".")[1]) >= 6):
		raise Exception, "Hey! ERPNext needs Python version to be 2.6+"
	
	# check distribution
	distribution = platform.linux_distribution()[0].lower().replace('"', '')
	print "Distribution = ", distribution
	is_redhat = distribution in ("redhat", "centos", "fedora")
	is_debian = distribution in ("debian", "ubuntu", "elementary os")
	
	if not (is_redhat or is_debian):
		raise Exception, "Sorry! This installer works only with yum or apt-get package management"
	
	return is_redhat, is_debian
		
def install_using_yum():
	packages = "python python-setuptools MySQL-python httpd git memcached ntp vim-enhanced screen"
	
	print "-"*80
	print "Installing Packages: (This may take some time)"
	print packages
	print "-"*80
	exec_in_shell("yum install -y %s" % packages)
	
	if not exec_in_shell("which mysql"):
		packages = "mysql mysql-server mysql-devel"
		print "Installing Packages:", packages
		exec_in_shell("yum install -y %s" % packages)
		exec_in_shell("service mysqld restart")
		
		# set a root password post install
		global root_password
		print "Please create a password for root user of MySQL"
		root_password = (get_root_password() or "erpnext").strip()
		exec_in_shell('mysqladmin -u root password "%s"' % (root_password,))
		print "Root password set as", root_password
	
	# install htop
	if not exec_in_shell("which htop"):
		try:
			exec_in_shell("cd /tmp && rpm -i --force http://packages.sw.be/rpmforge-release/rpmforge-release-0.5.2-2.el6.rf.x86_64.rpm && yum install -y htop")
		except:
			pass
	
	update_config_for_redhat()
	
def update_config_for_redhat():
	import re
	
	global apache_user
	apache_user = "apache"
	
	# update memcache user
	with open("/etc/sysconfig/memcached", "r") as original:
		memcached_conf = original.read()
	with open("/etc/sysconfig/memcached", "w") as modified:
		modified.write(re.sub('USER.*', 'USER="%s"' % apache_user,  memcached_conf))
	
	# set to autostart on startup
	for service in ("mysqld", "httpd", "memcached", "ntpd"):
		exec_in_shell("chkconfig --level 2345 %s on" % service)
		exec_in_shell("service %s restart" % service)
	
def install_using_apt():
	packages = "python python-setuptools python-mysqldb apache2 git memcached ntp vim screen htop"
	print "-"*80
	print "Installing Packages: (This may take some time)"
	print packages
	print "-"*80
	exec_in_shell("apt-get install -y %s" % packages)
	
	if not exec_in_shell("which mysql"):
		packages = "mysql-server libmysqlclient-dev"
		print "Installing Packages:", packages
		exec_in_shell("apt-get install -y %s" % packages)
	
	update_config_for_debian()
	
def update_config_for_debian():
	global apache_user
	apache_user = "www-data"

	# update memcache user
	with open("/etc/memcached.conf", "r") as original:
		memcached_conf = original.read()
	with open("/etc/memcached.conf", "w") as modified:
		modified.write(memcached_conf.replace("-u memcache", "-u %s" % apache_user))
	
	exec_in_shell("a2enmod rewrite")
	
	for service in ("mysql", "apache2", "memcached", "ntpd"):
		exec_in_shell("service %s restart" % service)
	
def install_python_modules():
	python_modules = "pytz python-dateutil jinja2 markdown2 termcolor python-memcached requests chardet dropbox google-api-python-client pygeoip"

	print "-"*80
	print "Installing Python Modules: (This may take some time)"
	print python_modules
	print "-"*80
	
	exec_in_shell("easy_install pip")
	exec_in_shell("pip install -q %s" % python_modules)
	
def install_erpnext(install_path):
	print
	print "-"*80
	print "Installing ERPNext"
	print "-"*80
	
	# ask for details
	global root_password
	if not root_password:
		root_password = get_root_password()
		test_root_connection(root_password)
	
	db_name = raw_input("ERPNext Database Name: ")
	if not db_name:
		raise Exception, "Sorry! You must specify ERPNext Database Name"
	
	# install folders and conf
	setup_folders(install_path)
	setup_conf(install_path, db_name)
	
	# setup paths
	sys.path.extend([".", "lib", "app"])
	
	# install database, run patches, update schema
	setup_db(install_path, root_password, db_name)
	
	setup_cron(install_path)
	
	setup_apache_conf(install_path)
	
def get_root_password():
	# ask for root mysql password
	import getpass
	root_pwd = None
	root_pwd = getpass.getpass("MySQL Root user's Password: ")
	return root_pwd
	
def test_root_connection(root_pwd):
	out = exec_in_shell("mysql -u root %s -e 'exit'" % \
		(("-p"+root_pwd) if root_pwd else "").replace('$', '\$').replace(' ', '\ '))
	if "access denied" in out.lower():
		raise Exception("Incorrect MySQL Root user's password")
		
def setup_folders(install_path):
	app = os.path.join(install_path, "app")
	if not os.path.exists(app):
		print "Cloning erpnext"
		exec_in_shell("cd %s && git clone https://github.com/webnotes/erpnext.git app" % install_path)
		exec_in_shell("cd app && git config core.filemode false")
	
	lib = os.path.join(install_path, "lib")
	if not os.path.exists(lib):
		print "Cloning wnframework"
		exec_in_shell("cd %s && git clone https://github.com/webnotes/wnframework.git lib" % install_path)
		exec_in_shell("cd lib && git config core.filemode false")
	
	public = os.path.join(install_path, "public")
	for p in [public, os.path.join(public, "files"), os.path.join(public, "backups"),
		os.path.join(install_path, "logs")]:
			if not os.path.exists(p):
				os.mkdir(p)
				
def setup_conf(install_path, db_name):
	import os, string, random, re

	# generate db password
	char_range = string.ascii_letters + string.digits
	db_password = "".join((random.choice(char_range) for n in xrange(16)))
	
	# make conf file
	with open(os.path.join(install_path, "lib", "conf", "conf.py"), "r") as template:
		conf = template.read()
	
	conf = re.sub("db_name.*", 'db_name = "%s"' % (db_name,), conf)
	conf = re.sub("db_password.*", 'db_password = "%s"' % (db_password,), conf)
	
	with open(os.path.join(install_path, "conf.py"), "w") as conf_file:
		conf_file.write(conf)
	
	return db_password
	
def setup_db(install_path, root_password, db_name):
	from webnotes.install_lib.install import Installer
	inst = Installer("root", root_password)
	inst.import_from_db(db_name, verbose=1)

	# run patches and sync
	exec_in_shell("./lib/wnf.py --patch_sync_build")
	
def setup_cron(install_path):
	erpnext_cron_entries = [
		"*/3 * * * * cd %s && python lib/wnf.py --run_scheduler >> /var/log/erpnext-sch.log 2>&1" % install_path,
		"0 */6 * * * cd %s && python lib/wnf.py --backup >> /var/log/erpnext-backup.log 2>&1" % install_path
		]
	
	for row in erpnext_cron_entries:
		try:
			existing_cron = exec_in_shell("crontab -l")
			if row not in existing_cron:
				exec_in_shell('{ crontab -l; echo "%s"; } | crontab' % row)
		except:
			exec_in_shell('echo "%s" | crontab' % row)
	
def setup_apache_conf(install_path):
	apache_conf_content = """Listen 8080
NameVirtualHost *:8080
<VirtualHost *:8080>
	ServerName localhost
	DocumentRoot %s/public/
	
	AddHandler cgi-script .cgi .xml .py
	AddType application/vnd.ms-fontobject .eot
	AddType font/ttf .ttf
	AddType font/otf .otf
	AddType application/x-font-woff .woff

	<Directory %s/public/>
		# directory specific options
		Options -Indexes +FollowSymLinks +ExecCGI
	
		# directory's index file
		DirectoryIndex web.py
		
		AllowOverride all
		Order Allow,Deny
		Allow from all

		# rewrite rule
		RewriteEngine on
		RewriteCond %%{REQUEST_FILENAME} !-f
		RewriteCond %%{REQUEST_FILENAME} !-d
		RewriteCond %%{REQUEST_FILENAME} !-l
		RewriteRule ^([^/]+)$ /web.py?page=$1 [QSA,L]		
	</Directory>
</VirtualHost>""" % (install_path, install_path)
	
	new_apache_conf_path = os.path.join(install_path, os.path.basename(install_path)+".conf")
	with open(new_apache_conf_path, "w") as apache_conf_file:
		apache_conf_file.write(apache_conf_content)

def post_install(install_path):
	global apache_user
	exec_in_shell("chown -R %s %s" % (apache_user, install_path))
	
	apache_conf_filename = os.path.basename(install_path)+".conf"
	if is_redhat:
		os.symlink(os.path.join(install_path, apache_conf_filename), 
			os.path.join("/etc/httpd/conf.d", apache_conf_filename))
		exec_in_shell("service httpd restart")
		
	elif is_debian:
		os.symlink(os.path.join(install_path, apache_conf_filename), 
			os.path.join("/etc/apache2/sites-enabled", apache_conf_filename))
		exec_in_shell("service apache2 restart")
	
	print
	print "-"*80
	print "Installation complete"
	print "Open your browser and go to http://localhost:8080"
	print "Login using username = Administrator and password = admin"

def exec_in_shell(cmd):
	# using Popen instead of os.system - as recommended by python docs
	from subprocess import Popen
	import tempfile

	with tempfile.TemporaryFile() as stdout:
		with tempfile.TemporaryFile() as stderr:
			p = Popen(cmd, shell=True, stdout=stdout, stderr=stderr)
			p.wait()

			stdout.seek(0)
			out = stdout.read()

			stderr.seek(0)
			err = stderr.read()

	if err and any((kw in err.lower() for kw in ["traceback", "error", "exception"])):
		print out
		raise Exception, err
	else:
		print "."

	return out

if __name__ == "__main__":
	install()