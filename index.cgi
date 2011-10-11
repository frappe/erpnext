#!/usr/bin/python
# main handler file

import cgi, cgitb, os, sys
cgitb.enable()

# import libs
sys.path.append('lib/py')
sys.path.append('erpnext')

import webnotes

webnotes.form = cgi.FieldStorage()

# make the form_dict
for key in webnotes.form.keys():
	webnotes.form_dict[key] = webnotes.form.getvalue(key)

# url comes with sid, redirect to html, sid set and all
if 'sid' in webnotes.form_dict:
	import webnotes.auth
	import webnotes.widgets.page_body

	webnotes.auth.HTTPRequest()

	print "Content-Type: text/html"

	# print cookies, if there ar additional cookies defined during the request, add them here
	if webnotes.cookies or webnotes.add_cookies:
		for c in webnotes.add_cookies.keys():
			webnotes.cookies[c] = webnotes.add_cookies[c]
		
		print webnotes.cookies

	print
	print webnotes.widgets.page_body.redirect_template % ('Redirecting...', 'index.html')

else:
	# pass on to legacy handler
	import webnotes.handler

