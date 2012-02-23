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

def make_template(doc, path, convert_fields = ['main_section', 'side_section']):
	"""make template"""
	import os, jinja2
	
	markdown(doc, convert_fields)
	
	# write template
	with open(path, 'r') as f:
		temp = jinja2.Template(f.read())
	
	return temp.render(doc = doc.fields)

def markdown(doc, fields):
	"""convert fields to markdown"""
	import markdown2
	# markdown
	for f in fields:
		doc.fields[f + '_html'] = markdown2.markdown(doc.fields[f] or '', \
			extras=["wiki-tables"])


def page_name(title):
	"""make page name from title, and check that there is no duplicate"""
	import re
	name = title.lower()
	name = re.sub('[~!@#$%^&*()<>,."\']', '', name)
	return '-'.join(name.split()[:4])
	
def add_page(title):
	"""add a custom page with title"""
	name = page_name(title)
	if webnotes.conn.sql("""select name from tabPage where name=%s""", name):
		p = Document('Page', name)
	else:
		p = Document('Page')
		
	p.title = title
	p.name = p.page_name = name
	p.module = 'Website'
	p.standard = 'No'

	return p
	
def add_guest_access_to_page(page):
	"""add Guest in Page Role"""
	if not webnotes.conn.sql("""select parent from `tabPage Role`
		where role='Guest' and parent=%s""", page):
		d = Document('Page Role')
		d.parent = page
		d.role = 'Guest'
		d.save()
