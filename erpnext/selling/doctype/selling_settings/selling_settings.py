# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document

class SellingSettings(Document):
	def validate(self):
		self.validate_automation()
		self.set_naming_series()
		self.set_defaults()

	def validate_automation(self):
		if self.select_price_list_based_on_address:
			self.default_price_list = None

		if not self.selection_based_on:
			self.selection_based_on = "Billing Address"

		self.validate_value("selection_based_on", "in", ("Billing Address", "Shipping Address"))

	def set_naming_series(self):
		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Customer", "customer_name",
			self.get("cust_master_name")=="Naming Series", hide_name_field=False)

	def set_defaults(self):
		for key in ["cust_master_name", "campaign_naming_by", "customer_group", "territory",
			"maintain_same_sales_rate", "editable_price_list_rate", "selling_price_list"]:
				frappe.db.set_default(key, self.get(key, ""))
