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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cint, cstr
from webnotes import msgprint, errprint
import webnotes.model.doctype

sql = webnotes.conn.sql
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	#-----------------------------------------------------------------------------------------------------------------------------------
	def get_transactions(self):
		return "\n".join([''] + [i[0] for i in sql("SELECT `tabDocField`.`parent` FROM `tabDocField`, `tabDocType` WHERE `tabDocField`.`fieldname` = 'naming_series' and `tabDocType`.name=`tabDocField`.parent order by `tabDocField`.parent")])
	
	#-----------------------------------------------------------------------------------------------------------------------------------
	def get_options_for(self, doctype):
		sr = webnotes.model.doctype.get_property(doctype, 'naming_series')
		if sr:
			return sr.split("\n")
		else:
			return []
	
	def scrub_options_list(self, ol):
		options = filter(lambda x: x, [cstr(n.upper()).strip() for n in ol])
		return options
	
	#-----------------------------------------------------------------------------------------------------------------------------------
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
					'select_doctype': doctype
				})
				ps.save(1)

		self.doc.set_options = "\n".join(options)
	
	#-----------------------------------------------------------------------------------------------------------------------------------
	def update_series(self):
			self.check_duplicate()
			self.set_series_for(self.doc.select_doc_for_series, self.doc.set_options.split("\n"))
			msgprint('Series Updated')			
			
	#-----------------------------------------------------------------------------------------------------------------------------------
	def check_duplicate(self):
		from core.doctype.doctype.doctype import DocType
		dt = DocType()
	
		parent = sql("select parent from `tabDocField` where fieldname='naming_series' and parent != %s", self.doc.select_doc_for_series)
		sr = ([p[0], webnotes.model.doctype.get_property(p[0], 'naming_series')] for p in parent)
		options = self.scrub_options_list(self.doc.set_options.split("\n"))
		for series in options:
			dt.validate_series(series, self.doc.select_doc_for_series)
			for i in sr:
				if i[0]:
					if series in i[0].split("\n"):
						msgprint("Oops! Series name %s is already in use in %s. Please select a new one" % (series, i[1]), raise_exception=1)
			
	#-----------------------------------------------------------------------------------------------------------------------------------
	def validate_series_name(self, n):
		import re
		if not re.match('[a-zA-Z0-9]+(([-/][a-zA-Z0-9])?[-/][a-zA-Z0-9]*)*',n):
			msgprint('Special Characters except "-" and "/" not allowed in naming series')
			raise Exception
		
	#-----------------------------------------------------------------------------------------------------------------------------------
	def get_options(self, arg=''):
		so = sql("select options from `tabDocField` where parent=%s and fieldname='naming_series'", self.doc.select_doc_for_series)
		if so:
			return so[0][0] or ''


	#-----------------------------------------------------------------------------------------------------------------------------------
	def update_series_start(self):
		if self.doc.prefix:
			ser_det = sql("select name from `tabSeries` where name = %s", self.doc.prefix)
			if ser_det:
				sql("update `tabSeries` set current = '%s' where name = '%s'" % (self.doc.starts_from-1,self.doc.prefix))
			else:
				sql("insert into tabSeries (name, current) values (%s,%s)",(cstr(self.doc.prefix),cint(self.doc.starts_from)-1))
			msgprint("Series Updated Successfully")
		else:
			msgprint("Please select prefix first")
