# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import cint

from erpnext.assets.doctype.asset.depreciation import get_disposal_account_and_cost_center
from erpnext.stock.doctype.serial_no.serial_no import get_delivery_note_serial_no, get_serial_nos


class SalesInvoiceItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_batch_qty: DF.Float
		actual_qty: DF.Float
		allow_zero_valuation_rate: DF.Check
		amount: DF.Currency
		asset: DF.Link | None
		barcode: DF.Data | None
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		batch_no: DF.Link | None
		brand: DF.Data | None
		conversion_factor: DF.Float
		cost_center: DF.Link
		customer_item_code: DF.Data | None
		deferred_revenue_account: DF.Link | None
		delivered_by_supplier: DF.Check
		delivered_qty: DF.Float
		delivery_note: DF.Link | None
		description: DF.TextEditor | None
		discount_account: DF.Link | None
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		dn_detail: DF.Data | None
		enable_deferred_revenue: DF.Check
		expense_account: DF.Link | None
		finance_book: DF.Link | None
		grant_commission: DF.Check
		has_item_scanned: DF.Check
		image: DF.Attach | None
		income_account: DF.Link
		incoming_rate: DF.Currency
		is_fixed_asset: DF.Check
		is_free_item: DF.Check
		item_code: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data
		item_tax_rate: DF.SmallText | None
		item_tax_template: DF.Link | None
		margin_rate_or_amount: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		net_amount: DF.Currency
		net_rate: DF.Currency
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		project: DF.Link | None
		purchase_order: DF.Link | None
		purchase_order_item: DF.Data | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		rate: DF.Currency
		rate_with_margin: DF.Currency
		sales_invoice_item: DF.Data | None
		sales_order: DF.Link | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		service_end_date: DF.Date | None
		service_start_date: DF.Date | None
		service_stop_date: DF.Date | None
		so_detail: DF.Data | None
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		stock_uom_rate: DF.Currency
		target_warehouse: DF.Link | None
		total_weight: DF.Float
		uom: DF.Link
		use_serial_batch_fields: DF.Check
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
	# end: auto-generated types

	def validate_cost_center(self, company: str):
		cost_center_company = frappe.get_cached_value("Cost Center", self.cost_center, "company")
		if cost_center_company != company:
			frappe.throw(
				_("Row #{0}: Cost Center {1} does not belong to company {2}").format(
					frappe.bold(self.idx), frappe.bold(self.cost_center), frappe.bold(company)
				)
			)

	def set_actual_qty(self):
		if self.item_code and self.warehouse:
			self.actual_qty = (
				frappe.db.get_value(
					"Bin", {"item_code": self.item_code, "warehouse": self.warehouse}, "actual_qty"
				)
				or 0
			)

	def set_income_account_for_fixed_asset(self, company: str):
		"""Set income account for fixed asset item based on company's disposal account and cost center."""
		if not self.is_fixed_asset:
			return

		disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)

		self.income_account = disposal_account
		if not self.cost_center:
			self.cost_center = depreciation_cost_center

	def set_serial_no_against_delivery_note(self):
		"""Set serial no based on delivery note."""
		if self.serial_no and self.delivery_note and self.qty != len(get_serial_nos(self.serial_no)):
			self.serial_no = get_delivery_note_serial_no(self.item_code, self.qty, self.delivery_note)

	def validate_serial_against_delivery_note(self):
		"""Ensure the serial numbers in this Sales Invoice Item are same as in the linked Delivery Note."""
		if not self.delivery_note or not self.dn_detail:
			return

		serial_nos = frappe.db.get_value("Delivery Note Item", self.dn_detail, "serial_no") or ""
		dn_serial_nos = set(get_serial_nos(serial_nos))

		serial_nos = self.serial_no or ""
		si_serial_nos = set(get_serial_nos(serial_nos))
		serial_no_diff = si_serial_nos - dn_serial_nos

		if serial_no_diff:
			dn_link = frappe.utils.get_link_to_form("Delivery Note", self.delivery_note)
			msg = (
				_("Row #{0}: The following serial numbers are not present in Delivery Note {1}:").format(
					self.idx, dn_link
				)
				+ " "
				+ ", ".join(frappe.bold(d) for d in serial_no_diff)
			)

			frappe.throw(msg=msg, title=_("Serial Nos Mismatch"))

		if self.serial_no and cint(self.qty) != len(si_serial_nos):
			frappe.throw(
				_(
					"Row #{0}: {1} serial numbers are required for Item {2}. You have provided {3} serial numbers."
				).format(self.idx, self.qty, self.item_code, len(si_serial_nos))
			)
