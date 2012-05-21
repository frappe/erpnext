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
	import webnotes.cms
	return webnotes.cms.page_name(title)
	
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

def get_header(page_name):
	"""get page header"""

	from webnotes.model.doc import Document
	from jinja2 import Template
	import webnotes.utils

	def get_item(l, label):
		for i in l:
			if i['label']==label:
				return i

	top_bar_items = webnotes.conn.sql("""select * from `tabTop Bar Item`
		where parent='Website Settings' and parentfield='top_bar_items'
		order by idx asc""", as_dict=1)
		
	# build child items
	for t in top_bar_items:
		if t.get('parent_label'):
			pi = get_item(top_bar_items, t['parent_label'])
			if 'child_items' not in pi:
				pi['child_items'] = []
			pi['child_items'].append(t)

	website_settings = Document('Website Settings', 'Website Settings')
	
	return Template("""<div class="navbar navbar-fixed-top">
		<div class="navbar-inner">
		<div class="container">
			<a class="brand" href="index.html">{{ brand }}</a>
			<ul class="nav">
				{% for page in top_bar_items %}
					{% if not page.parent_label %}
					<li data-label="{{ page.label }}">
						<a href="{{ page.url }}" {{ page.target }}>
						{{ page.label }}
						{% if page.child_items %}
							<ul class="dropdown-menu">
							{% for child in page.child_items %}
								<li data-label="{{ child.label }}">
									<a href="{{ child.url }}" {{ child.target }}>
							{% endfor %}
							</ul>
						{% endif %}
						</a></li>
					{% endif %}
				{% endfor %}
			</ul>
			<img src="images/lib/ui/spinner.gif" id="spinner"/>
			<ul class="nav pull-right">
				<li id="login-topbar-item"><a href="login-page.html">Login</a></li>
			</ul>
		</div>
		</div>
		</div>""").render(top_bar_items = top_bar_items, 
			brand=website_settings.brand_html or webnotes.utils.get_defaults('company') or 'ERPNext')
			
def get_footer(page_name):
	"""get page footer"""
	
	from webnotes.model.doc import Document
	from jinja2 import Template

	website_settings = Document('Website Settings', 'Website Settings')

	website_settings.footer_items = webnotes.conn.sql("""select * from `tabTop Bar Item`
		where parent='Website Settings' and parentfield='footer_items'
		order by idx asc""", as_dict=1)

	return Template("""<div class="web-footer">
		<div class="web-footer-menu"><ul>
		{% for item in footer_items %}
			<li><a href="{{ item.url }}" {{ item.target }}
				data-label="{{ item.label }}">{{ item.label }}</a></li>
		{% endfor %}
		</ul></div>
		<div class="web-footer-copyright">&copy; {{ copyright }}
		</div>""").render(website_settings.fields)
