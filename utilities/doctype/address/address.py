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

from webnotes import msgprint
from webnotes.utils import cstr, cint

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		if not self.doc.address_title:
			self.doc.address_title = self.doc.customer \
				or self.doc.supplier or self.doc.sales_partner or self.doc.lead
				
		if self.doc.address_title:
			self.doc.name = cstr(self.doc.address_title).strip() + "-" + cstr(self.doc.address_type).strip()
		else:
			webnotes.msgprint("""Address Title is mandatory.""" + self.doc.customer, raise_exception=True)
		
	def validate(self):
		self.validate_primary_address()
		self.validate_shipping_address()
	
	def validate_primary_address(self):
		"""Validate that there can only be one primary address for particular customer, supplier"""
		if self.doc.is_primary_address == 1:
			self._unset_other("is_primary_address")
			
		elif self.doc.is_shipping_address != 1:
			for fieldname in ["customer", "supplier", "sales_partner", "lead"]:
				if self.doc.fields.get(fieldname):
					if not webnotes.conn.sql("""select name from `tabAddress` where is_primary_address=1
						and `%s`=%s and name!=%s""" % (fieldname, "%s", "%s"), 
						(self.doc.fields[fieldname], self.doc.name)):
							self.doc.is_primary_address = 1
					break
				
	def validate_shipping_address(self):
		"""Validate that there can only be one shipping address for particular customer, supplier"""
		if self.doc.is_shipping_address == 1:
			self._unset_other("is_shipping_address")
			
	def _unset_other(self, is_address_type):
		for fieldname in ["customer", "supplier", "sales_partner", "lead"]:
			if self.doc.fields.get(fieldname):
				webnotes.conn.sql("""update `tabAddress` set `%s`=0 where `%s`=%s and name!=%s""" %
					(is_address_type, fieldname, "%s", "%s"), (self.doc.fields[fieldname], self.doc.name))
				break
				
def get_website_args():
	def _get_fields(fieldnames):
		return [webnotes._dict(zip(["label", "fieldname", "fieldtype", "options"], 
				[df.label, df.fieldname, df.fieldtype, df.options]))
			for df in webnotes.get_doctype("Address", processed=True).get({"fieldname": ["in", fieldnames]})]
	
	bean = None
	if webnotes.form_dict.name:
		bean = webnotes.bean("Address", webnotes.form_dict.name)
	
	return {
		"doc": bean.doc if bean else None,
		"meta": webnotes._dict({
			"left_fields": _get_fields(["address_title", "address_type", "address_line1", "address_line2",
				"city", "state", "pincode", "country"]),
			"right_fields": _get_fields(["email_id", "phone", "fax", "is_primary_address",
				"is_shipping_address"])
		}),
		"cint": cint
	}
	
