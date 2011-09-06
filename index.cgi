#!/usr/bin/python
# main handler file

import cgi, cgitb, os, sys
cgitb.enable()

# import libs
sys.path.append('lib/py')
sys.path.append('erpnext')

import webnotes
import webnotes.defs

webnotes.form = cgi.FieldStorage()

# make the form_dict
for key in webnotes.form.keys():
	webnotes.form_dict[key] = webnotes.form.getvalue(key)

# pass on to legacy handler
import webnotes.handler
