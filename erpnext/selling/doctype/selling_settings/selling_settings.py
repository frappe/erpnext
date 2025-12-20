# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
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
		allow_delivery_of_overproduced_qty: DF.Check
		allow_multiple_items: DF.Check
		allow_negative_rates_for_items: DF.Check
		allow_sales_order_creation_for_expired_quotation: DF.Check
		allow_zero_qty_in_quotation: DF.Check
		allow_zero_qty_in_sales_order: DF.Check
		blanket_order_allowance: DF.Float
		cust_master_name: DF.Literal["Customer Name", "Naming Series", "Auto Name"]
		customer_group: DF.Link | None
		deliver_scrap_items: DF.Check
		dn_required: DF.Literal["No", "Yes"]
		dont_reserve_sales_order_qty_on_sales_return: DF.Check
		editable_bundle_item_rates: DF.Check
		editable_price_list_rate: DF.Check
		enable_cutoff_date_on_bulk_delivery_note_creation: DF.Check
		enable_discount_accounting: DF.Check
		fallback_to_default_price_list: DF.Check
		hide_tax_id: DF.Check
		maintain_same_rate_action: DF.Literal["Stop", "Warn"]
		maintain_same_sales_rate: DF.Check
		role_to_override_stop_action: DF.Link | None
		sales_update_frequency: DF.Literal["Monthly", "Each Transaction", "Daily"]
		selling_price_list: DF.Link | None
		so_required: DF.Literal["No", "Yes"]
		territory: DF.Link | None
		use_legacy_js_reactivity: DF.Check
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

		self.validate_fallback_to_default_price_list()

	def validate_fallback_to_default_price_list(self):
		if (
			self.fallback_to_default_price_list
			and self.has_value_changed("fallback_to_default_price_list")
			and frappe.get_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing")
		):
			stock_meta = frappe.get_meta("Stock Settings")
			frappe.msgprint(
				_(
					"You have enabled {0} and {1} in {2}. This can lead to prices from the default price list being inserted into the transaction price list."
				).format(
					"<i>{}</i>".format(_(self.meta.get_label("fallback_to_default_price_list"))),
					"<i>{}</i>".format(_(stock_meta.get_label("auto_insert_price_list_rate_if_missing"))),
					frappe.bold(_("Stock Settings")),
				)
			)

	def toggle_hide_tax_id(self):
		_hide_tax_id = cint(self.hide_tax_id)

		# Make property setters to hide tax_id fields
		for doctype in ("Sales Order", "Sales Invoice", "Delivery Note"):
			make_property_setter(
				doctype, "tax_id", "hidden", _hide_tax_id, "Check", validate_fields_for_doctype=False
			)
			make_property_setter(
				doctype, "tax_id", "print_hide", _hide_tax_id, "Check", validate_fields_for_doctype=False
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
