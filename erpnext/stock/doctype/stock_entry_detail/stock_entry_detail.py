# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import (
	flt,
	get_link_to_form,
	getdate,
)

from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	OpeningEntryAccountError,
)
from erpnext.stock.stock_ledger import get_previous_sle


class StockEntryDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		additional_cost: DF.Currency
		against_fg: DF.Link | None
		against_stock_entry: DF.Link | None
		allow_alternative_item: DF.Check
		allow_zero_valuation_rate: DF.Check
		amount: DF.Currency
		barcode: DF.Data | None
		basic_amount: DF.Currency
		basic_rate: DF.Currency
		batch_no: DF.Link | None
		bom_no: DF.Link | None
		bom_secondary_item: DF.Data | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		customer_provided_item_cost: DF.Currency
		description: DF.TextEditor | None
		expense_account: DF.Link | None
		has_item_scanned: DF.Check
		image: DF.Attach | None
		is_finished_item: DF.Check
		is_legacy_scrap_item: DF.Check
		item_code: DF.Link
		item_group: DF.Data | None
		item_name: DF.Data | None
		job_card_item: DF.Data | None
		landed_cost_voucher_amount: DF.Currency
		material_request: DF.Link | None
		material_request_item: DF.Link | None
		original_item: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		po_detail: DF.Data | None
		project: DF.Link | None
		putaway_rule: DF.Link | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		reference_purchase_receipt: DF.Link | None
		retain_sample: DF.Check
		s_warehouse: DF.Link | None
		sample_quantity: DF.Int
		scio_detail: DF.Data | None
		sco_rm_detail: DF.Data | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		set_basic_rate_manually: DF.Check
		ste_detail: DF.Data | None
		stock_uom: DF.Link
		subcontracted_item: DF.Link | None
		t_warehouse: DF.Link | None
		transfer_qty: DF.Float
		transferred_qty: DF.Float
		secondary_item_type: DF.Literal["", "Co-Product", "By-Product", "Scrap", "Additional Finished Good"]
		uom: DF.Link
		use_serial_batch_fields: DF.Check
		valuation_rate: DF.Currency
	# end: auto-generated types

	def validate_batch(self):
		if not self.batch_no:
			return

		disabled = frappe.db.get_value("Batch", self.batch_no, "disabled")
		if disabled:
			frappe.throw(_("Batch {0} of Item {1} is disabled.").format(self.batch_no, self.item_code))
			return

		expiry_date = frappe.db.get_value("Batch", self.batch_no, "expiry_date")
		if expiry_date and getdate(self.parent_doc.posting_date) > getdate(expiry_date):
			frappe.throw(_("Batch {0} of Item {1} has expired.").format(self.batch_no, self.item_code))

	def validate_and_update_item_details(self, item_details, company, purpose):
		if flt(self.qty) and flt(self.qty) < 0:
			frappe.throw(
				_("Row {0}: The item {1}, quantity must be positive number").format(
					self.idx, bold(self.item_code)
				)
			)

		if item_details.get("is_stock_item") != 1:
			frappe.throw(_("{0} is not a stock Item").format(self.item_code))

		reset_fields = ("stock_uom", "item_name")
		for field in reset_fields:
			self.set(field, item_details.get(field))

		update_fields = (
			"uom",
			"description",
			"expense_account",
			"cost_center",
			"conversion_factor",
			"barcode",
		)
		for field in update_fields:
			if not self.get(field):
				self.set(field, item_details.get(field))
			if field == "conversion_factor" and self.uom == item_details.get("stock_uom"):
				self.set(field, item_details.get(field))

		if not self.transfer_qty and self.qty:
			self.transfer_qty = flt(
				flt(self.qty) * flt(self.conversion_factor), self.precision("transfer_qty")
			)

		if purpose == "Subcontracting Delivery":
			self.expense_account = frappe.get_value("Company", company, "default_expense_account")

	def validate_expense_account(self, is_opening, purpose):
		if not self.expense_account:
			frappe.throw(
				_(
					"Please enter <b>Difference Account</b> or set default "
					"<b>Stock Adjustment Account</b> for company {0}"
				).format(bold(self.parent_doc.company))
			)

		acc_details = frappe.get_cached_value(
			"Account",
			self.expense_account,
			["account_type", "report_type"],
			as_dict=True,
		)

		if is_opening == "Yes" and acc_details.report_type == "Profit and Loss":
			frappe.throw(
				_(
					"Difference Account must be a Asset/Liability type account "
					"(Temporary Opening), since this Stock Entry is an Opening Entry"
				),
				OpeningEntryAccountError,
			)

		if acc_details.account_type == "Stock":
			frappe.throw(
				_("At row #{0}: the Difference Account must not be a Stock type account...").format(
					self.idx, get_link_to_form("Account", self.expense_account)
				),
				title=_("Difference Account in Items Table"),
			)

		if (
			purpose not in ["Material Issue", "Subcontracting Delivery"]
			and acc_details.account_type == "Cost of Goods Sold"
		):
			frappe.msgprint(
				_("At row #{0}: you have selected the Difference Account {1}...").format(
					self.idx, bold(get_link_to_form("Account", self.expense_account))
				),
				indicator="orange",
				alert=1,
			)

	def set_transfer_qty(self):
		if not flt(self.conversion_factor):
			frappe.throw(_("Row {0}: UOM Conversion Factor is mandatory").format(self.idx))

		self.transfer_qty = flt(flt(self.qty) * flt(self.conversion_factor), self.precision("transfer_qty"))

		if not flt(self.transfer_qty):
			frappe.throw(
				_("Row {0}: Qty in Stock UOM can not be zero.").format(self.idx), title=_("Zero quantity")
			)

	def set_actual_qty(self, posting_date, posting_time):
		previous_sle = get_previous_sle(
			{
				"item_code": self.item_code,
				"warehouse": self.s_warehouse or self.t_warehouse,
				"posting_date": posting_date,
				"posting_time": posting_time,
			}
		)

		# get actual stock at source warehouse
		self.actual_qty = previous_sle.get("qty_after_transaction") or 0

	def delink_asset_repair_sabb(self, asset_repair):
		if not self.serial_and_batch_bundle:
			return

		voucher_detail_no = frappe.db.get_value(
			"Asset Repair Consumed Item",
			{"parent": asset_repair, "serial_and_batch_bundle": self.serial_and_batch_bundle},
			"name",
		)

		if not voucher_detail_no:
			return

		doc = frappe.get_doc("Serial and Batch Bundle", self.serial_and_batch_bundle)
		doc.db_set(
			{
				"voucher_type": "Asset Repair",
				"voucher_no": asset_repair,
				"voucher_detail_no": voucher_detail_no,
			}
		)
