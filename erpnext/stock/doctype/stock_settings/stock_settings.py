# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.html_utils import clean_html

from erpnext.stock.utils import check_pending_reposting


class StockSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action_if_quality_inspection_is_not_submitted: DF.Literal["Stop", "Warn"]
		action_if_quality_inspection_is_rejected: DF.Literal["Stop", "Warn"]
		allow_existing_serial_no: DF.Check
		allow_from_dn: DF.Check
		allow_from_pr: DF.Check
		allow_internal_transfer_at_arms_length_price: DF.Check
		allow_negative_stock: DF.Check
		allow_partial_reservation: DF.Check
		allow_to_edit_stock_uom_qty_for_purchase: DF.Check
		allow_to_edit_stock_uom_qty_for_sales: DF.Check
		allow_to_make_quality_inspection_after_purchase_or_delivery: DF.Check
		allow_uom_with_conversion_rate_defined_in_item: DF.Check
		auto_create_serial_and_batch_bundle_for_outward: DF.Check
		auto_indent: DF.Check
		auto_insert_price_list_rate_if_missing: DF.Check
		auto_reserve_serial_and_batch: DF.Check
		auto_reserve_stock: DF.Check
		auto_reserve_stock_for_sales_order_on_purchase: DF.Check
		clean_description_html: DF.Check
		default_warehouse: DF.Link | None
		disable_serial_no_and_batch_selector: DF.Check
		do_not_update_serial_batch_on_creation_of_auto_bundle: DF.Check
		do_not_use_batchwise_valuation: DF.Check
		enable_stock_reservation: DF.Check
		item_group: DF.Link | None
		item_naming_by: DF.Literal["Item Code", "Naming Series"]
		mr_qty_allowance: DF.Float
		naming_series_prefix: DF.Data | None
		over_delivery_receipt_allowance: DF.Float
		over_picking_allowance: DF.Percent
		pick_serial_and_batch_based_on: DF.Literal["FIFO", "LIFO", "Expiry"]
		reorder_email_notify: DF.Check
		role_allowed_to_create_edit_back_dated_transactions: DF.Link | None
		role_allowed_to_over_deliver_receive: DF.Link | None
		sample_retention_warehouse: DF.Link | None
		set_serial_and_batch_bundle_naming_based_on_naming_series: DF.Check
		show_barcode_field: DF.Check
		stock_auth_role: DF.Link | None
		stock_frozen_upto: DF.Date | None
		stock_frozen_upto_days: DF.Int
		stock_uom: DF.Link | None
		update_existing_price_list_rate: DF.Check
		update_price_list_based_on: DF.Literal["Rate", "Price List Rate"]
		use_naming_series: DF.Check
		use_serial_batch_fields: DF.Check
		validate_material_transfer_warehouses: DF.Check
		valuation_method: DF.Literal["FIFO", "Moving Average", "LIFO"]
	# end: auto-generated types

	def validate(self):
		for key in [
			"item_naming_by",
			"item_group",
			"stock_uom",
			"allow_negative_stock",
			"default_warehouse",
			"set_qty_in_transactions_based_on_serial_no_input",
			"use_serial_batch_fields",
			"set_serial_and_batch_bundle_naming_based_on_naming_series",
		]:
			frappe.db.set_default(key, self.get(key, ""))

		from erpnext.utilities.naming import set_by_naming_series

		set_by_naming_series(
			"Item",
			"item_code",
			self.get("item_naming_by") == "Naming Series",
			hide_name_field=True,
			make_mandatory=0,
		)

		# show/hide barcode field
		for name in ["barcode", "barcodes", "scan_barcode"]:
			frappe.make_property_setter(
				{"fieldname": name, "property": "hidden", "value": 0 if self.show_barcode_field else 1},
				validate_fields_for_doctype=False,
			)

		self.validate_warehouses()
		self.cant_change_valuation_method()
		self.validate_clean_description_html()
		self.validate_pending_reposts()
		self.validate_stock_reservation()
		self.validate_auto_insert_price_list_rate_if_missing()
		self.change_precision_for_for_sales()
		self.change_precision_for_purchase()

	def validate_warehouses(self):
		warehouse_fields = ["default_warehouse", "sample_retention_warehouse"]
		for field in warehouse_fields:
			if frappe.db.get_value("Warehouse", self.get(field), "is_group"):
				frappe.throw(
					_(
						"Group Warehouses cannot be used in transactions. Please change the value of {0}"
					).format(frappe.bold(self.meta.get_field(field).label)),
					title=_("Incorrect Warehouse"),
				)

	def cant_change_valuation_method(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		previous_valuation_method = doc_before_save.get("valuation_method")

		if previous_valuation_method and previous_valuation_method != self.valuation_method:
			# check if there are any stock ledger entries against items
			# which does not have it's own valuation method
			sle = frappe.db.sql(
				"""select name from `tabStock Ledger Entry` sle
				where exists(select name from tabItem
					where name=sle.item_code and (valuation_method is null or valuation_method='')) limit 1
			"""
			)

			if sle:
				frappe.throw(
					_(
						"Can't change the valuation method, as there are transactions against some items which do not have its own valuation method"
					)
				)

	def validate_clean_description_html(self):
		if int(self.clean_description_html or 0) and not int(self.db_get("clean_description_html") or 0):
			# changed to text
			frappe.enqueue(
				"erpnext.stock.doctype.stock_settings.stock_settings.clean_all_descriptions",
				now=frappe.in_test,
				enqueue_after_commit=True,
			)

	def validate_pending_reposts(self):
		if self.stock_frozen_upto:
			check_pending_reposting(self.stock_frozen_upto)

	def validate_stock_reservation(self):
		"""Raises an exception if the user tries to enable/disable `Stock Reservation` with `Negative Stock` or `Open Stock Reservation Entries`."""

		if not self.enable_stock_reservation and self.auto_reserve_stock:
			self.auto_reserve_stock = 0

		# Skip validation for tests
		if frappe.in_test:
			return

		# Change in value of `Allow Negative Stock`
		if self.has_value_changed("allow_negative_stock"):
			# Disable -> Enable: Don't allow if `Stock Reservation` is enabled
			if self.allow_negative_stock and self.enable_stock_reservation:
				frappe.throw(
					_("As {0} is enabled, you can not enable {1}.").format(
						frappe.bold(_("Stock Reservation")), frappe.bold(_("Allow Negative Stock"))
					)
				)

		# Change in value of `Enable Stock Reservation`
		if self.has_value_changed("enable_stock_reservation"):
			# Disable -> Enable
			if self.enable_stock_reservation:
				# Don't allow if `Allow Negative Stock` is enabled
				if self.allow_negative_stock:
					frappe.throw(
						_("As {0} is enabled, you can not enable {1}.").format(
							frappe.bold(_("Allow Negative Stock")), frappe.bold(_("Stock Reservation"))
						)
					)

			# Enable -> Disable
			else:
				# Don't allow if there are open Stock Reservation Entries
				has_reserved_stock = frappe.db.exists(
					"Stock Reservation Entry", {"docstatus": 1, "status": ["!=", "Delivered"]}
				)

				if has_reserved_stock:
					frappe.throw(
						_("As there are reserved stock, you cannot disable {0}.").format(
							frappe.bold(_("Stock Reservation"))
						)
					)

	def validate_auto_insert_price_list_rate_if_missing(self):
		if (
			self.auto_insert_price_list_rate_if_missing
			and self.has_value_changed("auto_insert_price_list_rate_if_missing")
			and frappe.get_single_value("Selling Settings", "fallback_to_default_price_list")
		):
			selling_meta = frappe.get_meta("Selling Settings")
			frappe.msgprint(
				_(
					"You have enabled {0} and {1} in {2}. This can lead to prices from the default price list being inserted in the transaction price list."
				).format(
					"<i>{}</i>".format(_(self.meta.get_label("auto_insert_price_list_rate_if_missing"))),
					"<i>{}</i>".format(_(selling_meta.get_label("fallback_to_default_price_list"))),
					frappe.bold(_("Selling Settings")),
				)
			)

	def on_update(self):
		self.toggle_warehouse_field_for_inter_warehouse_transfer()

	def change_precision_for_for_sales(self):
		doc_before_save = self.get_doc_before_save()
		if doc_before_save and (
			doc_before_save.allow_to_edit_stock_uom_qty_for_sales
			== self.allow_to_edit_stock_uom_qty_for_sales
		):
			return

		if self.allow_to_edit_stock_uom_qty_for_sales:
			doctypes = ["Sales Order Item", "Sales Invoice Item", "Delivery Note Item", "Quotation Item"]
			self.make_property_setter_for_precision(doctypes)

	def change_precision_for_purchase(self):
		doc_before_save = self.get_doc_before_save()
		if doc_before_save and (
			doc_before_save.allow_to_edit_stock_uom_qty_for_purchase
			== self.allow_to_edit_stock_uom_qty_for_purchase
		):
			return

		if self.allow_to_edit_stock_uom_qty_for_purchase:
			doctypes = [
				"Purchase Order Item",
				"Purchase Receipt Item",
				"Purchase Invoice Item",
				"Request for Quotation Item",
				"Supplier Quotation Item",
				"Material Request Item",
			]
			self.make_property_setter_for_precision(doctypes)

	@staticmethod
	def make_property_setter_for_precision(doctypes):
		for doctype in doctypes:
			if property_name := frappe.db.exists(
				"Property Setter",
				{"doc_type": doctype, "field_name": "conversion_factor", "property": "precision"},
			):
				frappe.db.set_value("Property Setter", property_name, "value", 9)
				continue

			make_property_setter(
				doctype,
				"conversion_factor",
				"precision",
				9,
				"Float",
				validate_fields_for_doctype=False,
			)

	def toggle_warehouse_field_for_inter_warehouse_transfer(self):
		make_property_setter(
			"Sales Invoice Item",
			"target_warehouse",
			"hidden",
			1 - cint(self.allow_from_dn),
			"Check",
			validate_fields_for_doctype=False,
		)
		make_property_setter(
			"Delivery Note Item",
			"target_warehouse",
			"hidden",
			1 - cint(self.allow_from_dn),
			"Check",
			validate_fields_for_doctype=False,
		)
		make_property_setter(
			"Purchase Invoice Item",
			"from_warehouse",
			"hidden",
			1 - cint(self.allow_from_pr),
			"Check",
			validate_fields_for_doctype=False,
		)
		make_property_setter(
			"Purchase Receipt Item",
			"from_warehouse",
			"hidden",
			1 - cint(self.allow_from_pr),
			"Check",
			validate_fields_for_doctype=False,
		)


def clean_all_descriptions():
	for item in frappe.get_all("Item", ["name", "description"]):
		if item.description:
			clean_description = clean_html(item.description)
		if item.description != clean_description:
			frappe.db.set_value("Item", item.name, "description", clean_description)


@frappe.whitelist()
def get_enable_stock_uom_editing():
	return frappe.get_cached_value(
		"Stock Settings",
		None,
		["allow_to_edit_stock_uom_qty_for_sales", "allow_to_edit_stock_uom_qty_for_purchase"],
		as_dict=1,
	)
