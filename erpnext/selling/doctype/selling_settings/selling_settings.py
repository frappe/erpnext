# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.model.document import Document
from frappe.utils import cint


class SellingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_against_multiple_purchase_orders: DF.Check
		allow_multiple_items: DF.Check
		allow_negative_rates_for_items: DF.Check
		allow_sales_order_creation_for_expired_quotation: DF.Check
		blanket_order_allowance: DF.Float
		cust_master_name: DF.Literal["Customer Name", "Naming Series", "Auto Name"]
		customer_group: DF.Link | None
		dn_required: DF.Literal["No", "Yes"]
		dont_reserve_sales_order_qty_on_sales_return: DF.Check
		editable_bundle_item_rates: DF.Check
		editable_price_list_rate: DF.Check
		enable_discount_accounting: DF.Check
		hide_tax_id: DF.Check
		maintain_same_rate_action: DF.Literal["Stop", "Warn"]
		maintain_same_sales_rate: DF.Check
		role_to_override_stop_action: DF.Link | None
		sales_update_frequency: DF.Literal["Monthly", "Each Transaction", "Daily"]
		selling_price_list: DF.Link | None
		so_required: DF.Literal["No", "Yes"]
		territory: DF.Link | None
		validate_selling_price: DF.Check
	# end: auto-generated types

	def on_update(self):
		self.toggle_hide_tax_id()
		self.toggle_editable_rate_for_bundle_items()
		self.toggle_discount_accounting_fields()

	def validate(self):
		for key in [
			"cust_master_name",
			"customer_group",
			"territory",
			"maintain_same_sales_rate",
			"editable_price_list_rate",
			"selling_price_list",
		]:
			frappe.db.set_default(key, self.get(key, ""))

		from erpnext.utilities.naming import set_by_naming_series

		set_by_naming_series(
			"Customer",
			"customer_name",
			self.get("cust_master_name") == "Naming Series",
			hide_name_field=False,
		)

	def toggle_hide_tax_id(self):
		self.hide_tax_id = cint(self.hide_tax_id)

		# Make property setters to hide tax_id fields
		for doctype in ("Sales Order", "Sales Invoice", "Delivery Note"):
			make_property_setter(
				doctype, "tax_id", "hidden", self.hide_tax_id, "Check", validate_fields_for_doctype=False
			)
			make_property_setter(
				doctype, "tax_id", "print_hide", self.hide_tax_id, "Check", validate_fields_for_doctype=False
			)

	def toggle_editable_rate_for_bundle_items(self):
		editable_bundle_item_rates = cint(self.editable_bundle_item_rates)

		make_property_setter(
			"Packed Item",
			"rate",
			"read_only",
			not (editable_bundle_item_rates),
			"Check",
			validate_fields_for_doctype=False,
		)

	def toggle_discount_accounting_fields(self):
		enable_discount_accounting = cint(self.enable_discount_accounting)

		make_property_setter(
			"Sales Invoice Item",
			"discount_account",
			"hidden",
			not (enable_discount_accounting),
			"Check",
			validate_fields_for_doctype=False,
		)
		if enable_discount_accounting:
			make_property_setter(
				"Sales Invoice Item",
				"discount_account",
				"mandatory_depends_on",
				"eval: doc.discount_amount",
				"Code",
				validate_fields_for_doctype=False,
			)
		else:
			make_property_setter(
				"Sales Invoice Item",
				"discount_account",
				"mandatory_depends_on",
				"",
				"Code",
				validate_fields_for_doctype=False,
			)

		make_property_setter(
			"Sales Invoice",
			"additional_discount_account",
			"hidden",
			not (enable_discount_accounting),
			"Check",
			validate_fields_for_doctype=False,
		)
		if enable_discount_accounting:
			make_property_setter(
				"Sales Invoice",
				"additional_discount_account",
				"mandatory_depends_on",
				"eval: doc.discount_amount",
				"Code",
				validate_fields_for_doctype=False,
			)
		else:
			make_property_setter(
				"Sales Invoice",
				"additional_discount_account",
				"mandatory_depends_on",
				"",
				"Code",
				validate_fields_for_doctype=False,
			)
