#!/usr/bin/python
from __future__ import unicode_literals
import os, commands, sys

def install():
	# get required details
	root_pwd = get_root_password()
	db_name, db_pwd = get_new_db_details()
	
	# install path
	install_path = os.getcwd()
	
	setup_folders(install_path)
	
	setup_conf(install_path, db_name, db_pwd)
	
	# setup paths
	sys.path.append('.')
	sys.path.append('lib')
	sys.path.append('app')
	
	setup_db(install_path, root_pwd, db_name)
	
	apply_patches(install_path)
	
	show_remaining_steps()
	
def setup_folders(path):
	execute_in_shell("git clone git://github.com/webnotes/wnframework.git lib", verbose=1)
	execute_in_shell("git clone git://github.com/webnotes/erpnext.git app", verbose=1)
	public = os.path.join(path, "public")
	os.mkdir(public)
	os.mkdir(os.path.join(public, "files"))
	os.mkdir(os.path.join(public, "backups"))
	os.mkdir(os.path.join(path, "logs"))
	
def setup_conf(path, db_name, db_pwd):
	# read template conf file
	with open(os.path.join(path, 'lib', 'conf', 'conf.py'), 'r') as template:
		content = template.read()

	# manipulate content
	import re

	# set new_dbname, new_dbpassword, files_path, backup_path, log_file_name
	content = re.sub("db_name.*", "db_name = '%s'" % db_name, content)
	content = re.sub("db_password.*", "db_password = '%s'" % db_pwd, content)

	# write conf file
	with open(os.path.join(path, 'conf.py'), 'w') as new_conf:
		new_conf.write(content)
	
def setup_db(path, root_pwd, db_name):
	source = os.path.join(path, 'app', "master.sql")
	execute_in_shell("gunzip -c %s.gz > %s" % (source, source), verbose=1)

	from webnotes.install_lib.install import Installer
	inst = Installer('root', root_pwd)
	inst.import_from_db(db_name, source_path=source, verbose = 1)
	execute_in_shell("rm %s" % source)
	
def apply_patches(path):
	# need to build before patches, once, so that all-web.js and all-web.css exists
	execute_in_shell("./lib/wnf.py -b", verbose=1)
	execute_in_shell("./lib/wnf.py --patch_sync_build", verbose=1)
	
	# set filemode false
	execute_in_shell("cd app && git config core.filemode false", verbose=1)
	execute_in_shell("cd lib && git config core.filemode false", verbose=1)
	
def get_root_password():
	# ask for root mysql password
	import getpass

	root_pwd = None
	while not root_pwd:
		root_pwd = getpass.getpass("MySQL Root user's Password: ")
	
	test_root_connection(root_pwd)
	
	return root_pwd
	
def test_root_connection(root_pwd):
	err, out = execute_in_shell("mysql -u root -p%s -e 'exit'" % \
		root_pwd.replace('$', '\$').replace(' ', '\ '))
	if "access denied" in out.lower():
		raise Exception("Incorrect MySQL Root user's password")
	
def get_new_db_details():
	return get_input("New ERPNext Database Name: "), \
		get_input("New ERPNext Database's Password: ")
	
def get_input(msg):
	val = None
	while not val:
		val = raw_input(msg)
	return val

def show_remaining_steps():
	steps_remaining = """
	Notes:
	------

	sample apache conf file
	#-----------------------------------------------------------
	SetEnv PYTHON_EGG_CACHE /var/www

	# you can change 99 to any other port

	Listen 99
	NameVirtualHost *:99
	<VirtualHost *:99>
		ServerName localhost
		DocumentRoot {path to erpnext's folder}/public
	    AddHandler cgi-script .cgi .xml .py

		<Directory {path to erpnext's folder}/public/>
			# directory specific options
			Options -Indexes +FollowSymLinks +ExecCGI

			# directory's index file
			DirectoryIndex web.py

			# rewrite rule
			RewriteEngine on

			# condition 1:
			# ignore login-page.html, app.html, blank.html, unsupported.html
			RewriteCond %{REQUEST_URI} ^((?!app\.html|blank\.html|unsupported\.html).)*$

			# condition 2: if there are no slashes
			# and file is .html or does not containt a .
			RewriteCond %{REQUEST_URI} ^(?!.+/)((.+\.html)|([^.]+))$

			# rewrite if both of the above conditions are true
			RewriteRule ^(.+)$ web.py?page=$1 [NC,L]

			AllowOverride all
			Order Allow,Deny
			Allow from all
		</Directory>
	</VirtualHost>
	#-----------------------------------------------------------

	To Do:

	* Configure apache/http conf file to point to public folder
	* chown recursively all files in your folder to apache user
	* login using: user="Administrator" and password="admin"

	"""

	print steps_remaining

def execute_in_shell(cmd, verbose=0):
	# using Popen instead of os.system - as recommended by python docs
	from subprocess import Popen, PIPE
	p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)

	# get err and output
	err, out = p.stderr.read(), p.stdout.read()

	if verbose:
		if err: print err
		if out: print out

	return err, out

if __name__=="__main__":
	install()