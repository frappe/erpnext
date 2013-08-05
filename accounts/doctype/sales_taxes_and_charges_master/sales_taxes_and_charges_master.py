# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint
from webnotes.model.controller import DocListController

class DocType(DocListController):
	def get_rate(self, arg):
		from webnotes.model.code import get_obj
		return get_obj('Sales Common').get_rate(arg)
		
	def validate(self):
		if self.doc.is_default == 1:
			webnotes.conn.sql("""update `tabSales Taxes and Charges Master` set is_default = 0 
				where ifnull(is_default,0) = 1 and name != %s and company = %s""", 
				(self.doc.name, self.doc.company))
				
		# at least one territory
		self.validate_table_has_rows("valid_for_territories")
		
	def on_update(self):
		cart_settings = webnotes.get_obj("Shopping Cart Settings")
		if cint(cart_settings.doc.enabled):
			cart_settings.validate_tax_masters()