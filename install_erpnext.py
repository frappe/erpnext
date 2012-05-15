#!/usr/bin/python
import os, commands

# ask for root mysql password
import getpass

root_pwd = None
while not root_pwd:
	root_pwd = getpass.getpass("MySQL Root user's Password: ")
	
# test root connection
op = commands.getoutput("mysql -u root -p%s -e 'exit'" % \
	root_pwd.replace('$', '\$').replace(' ', '\ '))
if "access denied" in op.lower():
	raise Exception("Incorrect MySQL Root user's password")

# ask for new dbname
new_dbname = None
while not new_dbname:
	new_dbname = raw_input("New ERPNext Database Name: ")

# ask for new dbpassword
new_dbpassword = None
while not new_dbpassword:
	new_dbpassword = raw_input("New ERPNext Database's Password: ")

# get erpnext path
erpnext_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(erpnext_path)

# setup backups
if not os.path.exists(os.path.join(erpnext_path, 'backups')):
	os.makedirs('backups')
	os.symlink(os.path.join(erpnext_path, 'backups'),
		os.path.join(erpnext_path, 'public', 'backups'))
	
# setup files
if not os.path.exists(os.path.join(erpnext_path, 'files')):
	os.makedirs('files')
	os.symlink(os.path.join(erpnext_path, 'files'),
		os.path.join(erpnext_path, 'public', 'files'))

# setup logs
if not os.path.exists(os.path.join(erpnext_path, 'logs')):
	os.makedirs('logs')
	os.system('touch logs/error_log.txt')

# setup lib -- framework repo with read only access
# change this if you have your own fork
if not os.path.exists(os.path.join(erpnext_path, 'lib')):
	os.system('git clone git://github.com/webnotes/wnframework.git lib')

# setup symlinks in public
if not os.path.exists(os.path.join(erpnext_path, 'public', 'js', 'lib')):
	os.symlink(os.path.join(erpnext_path, 'lib', 'js', 'lib'),
		os.path.join(erpnext_path, 'public', 'js', 'lib'))
if not os.path.exists(os.path.join(erpnext_path, 'public', 'images', 'lib')):
	os.symlink(os.path.join(erpnext_path, 'lib', 'images'),
		os.path.join(erpnext_path, 'public', 'images', 'lib'))

# extract master
if os.path.exists(os.path.join(erpnext_path, 'data', 'master.sql.gz')):
	os.system('gunzip data/master.sql.gz')

# setup conf
if not os.path.exists(os.path.join(erpnext_path, 'conf.py')):
	# read template conf file
	with open(os.path.join(erpnext_path, 'lib', 'conf', 'conf.py'), 'r') as template:
		content = template.read()
	
	# manipulate content
	import re
	
	# set new_dbname, new_dbpassword, modules_path, files_path, backup_path, log_file_name
	content = re.sub("db_name.*", "db_name = '%s'" % new_dbname, content)
	content = re.sub("db_password.*", "db_password = '%s'" % new_dbpassword, content)
	content = re.sub("modules_path.*", "modules_path = '%s'" % \
		os.path.join(erpnext_path, 'erpnext'), content)
	content = re.sub("files_path.*", "files_path = '%s'" % \
		os.path.join(erpnext_path, 'files'), content)
	content = re.sub("backup_path.*", "backup_path = '%s'" % \
		os.path.join(erpnext_path, 'backups'), content)
	content = re.sub("log_file_name.*", "log_file_name = '%s'" % \
		os.path.join(erpnext_path, 'logs', 'error_log.txt'), content)
		
	
	# write conf file
	with open(os.path.join(erpnext_path, 'conf.py'), 'w') as new_conf:
		new_conf.write(content)	

# install db
import sys
sys.path.append(erpnext_path)
sys.path.append(os.path.join(erpnext_path, 'lib', 'py'))
import conf
sys.path.append(conf.modules_path)

from webnotes.install_lib.install import Installer
inst = Installer('root', root_pwd)
inst.import_from_db(new_dbname, source_path=os.path.join(erpnext_path, 'data', 'master.sql'), verbose = 1)

# apply patches
os.chdir(erpnext_path)
os.system("lib/wnf.py -l")

# force sync all
os.system("lib/wnf.py --sync_all -f")

# create website files
from webnotes.model.code import get_obj
# rewrite pages
ws = get_obj('Website Settings')
ws.rewrite_pages()
ss = get_obj('Style Settings')
ss.validate()
ss.on_update()

# set filemode false
os.system("git config core.filemode false")
os.chdir(os.path.join(erpnext_path, 'lib'))
os.system("git config core.filemode false")

steps_remaining = """
To Do:

* Configure apache/http conf file to point to public folder
* chown recursively all files in your folder to apache user
* login using: user="Administrator" and password="admin"
"""

print steps_remaining

