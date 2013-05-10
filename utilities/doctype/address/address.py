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
from webnotes.utils import cstr

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		if not self.doc.address_title:
			self.doc.address_title = self.doc.customer or self.doc.supplier or self.doc.sales_partner
			
		if self.doc.address_title:
			self.doc.name = cstr(self.doc.address_title).strip() + "-" + cstr(self.doc.address_type).strip()
			
		else:
			webnotes.msgprint("""Address Title is mandatory.""", raise_exception=True)
		

	def validate(self):
		self.validate_primary_address()
		self.validate_shipping_address()
	
	def validate_primary_address(self):
		"""Validate that there can only be one primary address for particular customer, supplier"""
		sql = webnotes.conn.sql
		if self.doc.is_primary_address == 1:
			if self.doc.customer: 
				sql("update tabAddress set is_primary_address=0 where customer = '%s'" % (self.doc.customer))
			elif self.doc.supplier:
				sql("update tabAddress set is_primary_address=0 where supplier = '%s'" % (self.doc.supplier))
			elif self.doc.sales_partner:
				sql("update tabAddress set is_primary_address=0 where sales_partner = '%s'" % (self.doc.sales_partner))
		elif not self.doc.is_shipping_address:
			if self.doc.customer: 
				if not sql("select name from tabAddress where is_primary_address=1 and customer = '%s'" % (self.doc.customer)):
					self.doc.is_primary_address = 1
			elif self.doc.supplier:
				if not sql("select name from tabAddress where is_primary_address=1 and supplier = '%s'" % (self.doc.supplier)):
					self.doc.is_primary_address = 1
			elif self.doc.sales_partner:
				if not sql("select name from tabAddress where is_primary_address=1 and sales_partner = '%s'" % (self.doc.sales_partner)):
					self.doc.is_primary_address = 1

				
	def validate_shipping_address(self):
		"""Validate that there can only be one shipping address for particular customer, supplier"""
		sql = webnotes.conn.sql
		if self.doc.is_shipping_address == 1:
			if self.doc.customer: 
				sql("update tabAddress set is_shipping_address=0 where customer = '%s'" % (self.doc.customer))
			elif self.doc.supplier:
				sql("update tabAddress set is_shipping_address=0 where supplier = '%s'" % (self.doc.supplier))			
			elif self.doc.sales_partner:
				sql("update tabAddress set is_shipping_address=0 where sales_partner = '%s'" % (self.doc.sales_partner))			
