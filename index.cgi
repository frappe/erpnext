#!/usr/bin/python

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


import cgi, cgitb, os, sys
cgitb.enable()

# import libs
sys.path.append('lib/py')
sys.path.append('erpnext')

import webnotes
import webnotes.handler
import webnotes.auth
import webnotes.defs

def init():
	# make the form_dict
	webnotes.form = cgi.FieldStorage(keep_blank_values=True)
	for key in webnotes.form.keys():
		webnotes.form_dict[key] = webnotes.form.getvalue(key)

	# init request
	try:
		webnotes.http_request = webnotes.auth.HTTPRequest()
	except webnotes.AuthenticationError, e:
		pass
	except webnotes.UnknownDomainError, e:
		print "Location: " + (webnotes.defs.redirect_404)

def respond():
	import webnotes
	if 'cmd' in webnotes.form_dict:
		webnotes.handler.handle()
	else:
		import webnotes.cms.index
		print "Content-Type: text/html"
		webnotes.handler.print_cookies()
		print
		print webnotes.cms.index.get()

if __name__=="__main__":
	init()
	respond()
