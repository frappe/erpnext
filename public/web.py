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

"""
	return a dynamic page from website templates

	all html pages related to website are generated here
"""
from __future__ import unicode_literals
import cgi, cgitb, os, sys
cgitb.enable()

# import libs
sys.path.append('..')
import conf
sys.path.append('../lib/py')
sys.path.append(conf.modules_path)

def init():
	import webnotes.handler
	webnotes.handler.get_cgi_fields()
	webnotes.connect()

def respond():
	import webnotes
	import website.utils
	return website.utils.render(webnotes.form_dict.get('page'))

if __name__=="__main__":
	init()
	respond()