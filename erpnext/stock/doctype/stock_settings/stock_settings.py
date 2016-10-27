# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class StockSettings(Document):
	def validate(self):
		for key in ["item_naming_by", "item_group", "stock_uom", "allow_negative_stock", "default_warehouse"]:
			frappe.db.set_default(key, self.get(key, ""))

		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Item", "item_code",
			self.get("item_naming_by")=="Naming Series", hide_name_field=True)

		stock_frozen_limit = 356
		submitted_stock_frozen = self.stock_frozen_upto_days
		if submitted_stock_frozen > stock_frozen_limit:
			self.stock_frozen_upto_days = stock_frozen_limit
			frappe.msgprint (_("`Freeze Stocks Older Than` should be smaller than %d days.") %stock_frozen_limit)

		# show/hide barcode field
		frappe.make_property_setter({'fieldname': 'barcode', 'property': 'hidden',
			'value': 0 if self.show_barcode_field else 1})
