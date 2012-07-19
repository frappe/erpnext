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

# website patch

from __future__ import unicode_literals
import webnotes
from webnotes.model.doc import Document

def execute():	
	add_website_manager()
	from webnotes.modules import reload_doc
	from webnotes.model import delete_doc

	# cleanup page
	delete_doc("DocType", "Page")
	reload_doc("core", "doctype", "page")

	reload_doc('setup', 'doctype', 'item_group')
	delete_doc('Website', 'Module Def', 'Website')
	reload_doc('website', 'Module Def', 'Website')
	reload_doc('website', 'Role', 'Website Manager')
	reload_doc('website', 'Role', 'Blogger')

	webnotes.conn.sql("""delete from `tabModule Def Role` where parent='Website'""")
	d = Document('Module Def Role')
	d.parent = 'Website'
	d.role = 'Website Manager'
	d.save()
	
	reload_doc('website', 'doctype', 'about_us_settings')
	reload_doc('website', 'doctype', 'about_us_team')
	reload_doc('website', 'doctype', 'blog')
	reload_doc('website', 'doctype', 'contact_us_settings')
	reload_doc('website', 'doctype', 'product')
	reload_doc('website', 'doctype', 'product_group')
	reload_doc('website', 'doctype', 'products_settings')
	reload_doc('website', 'doctype', 'related_page')
	reload_doc('website', 'doctype', 'style_settings')
	reload_doc('website', 'doctype', 'top_bar_item')
	reload_doc('website', 'doctype', 'web_page')
	reload_doc('website', 'doctype', 'website_settings')

	reload_doc('website', 'page', 'about')
	reload_doc('website', 'page', 'blog')
	reload_doc('website', 'page', 'contact')
	reload_doc('website', 'page', 'products')
	reload_doc('website', 'page', 'unsubscribe')
		
	create_home_page()
	add_website_manager()

def create_home_page():
	"""create a dummy home page"""
	from webnotes.model.code import get_obj
	if not webnotes.conn.sql("""select name from `tabWeb Page` where name='home'"""):
		d = Document('Web Page')
		d.title = 'Home'
		d.head_section = "<h1>Your Headline</h1>"
		d.main_section = "<p>Some introduction about your company</p>"
		d.side_section = "<p>Links to other pages</p>"
		d.save()
		obj = get_obj(doc = d)
		obj.validate()
		obj.doc.save()

def add_website_manager():
	"""add website manager to system manager"""
	for i in webnotes.conn.sql("""select distinct parent from tabUserRole 
		where role='System Manager'"""):
		if not webnotes.conn.sql("""select parent from tabUserRole 
			where role='Website Manager' and parent=%s""", i[0]):
			d = Document('UserRole')
			d.parent = i[0]
			d.role = 'Website Manager'
			d.save(1)
