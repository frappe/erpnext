#!/usr/bin/python
# main handler file

import cgi, cgitb, os, sys
cgitb.enable()

# import libs
sys.path.append('lib/py')
sys.path.append('erpnext')

import webnotes
import webnotes.handler
import webnotes.auth

def init():
	# make the form_dict
	webnotes.form = cgi.FieldStorage(keep_blank_values=True)
	for key in webnotes.form.keys():
		webnotes.form_dict[key] = webnotes.form.getvalue(key)

	# init request
	webnotes.http_request = webnotes.auth.HTTPRequest()

def respond():
	import webnotes
	if 'cmd' in webnotes.form_dict:
		webnotes.handler.handle()
	else:
		import webnotes.index
		print "Content-Type: text/html"
		webnotes.handler.print_cookies()
		print
		print webnotes.index.get()

if __name__=="__main__":
	init()
	respond()