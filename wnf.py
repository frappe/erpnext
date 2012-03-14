#!/usr/bin/env python

# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, sys

def replace_code(start, txt1, txt2, extn):
	"""replace all txt1 by txt2 in files with extension (extn)"""
	import os, re
	for wt in os.walk(start, followlinks=1):
		for fn in wt[2]:
			if fn.split('.')[-1]==extn:
				fpath = os.path.join(wt[0], fn)
				with open(fpath, 'r') as f:
					content = f.read()
				
				if re.search(txt1, content):
					a = raw_input('Change in %s [y/n]?' % fpath)
					if a=='y':
						with open(fpath, 'w') as f:
							f.write(re.sub(txt1, txt2, content))
				
						print 'updated in %s' % fpath

def setup_options():
	from optparse import OptionParser
	parser = OptionParser()

	parser.add_option("-d", "--db",
						dest="db_name",
						help="Apply the patches on given db")

	# build
	parser.add_option("-b", "--build", default=False, action="store_true",
						help="minify + concat js files")
	parser.add_option("-c", "--clear", default=False, action="store_true",
						help="increment version")

	# git
	parser.add_option("--status", default=False, action="store_true",
						help="git status")
	parser.add_option("--pull", nargs=2, default=False,
						metavar = "remote branch",
						help="git pull (both repos)")
	parser.add_option("--push", nargs=3, default=False, 
						metavar = "remote branch comment",
						help="git commit + push (both repos) [remote] [branch] [comment]")
	parser.add_option("-l", "--latest",
						action="store_true", dest="run_latest", default=False,
						help="Apply the latest patches")

	# patch
	parser.add_option("-p", "--patch", nargs=1, dest="patch_list", metavar='patch_module',
						action="append",
						help="Apply patch")
	parser.add_option("-f", "--force",
						action="store_true", dest="force", default=False,
						help="Force Apply all patches specified using option -p or --patch")
	parser.add_option('--reload_doc', nargs=3, metavar = "module doctype docname",
						help="reload doc")
	parser.add_option('--export_doc', nargs=2, metavar = "doctype docname",
						help="export doc")

	# install
	parser.add_option('--install', nargs=3, metavar = "rootpassword dbname source",
						help="install fresh db")
	parser.add_option('--sync_with_gateway', nargs=1, metavar = "1/0", \
						help="Set or Unset Sync with Gateway")

	# diff
	parser.add_option('--diff_ref_file', nargs=0, \
						help="Get missing database records and mismatch properties, with file as reference")
	parser.add_option('--diff_ref_db', nargs=0, \
						help="Get missing .txt files and mismatch properties, with database as reference")

	# scheduler
	parser.add_option('--run_scheduler', default=False, action="store_true",
						help="Trigger scheduler")
	parser.add_option('--run_scheduler_event', nargs=1, metavar="[all|daily|weekly|monthly]",
						help="Run scheduler event")

	# misc
	parser.add_option("--replace", nargs=3, default=False, 
						metavar = "search replace_by extension",
						help="file search-replace")

	parser.add_option("--cci", nargs=1, metavar="CacheItem Key",
		help="Clear Cache Item")
	

	return parser.parse_args()
	
def run():
	sys.path.append('lib')
	sys.path.append('lib/py')
	import webnotes
	import webnotes.defs
	sys.path.append(webnotes.defs.modules_path)

	(options, args) = setup_options()


	from webnotes.db import Database
	import webnotes.modules.patch_handler

	# connect
	if options.db_name is not None:
		webnotes.connect(options.db_name)

	# build
	if options.build:
		import build.project
		build.project.build()		

	elif options.clear:
		from build.project import increment_version
		print "Version:" + str(increment_version())
	
	# code replace
	elif options.replace:
		replace_code('.', options.replace[0], options.replace[1], options.replace[2])
	
	# git
	elif options.status:
		os.system('git status')
		os.chdir('lib')
		os.system('git status')
	
	elif options.pull:
		os.system('git pull %s %s' % (options.pull[0], options.pull[1]))
		os.chdir('lib')
		os.system('git pull %s %s' % (options.pull[0], options.pull[1]))

	elif options.push:
		os.system('git commit -a -m "%s"' % options.push[2])
		os.system('git push %s %s' % (options.push[0], options.push[1]))
		os.chdir('lib')
		os.system('git commit -a -m "%s"' % options.push[2])
		os.system('git push %s %s' % (options.push[0], options.push[1]))
	
	# patch
	elif options.patch_list:
		# clear log
		webnotes.modules.patch_handler.log_list = []
		
		# run individual patches
		for patch in options.patch_list:
			webnotes.modules.patch_handler.run_single(\
				patchmodule = patch, force = options.force)
		
		print '\n'.join(webnotes.modules.patch_handler.log_list)
	
		# reload
	elif options.reload_doc:
		webnotes.modules.patch_handler.reload_doc(\
			{"module":options.reload_doc[0], "dt":options.reload_doc[1], "dn":options.reload_doc[2]})		
		print '\n'.join(webnotes.modules.patch_handler.log_list)

	elif options.export_doc:
		from webnotes.modules import export_doc
		export_doc(options.export_doc[0], options.export_doc[1])

	# run all pending
	elif options.run_latest:
		webnotes.modules.patch_handler.run_all()
		print '\n'.join(webnotes.modules.patch_handler.log_list)
	
	elif options.install:
		from webnotes.install_lib.install import Installer
		inst = Installer('root', options.install[0])
		inst.import_from_db(options.install[1], source_path=options.install[2], \
			password='admin', verbose = 1)
	
	elif options.sync_with_gateway:
		if int(options.sync_with_gateway[0]) in [0, 1]:
			webnotes.conn.begin()
			webnotes.conn.sql("""\
				UPDATE `tabSingles` SET value=%s
				WHERE field='sync_with_gateway' AND doctype='Control Panel'""", int(options.sync_with_gateway[0]))
			webnotes.conn.commit()
			webnotes.message_log.append("sync_with_gateway set to %s" % options.sync_with_gateway[0])
		else:
			webnotes.message_log.append("ERROR: sync_with_gateway can be either 0 or 1")
	
	elif options.diff_ref_file is not None:
		import webnotes.modules.diff
		webnotes.modules.diff.diff_ref_file()

	elif options.diff_ref_db is not None:
		import webnotes.modules.diff
		webnotes.modules.diff.diff_ref_db()
	
	elif options.run_scheduler:
		import webnotes.utils.scheduler
		print webnotes.utils.scheduler.execute()
	
	elif options.run_scheduler_event is not None:
		import webnotes.utils.scheduler
		print webnotes.utils.scheduler.trigger('execute_' + options.run_scheduler_event)
	
	elif options.cci is not None:
		if options.cci=='all':
			webnotes.conn.sql("DELETE FROM __CacheItem")
		else:
			from webnotes.utils.cache import CacheItem
			CacheItem(options.cci).clear()

	# print messages
	if webnotes.message_log:
		print '\n'.join(webnotes.message_log)

if __name__=='__main__':
	run()
