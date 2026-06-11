# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class QualityControlLot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accepted_qty: DF.Float
		batch_no: DF.Link | None
		company: DF.Link | None
		decided_qty: DF.Float
		disposed_qty: DF.Float
		inspection_basis: DF.Literal["Sample", "Each Quantity"]
		inspection_template: DF.Link | None
		item_code: DF.Link
		naming_series: DF.Literal["QCLOT-.YYYY.-"]
		pending_qty: DF.Float
		quality_inspection: DF.Link | None
		quality_warehouse: DF.Link
		received_qty: DF.Float
		rejected_qty: DF.Float
		returned_qty: DF.Float
		source_document: DF.DynamicLink | None
		source_document_type: DF.Link | None
		status: DF.Literal[
			"Under Inspection", "Awaiting Release", "Partially Released", "Released", "Rejected"
		]
	# end: auto-generated types

	def on_update(self):
		self._sync_source_quality_status()

	def after_delete(self):
		self._sync_source_quality_status()

	def _sync_source_quality_status(self):
		from erpnext.stock.services.quality_quarantine import sync_source_document_quality_status

		sync_source_document_quality_status(self.source_document_type, self.source_document)

	def validate(self):
		self.set_pending_qty_and_status()

	def set_pending_qty_and_status(self):
		self.pending_qty = flt(self.received_qty) - flt(self.accepted_qty) - flt(self.rejected_qty)

		undecided = flt(self.received_qty) - flt(self.decided_qty)
		awaiting_release = flt(self.decided_qty) - flt(self.rejected_qty) - flt(self.accepted_qty)
		moved = flt(self.accepted_qty) + flt(self.rejected_qty)
		if undecided > 0:
			# inspections may decide the lot in parts; until every unit is
			# decided the lot stays under inspection — Partially Released only
			# once accepted stock has actually left (a rejection is a verdict,
			# not a movement)
			self.status = "Partially Released" if flt(self.accepted_qty) > 0 else "Under Inspection"
		elif awaiting_release > 0:
			if flt(self.accepted_qty) > 0:
				self.status = "Partially Released"
			else:
				# the verdict is in but no stock has left yet — typically no
				# unique release warehouse, so the release awaits the user
				self.status = "Awaiting Release"
		elif flt(self.received_qty) <= 0 or moved <= 0:
			self.status = "Under Inspection"
		elif flt(self.accepted_qty) <= 0:
			self.status = "Rejected"
		else:
			self.status = "Released"

	def undecided_qty(self):
		return flt(self.received_qty) - flt(self.decided_qty)

	def awaiting_release_qty(self):
		return flt(self.decided_qty) - flt(self.rejected_qty) - flt(self.accepted_qty)


@frappe.whitelist()
def get_batch_summary(lot_name: str):
	"""The lot's batch with its live quarantine balance against the expected hold.

	The lot ledger says what should still be in the Quality Control warehouse
	(pending plus rejected stock not yet returned or disposed); the batch's
	actual balance there says what is. Computed fresh so a mismatch — however it
	came about — is visible right on the lot.
	"""
	from erpnext.stock.doctype.batch.batch import get_batch_qty

	lot = frappe.get_doc("Quality Control Lot", lot_name)
	lot.check_permission("read")
	if not lot.batch_no:
		return None

	expected_qty = (
		flt(lot.pending_qty) + flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty)
	)
	return {
		"batch_no": lot.batch_no,
		"held_qty": flt(get_batch_qty(lot.batch_no, lot.quality_warehouse)),
		"expected_qty": expected_qty,
	}


@frappe.whitelist()
def get_serial_numbers(lot_name: str):
	"""The lot's serials with their inspection verdict and current whereabouts.

	Membership comes from the lot's source document rows (the serials that
	physically entered quarantine with this lot), the verdict from the deciding
	inspections' per-unit verdicts, and the state from where each serial sits now —
	computed fresh, since serials leave the lot piecemeal through releases,
	returns and dispositions.
	"""
	from erpnext.stock.services.quality_trigger_resolution import get_row_serial_nos
	from erpnext.stock.services.quality_warehouse import is_rejected_warehouse

	lot = frappe.get_doc("Quality Control Lot", lot_name)
	lot.check_permission("read")
	if not frappe.get_cached_value("Item", lot.item_code, "has_serial_no"):
		return []
	if not lot.source_document_type or not lot.source_document:
		return []

	child_doctype = (
		"Stock Entry Detail"
		if lot.source_document_type == "Stock Entry"
		else lot.source_document_type + " Item"
	)
	members = set()
	for row in frappe.get_all(
		child_doctype,
		filters={"parent": lot.source_document, "item_code": lot.item_code},
		fields=["serial_no", "serial_and_batch_bundle"],
	):
		members.update(get_row_serial_nos(row))

	from erpnext.stock.services.quality_release import _union_unit_serials

	verdicts = {}
	for serial in _union_unit_serials(lot, "Accepted"):
		verdicts[serial] = "Accepted"
	for serial in _union_unit_serials(lot, "Rejected"):
		verdicts[serial] = "Rejected"

	serials = []
	for serial in sorted(members):
		info = frappe.db.get_value("Serial No", serial, ["warehouse", "batch_no"], as_dict=True)
		if not info:
			continue
		# a per-batch lot covers only its own batch's serials
		if lot.batch_no and info.batch_no and info.batch_no != lot.batch_no:
			continue

		if info.warehouse == lot.quality_warehouse:
			state = "In Quarantine"
		elif is_rejected_warehouse(info.warehouse):
			state = "Rejected Stock"
		elif info.warehouse:
			state = "Released"
		else:
			state = "Returned"

		serials.append(
			{
				"serial_no": serial,
				"verdict": verdicts.get(serial),
				"warehouse": info.warehouse,
				"state": state,
			}
		)
	return serials
