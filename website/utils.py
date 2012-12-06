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

from __future__ import unicode_literals
import webnotes

def render(page_name):
	"""render html page"""
	try:
		if page_name:
			html = get_html(page_name)
		else:
			html = get_html('index')
	except Exception, e:
		html = get_html('404')

	from webnotes.handler import eprint, print_zip
	eprint("Content-Type: text/html")
	print_zip(html)

def get_html(page_name):
	"""get page html"""
	page_name = scrub_page_name(page_name)
	comments = get_comments(page_name)
	
	from website.web_cache import get_page_html
	html = get_page_html(page_name, comments)
	return html

def get_comments(page_name):	
	if page_name == '404':
		comments = """error: %s""" % webnotes.getTraceback()
	else:
		comments = """page: %s""" % page_name
		
	return comments
	
def scrub_page_name(page_name):
	if page_name.endswith('.html'):
		page_name = page_name[:-5]

	return page_name

def make_template(doc, path, convert_fields = ['main_section', 'side_section']):
	"""make template"""
	import os, jinja2
		
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

def update_page_name(doc, title):
	"""set page_name and check if it is unique"""
	webnotes.conn.set(doc, "page_name", page_name(title))
	
	res = webnotes.conn.sql("""\
		select count(*) from `tab%s`
		where page_name=%s and name!=%s""" % (doc.doctype, '%s', '%s'),
		(doc.page_name, doc.name))
	if res and res[0][0] > 0:
		webnotes.msgprint("""A %s with the same title already exists.
			Please change the title of %s and save again."""
			% (doc.doctype, doc.name), raise_exception=1)
