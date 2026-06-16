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
