# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
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
