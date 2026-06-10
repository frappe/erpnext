# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from .material_transfer import MaterialTransferStockEntry


class QualityControlReleaseStockEntry(MaterialTransferStockEntry):
	"""Release quarantined stock out of a Quality Control warehouse.

	Behaves exactly like a Material Transfer — source and target warehouse, stock
	value carried over, no GL impact — but is a distinct purpose so it is the only
	stock movement (besides a purchase return) allowed to take stock out of a
	Quality Control warehouse. Every release must be backed by a Quality Control
	Lot with a submitted Quality Inspection, so stock cannot leave quarantine
	without a recorded decision.
	"""

	def validate(self):
		super().validate()
		self.validate_against_quality_control_lot()

	def validate_against_quality_control_lot(self):
		doc = self.doc

		if not doc.get("quality_control_lot"):
			frappe.throw(
				_("A Quality Control Release must reference the Quality Control Lot it releases."),
				title=_("Quality Control Lot Missing"),
			)

		lot = frappe.get_doc("Quality Control Lot", doc.quality_control_lot)

		if (
			not lot.quality_inspection
			or frappe.db.get_value("Quality Inspection", lot.quality_inspection, "docstatus") != 1
		):
			frappe.throw(
				_(
					"Quality Control Lot {0} has no submitted Quality Inspection. Stock cannot leave "
					"quarantine without a recorded inspection decision."
				).format(frappe.bold(lot.name)),
				title=_("Inspection Pending"),
			)

		release_qty = 0.0
		for row in doc.items:
			if row.item_code != lot.item_code:
				frappe.throw(
					_("Row #{0}: Item {1} does not belong to Quality Control Lot {2} (item {3}).").format(
						row.idx, frappe.bold(row.item_code), lot.name, frappe.bold(lot.item_code)
					)
				)
			if row.s_warehouse != lot.quality_warehouse:
				frappe.throw(
					_(
						"Row #{0}: Source warehouse must be {1}, where Quality Control Lot {2} is held."
					).format(row.idx, frappe.bold(lot.quality_warehouse), lot.name)
				)
			release_qty += flt(row.transfer_qty or row.qty)

		if release_qty > flt(lot.pending_qty):
			frappe.throw(
				_(
					"Cannot release {0} from Quality Control Lot {1}: only {2} is pending inspection release."
				).format(release_qty, lot.name, lot.pending_qty),
				title=_("Quantity Exceeds Lot"),
			)

	def on_submit(self):
		super().on_submit()
		self._apply_to_lot(+1)

	def on_cancel(self):
		super().on_cancel()
		self._apply_to_lot(-1)

	def _apply_to_lot(self, direction):
		doc = self.doc
		lot = frappe.get_doc("Quality Control Lot", doc.quality_control_lot)
		released = sum(flt(row.transfer_qty or row.qty) for row in doc.items)
		lot.accepted_qty = flt(lot.accepted_qty) + direction * released
		lot.flags.ignore_permissions = True
		lot.save()
