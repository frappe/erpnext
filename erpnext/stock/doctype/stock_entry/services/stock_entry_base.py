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

		from erpnext.stock.doctype.item_alternative.item_alternative import is_alternative_item

		for row in self.doc.items:
			if not row.original_item or row.original_item == row.item_code:
				continue

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
