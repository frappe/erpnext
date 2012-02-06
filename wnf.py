#!/usr/bin/env python

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
	parser.add_option("-b", "--build", default=False, action="store_true",
						help="minify + concat js files")
	parser.add_option("-c", "--clear", default=False, action="store_true",
						help="increment version")
	parser.add_option("--replace", nargs=3, default=False, 
						metavar = "search replace_by extension",
						help="file search-replace")
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
	parser.add_option("-p", "--patch", nargs=1, dest="patch_list", metavar='patch_module',
						action="append",
						help="Apply patch")
	parser.add_option("-f", "--force",
						action="store_true", dest="force", default=False,
						help="Force Apply all patches specified using option -p or --patch")
	parser.add_option("-d", "--db",
						dest="db_name",
						help="Apply the patches on given db")
	parser.add_option('-r', '--reload_doc', nargs=3, metavar = "module doctype docname",
						help="reload doc")
	
	return parser.parse_args()
	
def run():
	sys.path.append('.')
	sys.path.append('lib/py')
	import webnotes
	import webnotes.defs
	sys.path.append(webnotes.defs.modules_path)

	(options, args) = setup_options()


	from webnotes.db import Database
	import webnotes.modules.patch_handler

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
		
		# connect to db
		if options.db_name is not None:
			webnotes.connect(options.db_name)
		else:
			webnotes.connect()
	
		# run individual patches
		for patch in options.patch_list:
			webnotes.modules.patch_handler.run_single(\
				patchmodule = patch, force = options.force)
		
		print '\n'.join(webnotes.modules.patch_handler.log_list)
	
		# reload
	elif options.reload_doc:
		webnotes.modules.patch_handler.reload_doc(\
			{"module":args[0], "dt":args[1], "dn":args[2]})		
		print '\n'.join(webnotes.modules.patch_handler.log_list)

	# run all pending
	elif options.run_latest:
		webnotes.modules.patch_handler.run_all()
		print '\n'.join(webnotes.modules.patch_handler.log_list)
		
if __name__=='__main__':
	run()
