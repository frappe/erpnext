# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		for key in ["supplier_type", "supp_master_name", "maintain_same_rate", "buying_price_list"]:
			frappe.conn.set_default(key, self.doc.fields.get(key, ""))

		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Supplier", "supplier_name", 
			self.doc.get("supp_master_name")=="Naming Series", hide_name_field=False)
