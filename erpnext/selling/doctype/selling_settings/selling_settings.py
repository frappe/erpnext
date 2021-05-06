# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe.utils import cint
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils.nestedset import get_root_of

from frappe.model.document import Document

class SellingSettings(Document):
	def on_update(self):
		self.toggle_hide_tax_id()

	def validate(self):
		for key in ["cust_master_name", "campaign_naming_by", "customer_group", "territory",
			"maintain_same_sales_rate", "editable_price_list_rate", "selling_price_list"]:
				frappe.db.set_default(key, self.get(key, ""))

		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Customer", "customer_name",
			self.get("cust_master_name")=="Naming Series", hide_name_field=False)

	def toggle_hide_tax_id(self):
		self.hide_tax_id = cint(self.hide_tax_id)

		# Make property setters to hide tax_id fields
		for doctype in ("Sales Order", "Sales Invoice", "Delivery Note"):
			make_property_setter(doctype, "tax_id", "hidden", self.hide_tax_id, "Check", validate_fields_for_doctype=False)
			make_property_setter(doctype, "tax_id", "print_hide", self.hide_tax_id, "Check", validate_fields_for_doctype=False)

	def set_default_customer_group_and_territory(self):
		if not self.customer_group:
			self.customer_group = get_root_of('Customer Group')
		if not self.territory:
			self.territory = get_root_of('Territory')
