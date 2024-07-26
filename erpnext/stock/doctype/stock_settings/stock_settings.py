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
<<<<<<< HEAD
=======
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action_if_quality_inspection_is_not_submitted: DF.Literal["Stop", "Warn"]
		action_if_quality_inspection_is_rejected: DF.Literal["Stop", "Warn"]
		allow_from_dn: DF.Check
		allow_from_pr: DF.Check
		allow_internal_transfer_at_arms_length_price: DF.Check
		allow_negative_stock: DF.Check
		allow_partial_reservation: DF.Check
		allow_to_edit_stock_uom_qty_for_purchase: DF.Check
		allow_to_edit_stock_uom_qty_for_sales: DF.Check
		auto_create_serial_and_batch_bundle_for_outward: DF.Check
		auto_indent: DF.Check
		auto_insert_price_list_rate_if_missing: DF.Check
		auto_reserve_serial_and_batch: DF.Check
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
		show_barcode_field: DF.Check
		stock_auth_role: DF.Link | None
		stock_frozen_upto: DF.Date | None
		stock_frozen_upto_days: DF.Int
		stock_uom: DF.Link | None
		update_existing_price_list_rate: DF.Check
		use_naming_series: DF.Check
		use_serial_batch_fields: DF.Check
		valuation_method: DF.Literal["FIFO", "Moving Average", "LIFO"]
	# end: auto-generated types

>>>>>>> 723ac0ffc4 (fix: Update Rate as per Valuation Rate for Internal Transfers only if Setting is Enabled (#42050))
	def validate(self):
		for key in [
			"item_naming_by",
			"item_group",
			"stock_uom",
			"allow_negative_stock",
			"default_warehouse",
			"set_qty_in_transactions_based_on_serial_no_input",
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

		stock_frozen_limit = 356
		submitted_stock_frozen = self.stock_frozen_upto_days or 0
		if submitted_stock_frozen > stock_frozen_limit:
			self.stock_frozen_upto_days = stock_frozen_limit
			frappe.msgprint(
				_("`Freeze Stocks Older Than` should be smaller than %d days.") % stock_frozen_limit
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
		db_valuation_method = frappe.db.get_single_value("Stock Settings", "valuation_method")

		if db_valuation_method and db_valuation_method != self.valuation_method:
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
				now=frappe.flags.in_test,
				enqueue_after_commit=True,
			)

	def validate_pending_reposts(self):
		if self.stock_frozen_upto:
			check_pending_reposting(self.stock_frozen_upto)

	def on_update(self):
		self.toggle_warehouse_field_for_inter_warehouse_transfer()

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
