# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.stock.services.quality_warehouse import is_rejected_warehouse

from .material_transfer import MaterialTransferStockEntry


class QualityControlReleaseStockEntry(MaterialTransferStockEntry):
	"""Release quarantined stock out of a Quality Control warehouse.

	Behaves exactly like a Material Transfer — source and target warehouse, stock
	value carried over, no GL impact — but is a distinct purpose so it is the only
	stock movement (besides a purchase return) allowed to take stock out of a
	Quality Control warehouse. Every release must be backed by a Quality Control
	Lot with a submitted Quality Inspection, so stock cannot leave quarantine
	without a recorded decision.

	The target warehouse decides what a row may move: an ordinary warehouse
	receives accepted stock; a Rejected warehouse receives rejected stock, where
	normal stock rules take over (scrap, rework, sale as scrap).
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

		accepted_serials = self._get_unit_serials(lot, "Accepted")
		rejected_serials = self._get_unit_serials(lot, "Rejected")
		release_qty = 0.0
		disposal_qty = 0.0
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
			self._validate_row_batch(row, lot)
			if is_rejected_warehouse(row.t_warehouse):
				self._validate_row_serials(row, lot, rejected_serials, verdict="Rejected")
				disposal_qty += flt(row.transfer_qty or row.qty)
			else:
				self._validate_row_serials(row, lot, accepted_serials, verdict="Accepted")
				release_qty += flt(row.transfer_qty or row.qty)

		# inspections may decide the lot in parts: only the accepted-and-not-yet-
		# released quantity may leave — never undecided stock that merely shares
		# the warehouse
		awaiting_release = lot.awaiting_release_qty()
		if release_qty > awaiting_release:
			frappe.throw(
				_(
					"Cannot release {0} from Quality Control Lot {1}: only {2} accepted unit(s) "
					"await release."
				).format(release_qty, lot.name, awaiting_release),
				title=_("Quantity Exceeds Accepted Stock"),
			)

		rejected_outstanding = flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty)
		if disposal_qty > rejected_outstanding:
			frappe.throw(
				_(
					"Cannot move {0} to a Rejected warehouse from Quality Control Lot {1}: only {2} "
					"rejected unit(s) remain in quarantine."
				).format(disposal_qty, lot.name, rejected_outstanding),
				title=_("Quantity Exceeds Rejected Stock"),
			)

	def _validate_row_batch(self, row, lot):
		"""The release moves the lot's own batch — not another batch of the same
		item that happens to share the Quality Control warehouse."""
		if not lot.batch_no:
			return

		row_batches = set()
		if row.get("batch_no"):
			row_batches.add(row.batch_no)
		if row.get("serial_and_batch_bundle"):
			row_batches.update(
				frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					pluck="batch_no",
				)
			)

		if row_batches - {lot.batch_no}:
			frappe.throw(
				_("Row #{0}: Quality Control Lot {1} holds batch {2} — a release cannot move {3}.").format(
					row.idx,
					lot.name,
					frappe.bold(lot.batch_no),
					frappe.bold(", ".join(sorted(row_batches - {lot.batch_no}))),
				),
				title=_("Batch Mismatch"),
			)

		if not row_batches:
			frappe.throw(
				_("Row #{0}: Specify batch {1} of Quality Control Lot {2} on the release.").format(
					row.idx, frappe.bold(lot.batch_no), lot.name
				),
				title=_("Batch Missing"),
			)

	def _get_unit_serials(self, lot, status):
		"""The serials the lot's verdicts allow this movement, or None when no
		per-serial verdicts were recorded (quantity and batch guards apply instead).

		Verdicts accumulate across the lot's inspections. Accepted releases may
		also move the serials of a verdict-less remainder once the lot is fully
		decided — never a rejected or undecided serial.
		"""
		from erpnext.stock.services.quality_quarantine import (
			_accepted_serials_awaiting_release,
			_union_unit_serials,
		)

		rejected = _union_unit_serials(lot, "Rejected")
		if not rejected and not _union_unit_serials(lot, "Accepted"):
			return None

		if status == "Rejected":
			return rejected or None

		return set(_accepted_serials_awaiting_release(lot) or []) or None

	def _validate_row_serials(self, row, lot, allowed_serials, verdict):
		"""A row moves only serials whose inspection verdict matches its target.

		With per-serial verdicts on record, a row must name its serials — left
		unspecified, submission would auto-pick first-in-first-out and could
		smuggle a rejected unit out to the store, or an accepted one to the
		Rejected warehouse.
		"""
		if allowed_serials is None:
			return

		row_serials = set()
		if row.get("serial_no"):
			from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

			row_serials.update(get_serial_nos(row.serial_no))
		if row.get("serial_and_batch_bundle"):
			row_serials.update(
				frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle, "serial_no": ("is", "set")},
					pluck="serial_no",
				)
			)

		if not row_serials:
			frappe.throw(
				_("Row #{0}: Specify the {1} serial numbers of Quality Control Lot {2}.").format(
					row.idx, _(verdict.lower()), lot.name
				),
				title=_("Serial Numbers Missing"),
			)

		mismatched = row_serials - allowed_serials
		if mismatched:
			frappe.throw(
				_(
					"Row #{0}: Serial number(s) {1} were not {2} by the inspection of Quality "
					"Control Lot {3} and cannot move to {4}."
				).format(
					row.idx,
					frappe.bold(", ".join(sorted(mismatched))),
					_(verdict.lower()),
					lot.name,
					frappe.bold(row.t_warehouse),
				),
				title=_("Serial Verdict Mismatch"),
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
		released = disposed = 0.0
		for row in doc.items:
			if is_rejected_warehouse(row.t_warehouse):
				disposed += flt(row.transfer_qty or row.qty)
			else:
				released += flt(row.transfer_qty or row.qty)
		lot.accepted_qty = flt(lot.accepted_qty) + direction * released
		lot.disposed_qty = flt(lot.disposed_qty) + direction * disposed
		lot.flags.ignore_permissions = True
		lot.save()
