#!/usr/bin/env python

# Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
# 
# MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 


import cgi, cgitb, os, sys
cgitb.enable()

# import libs
sys.path.append('..')

import conf

sys.path.append('../lib/py')
sys.path.append(conf.modules_path)

import webnotes
import webnotes.handler
import webnotes.auth

def init():
	# make the form_dict
	webnotes.form = cgi.FieldStorage(keep_blank_values=True)
	for key in webnotes.form.keys():
		webnotes.form_dict[key] = webnotes.form.getvalue(key)

	# init request
	try:
		webnotes.http_request = webnotes.auth.HTTPRequest()
		return True
	except webnotes.AuthenticationError, e:
		return True
	#except webnotes.UnknownDomainError, e:
	#	print "Location: " + (conf.redirect_404)
	except webnotes.SessionStopped, e:
		if 'cmd' in webnotes.form_dict:
			webnotes.handler.print_json()
		else:
			print "Content-Type: text/html"
			print
			print """<html>
				<body style="background-color: #EEE;">
					<h3 style="width: 900px; background-color: #FFF; border: 2px solid #AAA; padding: 20px; font-family: Arial; margin: 20px auto">
						Updating.
						We will be back in a few moments...
					</h3>
				</body>
				</html>"""

def respond():
	import webnotes
	if 'cmd' in webnotes.form_dict:
		webnotes.handler.handle()
	else:
		print "Content-Type: text/html"
		print
		print "<html><head><script>window.location.href='index.html';</script></head></html>"

if __name__=="__main__":
	if init():
		respond()
