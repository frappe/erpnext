# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

#!/usr/bin/env python
from __future__ import unicode_literals
import os, sys
import argparse

is_redhat = is_debian = None
root_password = None

requirements = [
	"chardet", 
	"cssmin", 
	"dropbox", 
	"google-api-python-client", 
	"gunicorn", 
	"httplib2", 
	"jinja2", 
	"markdown2", 
	"markupsafe", 
	"mysql-python", 
	"pygeoip", 
	"python-dateutil", 
	"python-memcached", 
	"pytz==2013d", 
	"requests", 
	"six", 
	"slugify", 
	"termcolor", 
	"werkzeug"
]

def install(install_path):
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
		raise Exception, "Hey! ERPNext needs Python version to be 2.7+"
	
	# check distribution
	distribution = platform.linux_distribution()[0].lower().replace('"', '')
	print "Distribution = ", distribution
	is_redhat = distribution in ("redhat", "red hat enterprise linux server", "centos", "centos linux", "fedora")
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
	
	# set to autostart on startup
	for service in ("mysqld", "memcached", "ntpd"):
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
	global root_password
	if not root_password:
		root_password = get_root_password()
	exec_in_shell("echo mysql-server mysql-server/root_password password %s | sudo debconf-set-selections" % root_password)
	exec_in_shell("echo mysql-server mysql-server/root_password_again password %s | sudo debconf-set-selections" % root_password)
	
	if not exec_in_shell("which mysql"):
		packages = "mysql-server libmysqlclient-dev"
		print "Installing Packages:", packages
		exec_in_shell("apt-get install -y %s" % packages)
	
	update_config_for_debian()
	
def update_config_for_debian():
	for service in ("mysql", "ntpd"):
		exec_in_shell("service %s restart" % service)
	
def install_python_modules():
	print "-"*80
	print "Installing Python Modules: (This may take some time)"
	print "-"*80
	
	if not exec_in_shell("which pip"):
		exec_in_shell("easy_install pip")
	
	exec_in_shell("pip install --upgrade pip")
	exec_in_shell("pip install --upgrade setuptools")
	exec_in_shell("pip install --upgrade virtualenv")
	exec_in_shell("pip install {}".format(' '.join(requirements)))
	
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

	setup_cron(install_path)
	
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
	os.chdir(install_path)
	app = os.path.join(install_path, "app")
	if not os.path.exists(app):
		print "Cloning erpnext"
		exec_in_shell("cd %s && git clone https://github.com/webnotes/erpnext.git app" % install_path)
		exec_in_shell("cd app && git config core.filemode false")
		if not os.path.exists(app):
			raise Exception, "Couldn't clone erpnext repository"
	
	lib = os.path.join(install_path, "lib")
	if not os.path.exists(lib):
		print "Cloning wnframework"
		exec_in_shell("cd %s && git clone https://github.com/webnotes/wnframework.git lib" % install_path)
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
	pass

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

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--create_user', default=False, action='store_true')
	parser.add_argument('--username', default='erpnext')
	parser.add_argument('--password', default='erpnext')
	parser.add_argument('--no_install_prerequisites', default=False, action='store_true')
	return parser.parse_args()

def create_user(username, password):
	import subprocess, pwd
	p = subprocess.Popen("useradd -m -d /home/{username} -s {shell} {username}".format(username=username, shell=os.environ.get('SHELL')).split())
	p.wait()
	p = subprocess.Popen("passwd {username}".format(username=username).split(), stdin=subprocess.PIPE)
	p.communicate('{password}\n{password}\n'.format(password=password))
	p.wait()
	return pwd.getpwnam(username).pw_uid

def setup_cron(install_path):
	erpnext_cron_entries = [
		"*/3 * * * * cd %s && python2.7 lib/wnf.py --run_scheduler >> erpnext-sch.log 2>&1" % install_path,
		"0 */6 * * * cd %s && python2.7 lib/wnf.py --backup >> erpnext-backup.log 2>&1" % install_path
		]
	for row in erpnext_cron_entries:
		try:
			existing_cron = exec_in_shell("crontab -l")
			if row not in existing_cron:
				exec_in_shell('{ crontab -l; echo "%s"; } | crontab' % row)
		except:
			exec_in_shell('echo "%s" | crontab' % row)

if __name__ == "__main__":
	args = parse_args()
	install_path = os.getcwd()
	if os.getuid() != 0 and args.create_user and not args.no_install_prequisites:
		raise Exception, "Please run this script as root"

	if args.create_user:
		uid = create_user(args.username, args.password)
		install_path = '/home/{username}/erpnext'.format(username=args.username)

	if not args.no_install_prerequisites:
		install_pre_requisites()

	if os.environ.get('SUDO_UID') and not args.create_user:
		os.setuid(int(os.environ.get('SUDO_UID')))
	
	if os.getuid() == 0 and args.create_user:
		os.setuid(uid)
		if install_path:
			os.mkdir(install_path)
	
	install(install_path=install_path)
	print
	print "-"*80
	print "Installation complete"
	print "To start the development server,"
	print "Login as {username} with password {password}".format(username=args.username, password=args.password)
	print "cd {}".format(install_path)
	print "./lib/wnf.py --serve"
	print "-"*80
	print "Open your browser and go to http://localhost:8000"
	print "Login using username = Administrator and password = admin"
