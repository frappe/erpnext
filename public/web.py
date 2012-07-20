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
	from webnotes.utils import get_encoded_string
	try:
		if 'page' in webnotes.form_dict:
			html = get_html(webnotes.form_dict['page'])
		else:
			# show home page
			html = get_html('index')
	except Exception, e:
		html = get_html('404')
		
	content = []
	import webnotes.handler
	html = get_encoded_string(html)
	html, content = webnotes.handler.gzip_response(html, content)
	
	content += [
		"Content-Type: text/html",
		"",
	]
	
	webnotes.handler.print_content(content)
	print html

def get_html(page_name):
	import website.utils
	page_name = website.utils.scrub_page_name(page_name)
	
	comments = get_comments(page_name)
	
	import website.web_cache
	html = website.web_cache.get_html(page_name, comments)
	
	return html

def get_comments(page_name):
	import webnotes
	
	if page_name == '404':
		comments = """error: %s""" % webnotes.getTraceback()
	else:
		comments = """page: %s""" % page_name
		
	return comments

if __name__=="__main__":
	init()
	respond()