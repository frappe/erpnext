# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

#!/usr/bin/env python
from __future__ import unicode_literals
import os, sys

is_redhat = is_debian = None
root_password = None

requirements = [ 
	"MySQL-python",
	"pytz==2013b",
	"python-dateutil",
	"jinja2",
	"markdown2",
	"termcolor",
	"python-memcached",
	"requests",
	"chardet",
	"dropbox",
	"google-api-python-client ",
	"pygeoip"
]

def install(install_path=None):
	if os.getuid() != 0:
		raise Exception, "Please run this script as root"

	install_pre_requisites()

	if os.environ.get('SUDO_UID'):
		os.setuid(int(os.environ.get('SUDO_UID')))
	
	if not install_path:
		install_path = os.getcwd()
	setup_folders(install_path)
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
	if not (python_version and int(python_version.split(".")[0])==2 and int(python_version.split(".")[1]) >= 7):
		raise Exception, "Hey! ERPNext needs Python version to be 2.6+"
	
	# check distribution
	distribution = platform.linux_distribution()[0].lower().replace('"', '')
	print "Distribution = ", distribution
	is_redhat = distribution in ("redhat", "centos", "centos linux", "fedora")
	is_debian = distribution in ("debian", "ubuntu", "elementary os", "linuxmint")
	
	if not (is_redhat or is_debian):
		raise Exception, "Sorry! This installer works only with yum or apt-get package management"
	
	return is_redhat, is_debian
		
def install_using_yum():
	packages = "python python-setuptools gcc python-devel MySQL-python git memcached ntp vim-enhanced screen"
	
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
	exec_in_shell("apt-get update")
	packages = "python python-setuptools python-dev build-essential python-pip python-mysqldb git memcached ntp vim screen htop"
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

	# update memcache user
	with open("/etc/memcached.conf", "r") as original:
		memcached_conf = original.read()
	with open("/etc/memcached.conf", "w") as modified:
		modified.write(memcached_conf.replace("-u memcache", "-u %s" % apache_user))
	
	for service in ("mysql", "memcached", "ntpd"):
		exec_in_shell("service %s restart" % service)
	
def install_python_modules():
	print "-"*80
	print "Installing Python Modules: (This may take some time)"
	print python_modules
	print "-"*80
	
	if not exec_in_shell("which pip"):
		exec_in_shell("easy_install pip")
	
	exec_in_shell("pip install --upgrade pip")
	exec_in_shell("pip install --upgrade setuptools")
	exec_in_shell("pip install --upgrade virtualenv")
	exec_in_shell("pip install -r {}".format(' '.join(requirements)))
	
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
	
	# setup paths
	sys.path = [".", "lib", "app"] + sys.path
	import wnf
	
	# install database, run patches, update schema
	# setup_db(install_path, root_password, db_name)
	wnf.install(db_name, root_password=root_password)

	# setup_cron(install_path)
	
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
		exec_in_shell("cd %s && git clone https://github.com/webnotes/erpnext.git app && cd app && git checkout wsgi" % install_path)
		exec_in_shell("cd app && git config core.filemode false")
		if not os.path.exists(app):
			raise Exception, "Couldn't clone erpnext repository"
	
	lib = os.path.join(install_path, "lib")
	if not os.path.exists(lib):
		print "Cloning wnframework"
		exec_in_shell("cd %s && git clone https://github.com/webnotes/wnframework.git lib && cd lib && git checkout wsgi" % install_path)
		exec_in_shell("cd lib && git config core.filemode false")
		if not os.path.exists(lib):
			raise Exception, "Couldn't clone wnframework repository"
	
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
	
def post_install(install_path):
	print
	print "-"*80
	print "To start the development server, run lib/wnf.py --serve"
	print "-"*80
	print "Installation complete"
	print "Open your browser and go to http://localhost:8000"
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
			if out: out = out.decode('utf-8')

			stderr.seek(0)
			err = stderr.read()
			if err: err = err.decode('utf-8')

	if err and any((kw in err.lower() for kw in ["traceback", "error", "exception"])):
		print out
		raise Exception, err
	else:
		print "."

	return out

if __name__ == "__main__":
	install()
