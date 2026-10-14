# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import flt


class BuyingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_multiple_items: DF.Check
		allow_negative_rates_for_items: DF.Check
		allow_zero_qty_in_purchase_order: DF.Check
		allow_zero_qty_in_request_for_quotation: DF.Check
		allow_zero_qty_in_supplier_quotation: DF.Check
		auto_create_purchase_receipt: DF.Check
		auto_create_subcontracting_order: DF.Check
		backflush_raw_materials_of_subcontract_based_on: DF.Literal[
			"BOM", "Material Transferred for Subcontract"
		]
		bill_for_rejected_quantity_in_purchase_invoice: DF.Check
		blanket_order_allowance: DF.Float
		buying_price_list: DF.Link | None
		disable_last_purchase_rate: DF.Check
		fixed_email: DF.Link | None
		maintain_same_rate: DF.Check
		maintain_same_rate_action: DF.Literal["Stop", "Warn"]
		over_order_allowance: DF.Float
		over_transfer_allowance: DF.Float
		po_required: DF.Literal["No", "Yes"]
		pr_required: DF.Literal["No", "Yes"]
		project_update_frequency: DF.Literal["Each Transaction", "Manual"]
		role_to_override_stop_action: DF.Link | None
		set_landed_cost_based_on_purchase_invoice_rate: DF.Check
		set_valuation_rate_for_rejected_materials: DF.Check
		show_pay_button: DF.Check
		supp_master_name: DF.Literal["Supplier Name", "Naming Series", "Auto Name"]
		supplier_group: DF.Link | None
		use_transaction_date_exchange_rate: DF.Check
		validate_consumed_qty: DF.Check
	# end: auto-generated types

	def validate(self):
		for key in ["supplier_group", "supp_master_name", "maintain_same_rate", "buying_price_list"]:
			frappe.db.set_default(key, self.get(key, ""))

		self.update_supplier_naming_settings()

		if not self.bill_for_rejected_quantity_in_purchase_invoice:
			self.set_valuation_rate_for_rejected_materials = 0

	def update_supplier_naming_settings(self):
		if not self.has_value_changed("supp_master_name"):
			return

		from erpnext.utilities.naming import set_by_naming_series

		set_by_naming_series(
			"Supplier",
			"supplier_name",
			self.get("supp_master_name") == "Naming Series",
			hide_name_field=False,
		)

	def before_save(self):
		self.check_maintain_same_rate()

	def check_maintain_same_rate(self):
		if self.maintain_same_rate:
			self.set_landed_cost_based_on_purchase_invoice_rate = 0


def is_rejected_material_valued(voucher_type: str, voucher_detail_no: str | None = None) -> bool:
	"""Rejected material carries stock value only when something has paid for it.

	Material of an internal transfer always has: its value was credited out of the in-transit
	warehouse. A Purchase Receipt books rejected material against Stock Received But Not Billed, so
	the supplier still owes an invoice for it, and Buying Settings decides. A stock updating Purchase
	Invoice pays for it only when it bills the received qty, which is what the settings ask for.
	"""
	if is_material_from_in_transit_warehouse(voucher_type, voucher_detail_no):
		return True

	if not frappe.db.get_single_value("Buying Settings", "set_valuation_rate_for_rejected_materials"):
		return False

	return voucher_type != "Purchase Invoice" or bool(
		frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice")
	)


def is_material_from_in_transit_warehouse(voucher_type: str, voucher_detail_no: str | None) -> bool:
	if voucher_type not in ("Purchase Receipt", "Purchase Invoice") or not voucher_detail_no:
		return False

	return bool(frappe.get_cached_value(voucher_type + " Item", voucher_detail_no, "from_warehouse"))


def bills_rejected_quantity(doc) -> bool:
	"""An invoice that moves stock itself has no receipt to bill the rejected material for it, so it
	bills the received qty when the settings ask for the material to be valued.

	An internal transfer bills nothing of the sort: its material is paid for by the warehouse it came
	out of.
	"""
	if doc.doctype != "Purchase Invoice" or not doc.get("update_stock"):
		return False

	if doc.get("is_internal_supplier") and doc.get("represents_company") == doc.get("company"):
		return False

	return is_rejected_material_valued(doc.doctype)


def get_billed_qty(doc, item) -> float:
	if not flt(item.get("rejected_qty")) or not bills_rejected_quantity(doc):
		return flt(item.qty)

	return flt(item.qty) + flt(item.rejected_qty)
