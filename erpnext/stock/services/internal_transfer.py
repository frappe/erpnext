# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Internal (inter-company) transfer validation for stock transactions.

Extracted from ``StockController``. Validates warehouses, currency, packed items
and over-receipt quantities for internal-transfer stock vouchers. This is the
stock-side counterpart to ``accounts/services/internal_transfer.py`` (which owns
the party / rate / pricing / account side). The ``is_internal_transfer()``
predicate lives on ``AccountsController`` (delegating to the accounts service).
"""

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.utils import flt, get_link_to_form


class StockInternalTransferService:
	def __init__(self, doc) -> None:
		self.doc = doc

	def validate_internal_transfer(self):
		if self.doc.doctype in ("Sales Invoice", "Delivery Note", "Purchase Invoice", "Purchase Receipt"):
			if self.doc.is_internal_transfer():
				self.validate_in_transit_warehouses()
				self.validate_multi_currency()
				self.validate_packed_items()

				if self.doc.get("is_internal_supplier") and self.doc.docstatus == 1:
					self.validate_internal_transfer_qty()
			else:
				self.validate_internal_transfer_warehouse()

	def validate_internal_transfer_warehouse(self):
		for row in self.doc.items:
			if row.get("target_warehouse"):
				row.target_warehouse = None

			if row.get("from_warehouse"):
				row.from_warehouse = None

	def validate_in_transit_warehouses(self):
		if (
			self.doc.doctype == "Sales Invoice" and self.doc.get("update_stock")
		) or self.doc.doctype == "Delivery Note":
			for item in self.doc.get("items"):
				if not item.target_warehouse:
					frappe.throw(
						_("Row {0}: Target Warehouse is mandatory for internal transfers").format(item.idx)
					)

		if (
			self.doc.doctype == "Purchase Invoice" and self.doc.get("update_stock")
		) or self.doc.doctype == "Purchase Receipt":
			for item in self.doc.get("items"):
				if not item.from_warehouse:
					frappe.throw(
						_("Row {0}: From Warehouse is mandatory for internal transfers").format(item.idx)
					)

	def validate_multi_currency(self):
		if self.doc.currency != self.doc.company_currency:
			frappe.throw(_("Internal transfers can only be done in company's default currency"))

	def validate_packed_items(self):
		if self.doc.doctype in ("Sales Invoice", "Delivery Note Item") and self.doc.get("packed_items"):
			frappe.throw(_("Packed Items cannot be transferred internally"))

	def validate_internal_transfer_qty(self):
		if self.doc.doctype not in ["Purchase Invoice", "Purchase Receipt"]:
			return

		inter_company_reference = (
			self.doc.get("inter_company_reference")
			if self.doc.doctype == "Purchase Invoice"
			else self.doc.get("inter_company_invoice_reference")
		)

		item_wise_transfer_qty = self.get_item_wise_inter_transfer_qty(inter_company_reference)
		if not item_wise_transfer_qty:
			return

		item_wise_received_qty = self.get_item_wise_inter_received_qty()
		precision = frappe.get_precision(self.doc.doctype + " Item", "qty")

		over_receipt_allowance = frappe.get_single_value("Stock Settings", "over_delivery_receipt_allowance")

		parent_doctype = {
			"Purchase Receipt": "Delivery Note",
			"Purchase Invoice": "Sales Invoice",
		}.get(self.doc.doctype)

		for key, transferred_qty in item_wise_transfer_qty.items():
			recevied_qty = flt(item_wise_received_qty.get(key), precision)
			if over_receipt_allowance:
				transferred_qty = transferred_qty + flt(
					transferred_qty * over_receipt_allowance / 100, precision
				)

			if recevied_qty > flt(transferred_qty, precision):
				frappe.throw(
					_("For Item {0} cannot be received more than {1} qty against the {2} {3}").format(
						bold(key[1]),
						bold(flt(transferred_qty, precision)),
						bold(parent_doctype),
						get_link_to_form(parent_doctype, inter_company_reference),
					)
				)

	def get_item_wise_inter_transfer_qty(self, inter_company_reference):
		parent_doctype = {
			"Purchase Receipt": "Delivery Note",
			"Purchase Invoice": "Sales Invoice",
		}.get(self.doc.doctype)

		child_doctype = parent_doctype + " Item"

		parent_tab = frappe.qb.DocType(parent_doctype)
		child_tab = frappe.qb.DocType(child_doctype)

		query = (
			frappe.qb.from_(parent_doctype)
			.inner_join(child_tab)
			.on(child_tab.parent == parent_tab.name)
			.select(
				child_tab.name,
				child_tab.item_code,
				child_tab.qty,
			)
			.where((parent_tab.name == inter_company_reference) & (parent_tab.docstatus == 1))
		)

		data = query.run(as_dict=True)
		item_wise_transfer_qty = defaultdict(float)
		for row in data:
			item_wise_transfer_qty[(row.name, row.item_code)] += flt(row.qty)

		return item_wise_transfer_qty

	def get_item_wise_inter_received_qty(self):
		child_doctype = self.doc.doctype + " Item"

		parent_tab = frappe.qb.DocType(self.doc.doctype)
		child_tab = frappe.qb.DocType(child_doctype)

		query = (
			frappe.qb.from_(self.doc.doctype)
			.inner_join(child_tab)
			.on(child_tab.parent == parent_tab.name)
			.select(
				child_tab.item_code,
				child_tab.qty,
			)
			.where(parent_tab.docstatus == 1)
		)

		if self.doc.doctype == "Purchase Invoice":
			query = query.select(
				child_tab.sales_invoice_item.as_("name"),
			)

			query = query.where(
				parent_tab.inter_company_invoice_reference == self.doc.inter_company_invoice_reference
			)
		else:
			query = query.select(
				child_tab.delivery_note_item.as_("name"),
			)

			query = query.where(parent_tab.inter_company_reference == self.doc.inter_company_reference)

		data = query.run(as_dict=True)
		item_wise_transfer_qty = defaultdict(float)
		for row in data:
			item_wise_transfer_qty[(row.name, row.item_code)] += flt(row.qty)

		return item_wise_transfer_qty
