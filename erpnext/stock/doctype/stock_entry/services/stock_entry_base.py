import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import get_backflush_based_on


class BaseStockEntry:
	"""Shared foundation for all stock entry purpose handlers.

	Provides common lazy-loaded work order document, backflush configuration,
	and work order status validation used across multiple handler classes.
	"""

	def __init__(self, se_doc):
		self.doc = se_doc

	@property
	def wo_doc(self):
		if not getattr(self, "_wo_doc", None):
			if self.doc.work_order:
				self._wo_doc = frappe.get_doc("Work Order", self.doc.work_order)
		return getattr(self, "_wo_doc", None)

	@property
	def backflush_based_on(self):
		return get_backflush_based_on(self.doc.bom_no)

	def _validate_work_order(self):
		if not self.wo_doc:
			return

		msg = ""
		if flt(self.wo_doc.docstatus) != 1:
			msg = _("Work Order {0} must be submitted").format(self.doc.work_order)

		if self.wo_doc.status == "Stopped":
			msg = _("Transaction not allowed against stopped Work Order {0}").format(self.doc.work_order)

		if msg:
			frappe.throw(msg)

	def validate_alternative_items(self):
		if not self.wo_doc:
			return

		rows = [row for row in self.doc.items if row.original_item and row.original_item != row.item_code]
		if not rows:
			return

		transferred_pairs = self.get_transferred_alternative_pairs()
		for row in rows:
			if (row.original_item, row.item_code) not in transferred_pairs:
				self.validate_alternative_item_row(row)

	def validate_alternative_item_row(self, row):
		from erpnext.stock.doctype.item_alternative.item_alternative import is_alternative_item

		if not self.wo_doc.allow_alternative_item:
			frappe.throw(
				_("Row #{0}: Work Order {1} does not allow alternative items").format(
					row.idx, frappe.bold(self.doc.work_order)
				)
			)

		if not is_alternative_item(row.original_item, row.item_code):
			frappe.throw(
				_("Row #{0}: Item {1} is not an alternative of Item {2}").format(
					row.idx, frappe.bold(row.item_code), frappe.bold(row.original_item)
				)
			)

	def get_transferred_alternative_pairs(self):
		if self.doc.purpose == "Material Transfer for Manufacture" and not self.doc.is_return:
			return set()

		stock_entry = frappe.qb.DocType("Stock Entry")
		stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")

		pairs = (
			frappe.qb.from_(stock_entry)
			.inner_join(stock_entry_detail)
			.on(stock_entry.name == stock_entry_detail.parent)
			.select(stock_entry_detail.original_item, stock_entry_detail.item_code)
			.distinct()
			.where(
				(stock_entry.work_order == self.doc.work_order)
				& (stock_entry.purpose == "Material Transfer for Manufacture")
				& (stock_entry.is_return == 0)
				& (stock_entry.docstatus == 1)
				& (stock_entry_detail.original_item.isnotnull())
				& (stock_entry_detail.original_item != stock_entry_detail.item_code)
			)
		).run()

		return {tuple(pair) for pair in pairs}
