# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Quality inspection validation for stock transactions.

Extracted from ``StockController``. Validates that items requiring quality
inspection have a present / submitted / non-rejected Quality Inspection.
"""

import frappe
from frappe import _

from erpnext.exceptions import (
	QualityInspectionNotSubmittedError,
	QualityInspectionRejectedError,
	QualityInspectionRequiredError,
)

# Doctype -> the document-level "inspection required" flag. Shared with
# check_item_quality_inspection in stock_controller so the two stay in sync.
INSPECTION_FIELDNAME_MAP = {
	"Purchase Receipt": "inspection_required_before_purchase",
	"Purchase Invoice": "inspection_required_before_purchase",
	"Subcontracting Receipt": "inspection_required_before_purchase",
	"Sales Invoice": "inspection_required_before_delivery",
	"Delivery Note": "inspection_required_before_delivery",
}

# Purposes whose inward (t_warehouse) row is inspected.
QI_INCOMING_PURPOSES = (
	"Material Receipt",
	"Repack",
	"Receive from Customer",
	"Subcontracting Return",
)

# Purposes whose outgoing (s_warehouse) row is inspected. This is an explicit
# allow-list rather than "everything that isn't incoming" so a new purpose can't
# silently start requiring a QI. Material Consumption for Manufacture is left out
# on purpose: an inspection_required BOM inspects the manufactured output (handled
# by the "Manufacture" finished-good rule), not each consumed raw material.
# Keep this in sync with erpnext.stock.qi_* helpers in transaction.js.
QI_OUTGOING_PURPOSES = (
	"Material Issue",
	"Material Transfer",
	"Material Transfer for Manufacture",
	"Send to Subcontractor",
	"Subcontracting Delivery",
	"Disassemble",
)


def stock_entry_row_requires_inspection(purpose, row):
	"""Check if this Stock Entry row need a Quality Inspection."""
	if row.get("secondary_item_type") or row.get("is_legacy_scrap_item"):
		return False
	if purpose == "Manufacture":
		return bool(row.is_finished_item)
	if purpose in QI_INCOMING_PURPOSES:
		return bool(row.t_warehouse)
	if purpose in QI_OUTGOING_PURPOSES:
		return bool(row.s_warehouse and row.s_warehouse != row.t_warehouse)
	return False


class QualityInspectionService:
	def __init__(self, doc) -> None:
		self.doc = doc

	def validate_inspection(self):
		"""Checks if quality inspection is set/ is valid for Items that require inspection."""
		inspection_required_fieldname = INSPECTION_FIELDNAME_MAP.get(self.doc.doctype)

		# return if inspection is not required on document level
		if (
			(not inspection_required_fieldname and self.doc.doctype != "Stock Entry")
			or (self.doc.doctype == "Stock Entry" and not self.doc.inspection_required)
			or (self.doc.doctype in ["Sales Invoice", "Purchase Invoice"] and not self.doc.update_stock)
		):
			return

		for row in self.doc.get("items"):
			qi_required = False
			if inspection_required_fieldname and frappe.get_cached_value(
				"Item", row.item_code, inspection_required_fieldname
			):
				qi_required = True
			elif self.doc.doctype == "Stock Entry":
				qi_required = stock_entry_row_requires_inspection(self.doc.purpose, row)

			if row.get("secondary_item_type") or row.get("is_legacy_scrap_item"):
				continue

			if qi_required:  # validate row only if inspection is required on item level
				if self.doc.doctype in [
					"Purchase Receipt",
					"Purchase Invoice",
					"Sales Invoice",
					"Delivery Note",
				] and frappe.get_single_value(
					"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
				):
					return

				self.validate_qi_presence(row)
				if self.doc.docstatus == 1:
					self.validate_qi_submission(row)
					self.validate_qi_rejection(row)

	def validate_qi_presence(self, row):
		"""Check if QI is present on row level. Warn on save and stop on submit if missing."""
		if not row.quality_inspection:
			msg = _("Row #{0}: Quality Inspection is required for Item {1}").format(
				row.idx, frappe.bold(row.item_code)
			)
			if self.doc.docstatus == 1:
				frappe.throw(msg, title=_("Inspection Required"), exc=QualityInspectionRequiredError)
			else:
				frappe.msgprint(msg, title=_("Inspection Required"), indicator="blue")

	def validate_qi_submission(self, row):
		"""Check if QI is submitted on row level, during submission"""
		action = frappe.get_single_value("Stock Settings", "action_if_quality_inspection_is_not_submitted")
		qa_docstatus = frappe.db.get_value("Quality Inspection", row.quality_inspection, "docstatus")

		if qa_docstatus != 1:
			link = frappe.utils.get_link_to_form("Quality Inspection", row.quality_inspection)
			msg = _("Row #{0}: Quality Inspection {1} is not submitted for the item: {2}").format(
				row.idx, link, row.item_code
			)
			if action == "Stop":
				frappe.throw(msg, title=_("Inspection Submission"), exc=QualityInspectionNotSubmittedError)
			else:
				frappe.msgprint(msg, alert=True, indicator="orange")

	def validate_qi_rejection(self, row):
		"""Check if QI is rejected on row level, during submission"""
		action = frappe.get_single_value("Stock Settings", "action_if_quality_inspection_is_rejected")
		qa_status = frappe.db.get_value("Quality Inspection", row.quality_inspection, "status")

		if qa_status == "Rejected":
			link = frappe.utils.get_link_to_form("Quality Inspection", row.quality_inspection)
			msg = _("Row #{0}: Quality Inspection {1} was rejected for item {2}").format(
				row.idx, link, row.item_code
			)
			if action == "Stop":
				frappe.throw(msg, title=_("Inspection Rejected"), exc=QualityInspectionRejectedError)
			else:
				frappe.msgprint(msg, alert=True, indicator="orange")
