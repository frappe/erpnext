# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document

class BuyingSettings(Document):
	def validate(self):
		for key in ["supplier_type", "supp_master_name", "maintain_same_rate", "buying_price_list"]:
			frappe.db.set_default(key, self.get(key, ""))

		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Supplier", "supplier_name",
			self.get("supp_master_name")=="Naming Series", hide_name_field=False)
		self.process_item_submit()

	def process_item_submit(self):
		if self.allow_item_qty_submit == 'Yes' or self.allow_item_price_submit == 'Yes':
			frappe.db.sql(""" update tabDocField set allow_on_submit=1 where (fieldtype in ('Currency','Float','Percent') or
				fieldname in ('items','base_in_words','in_words','status')) and
				parent = "Purchase Order" """)
			frappe.db.sql("""update tabDocField set allow_on_submit=1 where fieldtype in ('Currency','Float','Percent') and			
				parent = 'Purchase Order Item' """)
			frappe.db.sql(""" update tabDocField set allow_on_submit=1 where fieldtype in ('Currency','Float','Percent') and
				parent = 'Purchase Taxes and Charges' """)
			if self.allow_item_price_submit == 'No':
				frappe.db.sql("""update tabDocField set allow_on_submit=0 where fieldname = 'rate' and
				parent = 'Purchase Order Item'""")
			if self.allow_item_qty_submit == 'No':
				frappe.db.sql(""" update tabDocField set allow_on_submit=0 where fieldname = 'qty' and
					parent = 'Purchase Order Item' """)
		if self.allow_item_qty_submit == 'No' and self.allow_item_price_submit == 'No':
			frappe.db.sql(""" update tabDocField set allow_on_submit=0 where (fieldtype in ('Currency','Float','Percent') or
				fieldname in ('items','base_in_words','in_words','status')) and	parent = 'Purchase Order' """)
			frappe.db.sql("""update tabDocField set allow_on_submit=0 where fieldtype in ('Currency','Float','Percent') and
				parent = 'Purchase Order Item' """)

