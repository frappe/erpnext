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

from webnotes.utils import cstr
from webnotes import msgprint
import webnotes.model.doctype

sql = webnotes.conn.sql

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def get_transactions(self, arg=None):
		return {
			"transactions": "\n".join([''] + sorted(list(set(
				webnotes.conn.sql_list("""select parent
					from `tabDocField` where fieldname='naming_series'""") 
				+ webnotes.conn.sql_list("""select dt from `tabCustom Field` 
					where fieldname='naming_series'""")
				)))),
			"prefixes": "\n".join([''] + [i[0] for i in 
				sql("""select name from tabSeries""")])
		}
	
	def scrub_options_list(self, ol):
		options = filter(lambda x: x, [cstr(n.upper()).strip() for n in ol])
		return options

	def update_series(self, arg=None):
		"""update series list"""
		self.check_duplicate()
		series_list = self.doc.set_options.split("\n")
		
		# set in doctype
		self.set_series_for(self.doc.select_doc_for_series, series_list)
		
		# create series
		map(self.insert_series, series_list)
		
		msgprint('Series Updated')
		
		return self.get_transactions()
	
	def set_series_for(self, doctype, ol):
		options = self.scrub_options_list(ol)
		
		# validate names
		for i in options: self.validate_series_name(i)
		
		if self.doc.user_must_always_select:
			options = [''] + options
			default = ''
		else:
			default = options[0]
		
		# update in property setter
		from webnotes.model.doc import Document
		prop_dict = {'options': "\n".join(options), 'default': default}
		for prop in prop_dict:
			ps_exists = webnotes.conn.sql("""SELECT name FROM `tabProperty Setter`
					WHERE doc_type = %s AND field_name = 'naming_series'
					AND property = %s""", (doctype, prop))
			if ps_exists:
				ps = Document('Property Setter', ps_exists[0][0])
				ps.value = prop_dict[prop]
				ps.save()
			else:
				ps = Document('Property Setter', fielddata = {
					'doctype_or_field': 'DocField',
					'doc_type': doctype,
					'field_name': 'naming_series',
					'property': prop,
					'value': prop_dict[prop],
					'property_type': 'Select',
				})
				ps.save(1)

		self.doc.set_options = "\n".join(options)

		webnotes.clear_cache(doctype=doctype)
			
	def check_duplicate(self):
		from core.doctype.doctype.doctype import DocType
		dt = DocType()
	
		parent = list(set(
			webnotes.conn.sql_list("""select dt.name 
				from `tabDocField` df, `tabDocType` dt 
				where dt.name = df.parent and df.fieldname='naming_series' and dt.name != %s""",
				self.doc.select_doc_for_series)
			+ webnotes.conn.sql_list("""select dt.name 
				from `tabCustom Field` df, `tabDocType` dt 
				where dt.name = df.dt and df.fieldname='naming_series' and dt.name != %s""",
				self.doc.select_doc_for_series)
			))
		sr = [[webnotes.model.doctype.get_property(p, 'options', 'naming_series'), p] 
			for p in parent]
		options = self.scrub_options_list(self.doc.set_options.split("\n"))
		for series in options:
			dt.validate_series(series, self.doc.select_doc_for_series)
			for i in sr:
				if i[0]:
					if series in i[0].split("\n"):
						msgprint("Oops! Series name %s is already in use in %s. \
							Please select a new one" % (series, i[1]), raise_exception=1)
			
	def validate_series_name(self, n):
		import re
		if not re.match("^[a-zA-Z0-9-/.#]*$", n):
			msgprint('Special Characters except "-" and "/" not allowed in naming series',
				raise_exception=True)
		
	def get_options(self, arg=''):
		sr = webnotes.model.doctype.get_property(self.doc.select_doc_for_series, 
			'options', 'naming_series')
		return sr

	def get_current(self, arg=None):
		"""get series current"""
		self.doc.current_value = webnotes.conn.sql("""select current from tabSeries where name=%s""", 
			self.doc.prefix)[0][0]

	def insert_series(self, series):
		"""insert series if missing"""
		if not webnotes.conn.exists('Series', series):
			sql("insert into tabSeries (name, current) values (%s,0)", (series))			

	def update_series_start(self):
		if self.doc.prefix:
			self.insert_series(self.doc.prefix)
			sql("update `tabSeries` set current = '%s' where name = '%s'" % (self.doc.current_value,self.doc.prefix))
			msgprint("Series Updated Successfully")
		else:
			msgprint("Please select prefix first")
