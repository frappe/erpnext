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
import website.utils
import website.web_cache

class Page(object):
	def __init__(self, doctype):
		self.doctype = doctype
		
	def autoname(self):
		"""name from title"""
		self.doc.name = website.utils.page_name(self.doc.title)
		
	def validate(self):
		if self.doc.name:
			self.old_page_name = webnotes.conn.get_value(self.doctype, self.doc.name, 'page_name')

	def on_update(self):
		# page name updates with the title
		self.update_page_name()
		
		self.clear_web_cache()

		self.doc.save()
		
	def on_trash(self):
		"""delete Web Cache entry"""
		self.delete_web_cache(self.doc.page_name)
	
	def update_page_name(self):
		"""set page_name and check if it is unique"""
		self.doc.page_name = website.utils.page_name(self.doc.title)
		
		res = webnotes.conn.sql("""\
			select count(*) from `tab%s`
			where page_name=%s and name!=%s""" % (self.doctype, '%s', '%s'),
			(self.doc.page_name, self.doc.name))
		if res and res[0][0] > 0:
			webnotes.msgprint("""A %s with the same title already exists.
				Please change the title of %s and save again."""
				% (self.doctype, self.doc.name), raise_exception=1)

	def clear_web_cache(self):
		"""
			if web cache entry doesn't exist, it creates one
			if duplicate entry exists for another doctype, it raises exception
		"""
		# delete web cache entry of old name
		if hasattr(self, 'old_page_name') and self.old_page_name and \
				self.old_page_name != self.doc.page_name:
			self.delete_web_cache(self.old_page_name)
		
		website.web_cache.create_cache(self.doc.page_name, self.doc.doctype, self.doc.name)
		website.web_cache.clear_cache(self.doc.page_name, self.doc.doctype, self.doc.name)
		
	def delete_web_cache(self, page_name):
		"""delete entry of page name from Web Cache"""
		website.web_cache.delete_cache(page_name)

	def markdown_to_html(self, fields_list):
		"""convert fields from markdown to html"""
		import markdown2
		for f in fields_list:
			field_name = "%s_html" % f
			self.doc.fields[field_name] = markdown2.markdown(self.doc.fields.get(f) or '', \
				extras=["wiki-tables"])