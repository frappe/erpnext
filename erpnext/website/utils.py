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

import webnotes
from webnotes.model.doc import Document

def scrub_page_name(page_name):
	if page_name.endswith('.html'):
		page_name = page_name[:-5]

	return page_name

def make_template(doc, path, convert_fields = ['main_section', 'side_section']):
	"""make template"""
	import os, jinja2
	
	markdown(doc, convert_fields)
	
	# write template
	with open(path, 'r') as f:
		temp = jinja2.Template(f.read())
	
	return temp.render(doc = doc.fields)

def page_name(title):
	"""make page name from title"""
	import re
	name = title.lower()
	name = re.sub('[~!@#$%^&*()<>,."\']', '', name)
	return '-'.join(name.split()[:4])

def render(page_name):
	"""render html page"""
	import webnotes
	try:
		if page_name:
			html = get_html(page_name)
		else:
			html = get_html('index')
	except Exception, e:
		html = get_html('404')

	print "Content-Type: text/html"
	print
	print html.encode('utf-8')
	
def get_html(page_name):
	"""get page html"""
	page_name = scrub_page_name(page_name)
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
