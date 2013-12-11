# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def validate(self):
		for key in ["item_naming_by", "item_group", "stock_uom", 
			"allow_negative_stock"]:
			webnotes.conn.set_default(key, self.doc.fields.get(key, ""))
			
		from setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Item", "item_code", 
			self.doc.get("item_naming_by")=="Naming Series", hide_name_field=True)
			
