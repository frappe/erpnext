# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from math import isfinite
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, get_link_to_form
from frappe.utils.number_format import NUMBER_FORMAT_MAP, NumberFormat

from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)
from erpnext.stock.services.quality_inspection_service import (
	QI_INCOMING_PURPOSES,
	QI_OUTGOING_PURPOSES,
)


class QualityInspection(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.quality_inspection_reading_entry.quality_inspection_reading_entry import (
			QualityInspectionReadingEntry,
		)

		from erpnext.stock.doctype.quality_inspection_reading.quality_inspection_reading import (
			QualityInspectionReading,
		)

		amended_from: DF.Link | None
		batch_no: DF.Link | None
		bom_no: DF.Link | None
		child_row_reference: DF.Data | None
		company: DF.Link | None
		description: DF.SmallText | None
		inspected_by: DF.Link
		inspection_basis: DF.Literal["", "Sample", "Each Quantity"]
		inspection_type: DF.Literal["", "Incoming", "Outgoing", "In Process"]
		item_code: DF.Link
		item_name: DF.Data | None
		serial_no: DF.SmallText | None
		letter_head: DF.Link | None
		manual_inspection: DF.Check
		naming_series: DF.Literal["MAT-QA-.YYYY.-"]
		quality_inspection_template: DF.Link | None
		readings: DF.Table[QualityInspectionReading]
		reference_name: DF.DynamicLink
		reference_type: DF.Literal[
			"",
			"Purchase Receipt",
			"Purchase Invoice",
			"Subcontracting Receipt",
			"Delivery Note",
			"Sales Invoice",
			"Stock Entry",
			"Job Card",
			"Quality Control Lot",
		]
		remarks: DF.Text | None
		report_date: DF.Date
		sample_size: DF.Float
		decided_quantity: DF.Float
		accepted_unit_quantity: DF.Int
		rejected_unit_quantity: DF.Int
		unit_quantity: DF.Int
		unit_readings: DF.Table[QualityInspectionReadingEntry]
		status: DF.Literal["", "Accepted", "Partially Accepted", "Rejected", "Cancelled"]
		verified_by: DF.Data | None

	# end: auto-generated types
	def on_discard(self):
		self.update_qc_reference()
		self.db_set("status", "Cancelled")

	def validate(self):
		self.set_inspection_basis_from_lot()
		# the reference must be resolved before the unit machinery runs: the
		# quantity under inspection comes off the referenced row or lot
		self.validate_item_belongs_to_reference()
		self.set_child_row_reference()

		if self.inspection_basis == "Each Quantity":
			# per-unit readings live in the unit readings table; rows lurking in
			# the hidden readings table would invisibly block submission
			self.set("readings", [])
			if not cint(self.unit_quantity):
				self.unit_quantity = cint(self.get_qty_under_inspection() or 0)
			self.validate_units()
			self.evaluate_unit_entry_statuses()
			self.roll_up_unit_results()
		else:
			# symmetric shed: a basis flipped back to Sample drops per-unit rows
			self.set("unit_readings", [])
			self.unit_quantity = 0
			self.roll_up_unit_results()
			if not self.readings and self.item_code:
				self.get_item_specification_details()

		if (
			self.inspection_type == "In Process"
			and self.reference_type == "Job Card"
			and self.quality_inspection_template
		):
			parameters = get_template_details(self.quality_inspection_template)
			for reading in self.readings:
				for d in parameters:
					if reading.specification == d.specification:
						reading.update(d)
						reading.status = "Accepted"

		if self.readings:
			self.validate_reading_number_format()
			self.inspect_and_set_status()
		elif self.unit_readings and not self.manual_inspection:
			self.set_status_from_unit_readings()

		self.set_decided_quantity_default()
		self.validate_inspection_required()
		self.validate_serial_nos()
		self.set_company()
		self.warn_unrecorded_readings()

	def set_company(self):
		if self.reference_type and self.reference_name:
			company = frappe.get_cached_value(self.reference_type, self.reference_name, "company")
			if company != self.company:
				self.company = company

	def validate_item_belongs_to_reference(self):
		"""The inspected item must be on the referenced document.

		The form's item picker only offers the reference's items; this is the
		server-side authority behind it — an inspection of an unrelated item
		would still decide the reference (a wrong-item verdict could book a
		lot's quantities or gate a document row it never looked at).
		"""
		if not (self.reference_type and self.reference_name and self.item_code):
			return

		# a caller that skips link validation has no real reference to check against
		if self.flags.ignore_links:
			return

		if self.reference_type == "Quality Control Lot":
			lot_item = frappe.db.get_value("Quality Control Lot", self.reference_name, "item_code")
			if lot_item and lot_item != self.item_code:
				frappe.throw(
					_("Quality Control Lot {0} holds item {1}, not {2}.").format(
						frappe.bold(self.reference_name), frappe.bold(lot_item), frappe.bold(self.item_code)
					),
					title=_("Item Not On Reference"),
				)
			return

		if self.reference_type == "Job Card":
			production_item = frappe.db.get_value("Job Card", self.reference_name, "production_item")
			if production_item and production_item != self.item_code:
				frappe.throw(
					_("Job Card {0} produces item {1}, not {2}.").format(
						frappe.bold(self.reference_name),
						frappe.bold(production_item),
						frappe.bold(self.item_code),
					),
					title=_("Item Not On Reference"),
				)
			return

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		if not frappe.db.exists(
			child_doctype,
			{"parent": self.reference_name, "item_code": self.item_code, "docstatus": ("<", 2)},
		):
			frappe.throw(
				_("Item {0} is not on {1} {2}.").format(
					frappe.bold(self.item_code),
					_(self.reference_type),
					frappe.bold(self.reference_name),
				),
				title=_("Item Not On Reference"),
			)

	def set_child_row_reference(self):
		if self.child_row_reference:
			return

		if not (self.reference_type and self.reference_name):
			return

		# a Quality Control Lot has no item child table to reference
		if self.reference_type == "Quality Control Lot":
			return

		doctype = self.reference_type + " Item"
		if self.reference_type == "Stock Entry":
			doctype = "Stock Entry Detail"

		child_doc = frappe.qb.DocType(doctype)
		qi_doc = frappe.qb.DocType("Quality Inspection")

		child_row_references = (
			frappe.qb.from_(child_doc)
			.left_join(qi_doc)
			.on(child_doc.name == qi_doc.child_row_reference)
			.select(child_doc.name)
			.where(
				(child_doc.item_code == self.item_code)
				& (child_doc.parent == self.reference_name)
				& (child_doc.docstatus < 2)
				& (qi_doc.name.isnull())
			)
			.orderby(child_doc.idx)
		).run(pluck=True)

		if len(child_row_references):
			self.child_row_reference = child_row_references[0]

	def set_inspection_basis_from_lot(self):
		"""Prefill how the stock is inspected (Sample / Each Quantity).

		The Quality Control Lot (or the item's quality trigger) proposes the
		basis; a basis already on the document is the inspector's choice and is
		left alone.
		"""
		from erpnext.stock.services.quality_trigger_resolution import get_inspection_basis

		if self.inspection_basis:
			return

		if self.reference_type == "Quality Control Lot" and self.reference_name:
			self.inspection_basis = (
				frappe.db.get_value("Quality Control Lot", self.reference_name, "inspection_basis")
				or "Sample"
			)
		elif self.reference_type and self.item_code:
			self.inspection_basis = get_inspection_basis(self.item_code, self.reference_type)
		else:
			self.inspection_basis = "Sample"

	def set_status_from_unit_readings(self):
		"""The per-unit roll-up decides the verdict unless the inspector overrides."""
		if self.accepted_unit_quantity and self.rejected_unit_quantity:
			self.status = "Partially Accepted"
		elif self.accepted_unit_quantity:
			self.status = "Accepted"
		else:
			self.status = "Rejected"

	def validate_serial_nos(self):
		"""The recorded serials must be real and the item's; they set the sample size.

		Each Quantity inspections record serials per unit in the reading bundle,
		so the document-level field is cleared there.
		"""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if self.inspection_basis == "Each Quantity":
			self.serial_no = None
			return

		if not self.serial_no:
			return

		serial_nos = get_serial_nos(self.serial_no)
		incoming = self._referenced_row_typed_serials()
		for serial in serial_nos:
			info = frappe.db.get_value("Serial No", serial, ["item_code", "batch_no"], as_dict=True)
			if not info:
				if serial in incoming:
					# inward documents create their serials at submission; a serial
					# typed on the row under inspection is legitimate before then
					continue
				frappe.throw(_("Serial No {0} does not exist.").format(frappe.bold(serial)))
			if info.item_code != self.item_code:
				frappe.throw(
					_("Serial No {0} belongs to item {1}, not {2}.").format(
						frappe.bold(serial), frappe.bold(info.item_code), frappe.bold(self.item_code)
					)
				)
			# both-tracked items: the serial's own batch is the truth the named
			# batch must agree with
			if self.batch_no and info.batch_no and info.batch_no != self.batch_no:
				frappe.throw(
					_("Serial No {0} belongs to batch {1}, not {2}.").format(
						frappe.bold(serial), frappe.bold(info.batch_no), frappe.bold(self.batch_no)
					),
					title=_("Serial and Batch Disagree"),
				)

		if serial_nos:
			self.sample_size = len(serial_nos)

	def _referenced_row_awaits_batch(self):
		"""Whether the row under inspection will only get its batch at submission.

		Auto-created batches do not exist before the inbound document submits, so
		the inspection cannot name one — the document-side consistency gate takes
		over once the batch materialises.
		"""
		if not self.child_row_reference or self.reference_type == "Quality Control Lot":
			return False

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		row = frappe.db.get_value(
			child_doctype,
			self.child_row_reference,
			["batch_no", "serial_and_batch_bundle"],
			as_dict=True,
		)
		if not row:
			return False

		from erpnext.stock.services.quality_trigger_resolution import get_row_batch_nos

		return not get_row_batch_nos(row)

	def _referenced_row_typed_serials(self):
		"""Serials typed on the referenced row — acceptable before they exist."""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if not self.child_row_reference or self.reference_type == "Quality Control Lot":
			return set()

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		typed = frappe.db.get_value(child_doctype, self.child_row_reference, "serial_no")
		return set(get_serial_nos(typed or ""))

	def validate_inspection_required(self):
		# Obsolete under the Item Quality Trigger model: Quality Inspection requirement is governed
		# by triggers on the transaction, not by per-Item flags or a global setting.
		pass

	def before_submit(self):
		self.validate_readings_status_mandatory()
		self.validate_readings_recorded()
		self.validate_sample_size()
		self.validate_unit_readings_complete()
		self.validate_tracking_identity_recorded()
		self.validate_inspected_serials_against_reference()
		self.validate_inspected_batch_against_reference()
		self.validate_unit_readings_coverage()
		self.validate_decided_quantity()
		self.validate_units_not_already_decided()

	def set_decided_quantity_default(self):
		"""A blank (or zero) Decided Quantity means everything still undecided."""
		if (
			self.reference_type == "Quality Control Lot"
			and self.reference_name
			and (self.inspection_basis != "Each Quantity" or self.manual_inspection)
			and not flt(self.decided_quantity)
		):
			self.decided_quantity = flt(self.get_qty_under_inspection())

	def validate_decided_quantity(self):
		"""Resolve and bound how much of the lot this verdict decides.

		Each Quantity verdicts decide exactly their units. Sample and manual
		verdicts decide the stated quantity, defaulting to everything still
		undecided — and for serialized items a partial verdict must name its
		units, so it has to be on an Each Quantity basis.
		"""
		if self.reference_type != "Quality Control Lot" or not self.reference_name:
			self.decided_quantity = 0
			return

		undecided = flt(self.get_qty_under_inspection())
		if self.inspection_basis == "Each Quantity" and not self.manual_inspection:
			self.decided_quantity = flt(self.unit_quantity)
		elif not flt(self.decided_quantity):
			self.decided_quantity = undecided

		if flt(self.decided_quantity) <= 0:
			frappe.throw(
				_("This inspection decides nothing — the Decided Quantity must be greater than zero."),
				title=_("Nothing To Decide"),
			)
		if flt(self.decided_quantity) > undecided:
			frappe.throw(
				_(
					"This inspection decides {0} unit(s), but only {1} remain undecided on Quality "
					"Control Lot {2}."
				).format(self.decided_quantity, undecided, frappe.bold(self.reference_name)),
				title=_("More Than Undecided"),
			)

		if self.inspection_basis != "Each Quantity" and flt(self.sample_size) > flt(self.decided_quantity):
			frappe.throw(
				_(
					"The sample of {0} unit(s) exceeds the {1} unit(s) this verdict decides — a "
					"sample is drawn from the quantity it decides."
				).format(self.sample_size, self.decided_quantity),
				title=_("Sample Exceeds Decided Quantity"),
			)

		if (
			flt(self.decided_quantity) < undecided
			and not (self.inspection_basis == "Each Quantity" and not self.manual_inspection)
			and frappe.get_cached_value("Item", self.item_code, "has_serial_no")
		):
			frappe.throw(
				_(
					"A partial verdict on a serialized item must say which units it covers — "
					"use the Each Quantity basis with per-unit readings."
				),
				title=_("Partial Verdict Needs Unit Readings"),
			)

	def validate_units_not_already_decided(self):
		"""A serial decided by an earlier verdict cannot be decided again."""
		if self.reference_type != "Quality Control Lot" or not self.unit_readings:
			return

		decided_serials = set(
			frappe.get_all(
				"Quality Inspection Reading Entry",
				filters={
					"parenttype": "Quality Inspection",
					"parentfield": "unit_readings",
					"parent": (
						"in",
						frappe.get_all(
							"Quality Inspection",
							filters={
								"reference_type": "Quality Control Lot",
								"reference_name": self.reference_name,
								"docstatus": 1,
								"name": ("!=", self.name),
							},
							pluck="name",
						),
					),
					"serial_no": ("is", "set"),
				},
				pluck="serial_no",
			)
		)
		repeated = {
			entry.serial_no for entry in self.unit_readings if entry.serial_no
		} & decided_serials
		if repeated:
			frappe.throw(
				_("Serial number(s) {0} were already decided by an earlier inspection of this lot.").format(
					frappe.bold(", ".join(sorted(repeated)))
				),
				title=_("Serials Already Decided"),
			)

	def validate_sample_size(self):
		"""A Sample inspection of zero units is a verdict about nothing."""
		if self.inspection_basis == "Each Quantity":
			return
		if flt(self.sample_size) <= 0:
			frappe.throw(
				_("A Sample inspection must inspect at least one unit — set the Sample Size."),
				title=_("Sample Size Missing"),
			)

	def validate_inspected_batch_against_reference(self):
		"""The inspected batch must be the batch of the stock under inspection."""
		from erpnext.stock.services.quality_trigger_resolution import get_row_batch_nos

		if not self.batch_no:
			return

		if self.reference_type == "Quality Control Lot" and self.reference_name:
			lot_batch = frappe.db.get_value("Quality Control Lot", self.reference_name, "batch_no")
			if lot_batch and self.batch_no != lot_batch:
				frappe.throw(
					_("Quality Control Lot {0} holds batch {1}, not {2}.").format(
						self.reference_name, frappe.bold(lot_batch), frappe.bold(self.batch_no)
					),
					title=_("Inspected Batch Mismatch"),
				)
			return

		if not self.child_row_reference:
			return

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		row = frappe.db.get_value(
			child_doctype,
			self.child_row_reference,
			["batch_no", "serial_and_batch_bundle"],
			as_dict=True,
		)
		if not row:
			return

		row_batches = get_row_batch_nos(row)
		if row_batches and self.batch_no not in row_batches:
			frappe.throw(
				_(
					"Batch {0} is not on the document row under inspection — only the stock "
					"actually moving can be inspected."
				).format(frappe.bold(self.batch_no)),
				title=_("Inspected Batch Mismatch"),
			)

	def validate_inspected_serials_against_reference(self):
		"""The inspected serials must belong to the stock under inspection.

		Lot-referenced inspections check against the serials that arrived through
		the lot's source document (falling back to "currently held in the lot's
		Quality Control warehouse"); transaction-referenced ones check against the
		referenced row when it already carries serials — the document-side gate at
		its submission is the authority there either way. Covers the sampled
		Serial Nos and the reading bundle's per-unit serials alike.
		"""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		from erpnext.stock.services.quality_trigger_resolution import get_row_serial_nos

		inspected = set(get_serial_nos(self.serial_no)) if (self.serial_no or "").strip() else set()
		inspected.update(entry.serial_no for entry in self.get("unit_readings") if entry.serial_no)
		if not inspected:
			return

		if self.reference_type == "Quality Control Lot" and self.reference_name:
			lot = frappe.db.get_value(
				"Quality Control Lot",
				self.reference_name,
				["item_code", "quality_warehouse", "source_document_type", "source_document"],
				as_dict=True,
			)

			members = set()
			if lot.source_document_type and lot.source_document:
				child_doctype = (
					"Stock Entry Detail"
					if lot.source_document_type == "Stock Entry"
					else lot.source_document_type + " Item"
				)
				for row in frappe.get_all(
					child_doctype,
					filters={"parent": lot.source_document, "item_code": lot.item_code},
					fields=["serial_no", "serial_and_batch_bundle"],
				):
					members.update(get_row_serial_nos(row))

			if members:
				missing = inspected - members
				if missing:
					frappe.throw(
						_(
							"Serial number(s) {0} did not arrive through {1}, the source of "
							"Quality Control Lot {2} — only the lot's own units can be inspected."
						).format(
							frappe.bold(", ".join(sorted(missing))),
							frappe.bold(lot.source_document),
							self.reference_name,
						),
						title=_("Inspected Serials Mismatch"),
					)
			else:
				strangers = [
					serial
					for serial in sorted(inspected)
					if frappe.db.get_value("Serial No", serial, "warehouse") != lot.quality_warehouse
				]
				if strangers:
					frappe.throw(
						_(
							"Serial number(s) {0} are not held in {1}, where Quality Control Lot "
							"{2} is quarantined."
						).format(
							frappe.bold(", ".join(strangers)),
							frappe.bold(lot.quality_warehouse),
							self.reference_name,
						),
						title=_("Inspected Serials Mismatch"),
					)
			return

		if not self.child_row_reference:
			return

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		row = frappe.db.get_value(
			child_doctype,
			self.child_row_reference,
			["serial_no", "serial_and_batch_bundle"],
			as_dict=True,
		)
		if not row:
			return

		row_serials = get_row_serial_nos(row)
		if not row_serials:
			return

		missing = inspected - row_serials
		if missing:
			frappe.throw(
				_(
					"Sampled serial number(s) {0} are not on the document row under inspection — "
					"only the stock actually moving can be sampled."
				).format(frappe.bold(", ".join(sorted(missing)))),
				title=_("Sampled Serials Mismatch"),
			)

	def validate_tracking_identity_recorded(self):
		"""A tracked item's verdict must say which units it covers.

		Serialized items record the sampled serials, batched items the batch.
		Each Quantity / bundle-decided inspections are exempt: their identity
		lives per unit in the reading bundle and on the Quality Control Lot.
		"""
		if not self.item_code:
			return

		bundle_decided = self.inspection_basis == "Each Quantity"
		item = frappe.get_cached_value(
			"Item", self.item_code, ["has_serial_no", "has_batch_no"], as_dict=True
		)
		if not bundle_decided and item.has_serial_no and not (self.serial_no or "").strip():
			frappe.throw(
				_(
					"Record the sampled Serial Nos before submission — {0} is serialized, and the "
					"verdict must say which units it covers."
				).format(frappe.bold(self.item_code)),
				title=_("Serial Nos Missing"),
			)
		# the bundle carries serials per unit but no batch: only a lot reference
		# (which holds the batch itself) exempts the batch requirement
		if bundle_decided and self.reference_type == "Quality Control Lot":
			return
		if item.has_batch_no and not self.batch_no and not self._referenced_row_awaits_batch():
			frappe.throw(
				_(
					"Record the Batch No before submission — {0} is batch-tracked, and the verdict "
					"must say which batch it covers."
				).format(frappe.bold(self.item_code)),
				title=_("Batch No Missing"),
			)

	def warn_unrecorded_readings(self):
		"""A heads-up on save: drafts may be incomplete, but submission will not be.

		Silent on creation — the dialog and the lot button create drafts with
		empty readings by design — and a toast on subsequent saves.
		"""
		if self.docstatus != 0 or self.is_new():
			return
		if self.manual_inspection or self.inspection_basis == "Each Quantity":
			return

		unrecorded = [
			reading
			for reading in self.readings
			if not reading.manual_inspection and not self.has_recorded_reading(reading)
		]
		if unrecorded:
			frappe.msgprint(
				_("{0} reading(s) not yet recorded — required before submission.").format(len(unrecorded)),
				indicator="orange",
				alert=True,
			)

	def validate_readings_recorded(self):
		"""The decision must rest on recorded readings.

		Draft saves leave unrecorded rows untouched, so without this gate an
		untouched row would pass on its default status. Manual inspections and
		manual rows are the inspector's explicit call and exempt; Each Quantity
		inspections and bundle-decided ones carry their readings in the bundle.
		"""
		if self.manual_inspection or self.inspection_basis == "Each Quantity":
			return

		if not self.readings:
			frappe.throw(
				_(
					"Add readings before submission, or check Manual Inspection to record a "
					"verdict-style decision."
				),
				title=_("Readings Missing"),
			)

		for reading in self.readings:
			if reading.manual_inspection:
				continue
			# formula rows included: a formula with no readings has nothing to evaluate
			if not self.has_recorded_reading(reading):
				frappe.throw(
					_("Row #{0}: Record a reading for {1} before submission.").format(
						reading.idx, frappe.bold(reading.specification)
					),
					title=_("Reading Missing"),
				)

	def validate_unit_readings_coverage(self):
		"""An Each Quantity inspection must cover exactly the stock it decides."""
		if self.inspection_basis != "Each Quantity":
			return

		# a manual inspection's verdict overrides the per-unit machinery
		if self.manual_inspection:
			return

		inspected_qty = self.get_qty_under_inspection()
		if self.reference_type == "Quality Control Lot":
			# the lot may be decided in parts — but never beyond what is undecided
			if inspected_qty is not None and flt(self.unit_quantity) > flt(inspected_qty):
				frappe.throw(
					_(
						"The unit readings inspect {0} unit(s), but only {1} remain undecided on "
						"the Quality Control Lot."
					).format(self.unit_quantity, inspected_qty),
					title=_("More Units Than Undecided"),
				)
		elif inspected_qty and flt(self.unit_quantity) != flt(inspected_qty):
			frappe.throw(
				_(
					"The unit readings inspect {0} unit(s), but {1} are under inspection. Every "
					"unit needs its own readings on an Each Quantity basis."
				).format(self.unit_quantity, inspected_qty),
				title=_("Incomplete Per-Unit Readings"),
			)

	def validate_units(self):
		units = {entry.unit_no for entry in self.unit_readings}
		if units and (min(units) < 1 or max(units) > cint(self.unit_quantity)):
			frappe.throw(
				_("Unit numbers must lie between 1 and the unit quantity ({0}).").format(
					self.unit_quantity
				)
			)

	def evaluate_unit_entry_statuses(self):
		"""Derive each unit entry's status from its reading, like the sampled readings.

		Numeric readings pass inside [min, max]; non-numeric readings are compared
		case-insensitively against the acceptance criteria value. Entries without a
		reading keep their manually chosen status.
		"""
		for entry in self.unit_readings:
			reading = (entry.reading_value or "").strip()
			if not reading:
				continue

			if entry.numeric:
				passed = flt(entry.min_value) <= flt(reading) <= flt(entry.max_value)
			elif (entry.value or "").strip():
				passed = reading.casefold() == entry.value.strip().casefold()
			else:
				continue

			entry.status = "Accepted" if passed else "Rejected"

	def roll_up_unit_results(self):
		"""A unit is accepted only if every one of its readings is accepted."""
		rejected_units = {entry.unit_no for entry in self.unit_readings if entry.status == "Rejected"}
		inspected_units = {entry.unit_no for entry in self.unit_readings}

		self.rejected_unit_quantity = len(rejected_units)
		self.accepted_unit_quantity = len(inspected_units - rejected_units)

	def get_unit_serials(self, status):
		"""Serial numbers of units whose roll-up matches the status.

		A unit is rejected if any of its readings rejected. Units without a
		recorded serial are skipped — quantity accounting covers them.
		"""
		rejected_units = {entry.unit_no for entry in self.unit_readings if entry.status == "Rejected"}
		serial_by_unit = {}
		for entry in self.unit_readings:
			if entry.serial_no:
				serial_by_unit.setdefault(entry.unit_no, entry.serial_no)

		if status == "Accepted":
			units = set(serial_by_unit) - rejected_units
		else:
			units = set(serial_by_unit) & rejected_units
		return sorted(serial_by_unit[unit] for unit in units)

	def validate_unit_readings_complete(self):
		"""An Each Quantity inspection means every unit was actually inspected.

		On submission every declared unit must have readings, and every entry
		must carry one — otherwise untouched rows would pass on their default
		status without anyone having looked at the unit.
		"""
		if self.inspection_basis != "Each Quantity" or self.manual_inspection:
			return

		if not self.unit_readings:
			frappe.throw(
				_(
					"This inspection is on an Each Quantity basis: every unit needs its own "
					"readings. Use Populate Units to build the grid, or check Manual Inspection "
					"to record an overriding verdict."
				),
				title=_("Per-Unit Readings Required"),
			)

		self._validate_unit_serials()
		inspected_units = {entry.unit_no for entry in self.unit_readings}
		missing_units = sorted(set(range(1, cint(self.unit_quantity) + 1)) - inspected_units)
		if missing_units:
			frappe.throw(
				_("Unit(s) {0} have no readings. Every unit must be inspected before submission.").format(
					frappe.bold(", ".join(map(str, missing_units)))
				),
				title=_("Units Not Inspected"),
			)

		for entry in self.unit_readings:
			if not (entry.reading_value or "").strip():
				frappe.throw(
					_("Row #{0}: Record a reading for unit {1} ({2}) before submission.").format(
						entry.idx, entry.unit_no, entry.specification
					),
					title=_("Reading Missing"),
				)

	def _validate_unit_serials(self):
		"""Lot-flow unit readings of serialized items must name every unit's serial.

		Without them the release falls back to picking units by age instead of
		by verdict. Row-referenced inspections are exempt — inward serials may
		not exist before the document submits.
		"""
		if not self.item_code or not frappe.get_cached_value("Item", self.item_code, "has_serial_no"):
			return
		if self.reference_type != "Quality Control Lot":
			return

		units_without_serial = sorted(
			{entry.unit_no for entry in self.unit_readings if not entry.serial_no}
			- {entry.unit_no for entry in self.unit_readings if entry.serial_no}
		)
		if units_without_serial:
			frappe.throw(
				_("Unit(s) {0} have no Serial No — every unit of a serialized item must be identified.").format(
					frappe.bold(", ".join(map(str, units_without_serial)))
				),
				title=_("Unit Serials Missing"),
			)

		unit_serials = {}
		for entry in self.unit_readings:
			if entry.serial_no and unit_serials.setdefault(entry.unit_no, entry.serial_no) != entry.serial_no:
				frappe.throw(
					_("Unit {0} carries two different serials.").format(frappe.bold(entry.unit_no))
				)
		if len(set(unit_serials.values())) != len(unit_serials):
			frappe.throw(_("The same Serial No is recorded against more than one unit."))

	@frappe.whitelist()
	def populate_units(self):
		"""Generate one unit reading row per unit and template parameter."""
		parameters = get_template_details(self.quality_inspection_template)
		if not parameters:
			frappe.throw(_("Select a Quality Inspection Template with parameters first."))

		if not cint(self.unit_quantity):
			self.unit_quantity = cint(self.get_qty_under_inspection() or 0)
		if not cint(self.unit_quantity):
			frappe.throw(_("Set the Unit Quantity first."))

		unit_serials = self._get_unit_serials_for_population()
		self.set("unit_readings", [])
		for unit_no in range(1, cint(self.unit_quantity) + 1):
			for parameter in parameters:
				self.append(
					"unit_readings",
					{
						"unit_no": unit_no,
						"serial_no": unit_serials.get(unit_no),
						"specification": parameter.specification,
						"numeric": parameter.numeric,
						"value": parameter.value,
						"min_value": parameter.min_value,
						"max_value": parameter.max_value,
						"status": "Accepted",
					},
				)
		self.roll_up_unit_results()

	def _get_unit_serials_for_population(self):
		"""Map units to serials when the stock under inspection names them.

		Lot flow: the serials that arrived through the lot's source document and
		still sit in its Quality Control warehouse. Row flow: the referenced
		row's serials. Only an unambiguous one-serial-per-unit match prefills.
		"""
		from erpnext.stock.services.quality_trigger_resolution import get_row_serial_nos

		if not self.item_code or not frappe.get_cached_value("Item", self.item_code, "has_serial_no"):
			return {}

		serials = []
		if self.reference_type == "Quality Control Lot" and self.reference_name:
			lot = frappe.db.get_value(
				"Quality Control Lot",
				self.reference_name,
				["item_code", "batch_no", "quality_warehouse", "source_document_type", "source_document"],
				as_dict=True,
			)
			if lot and lot.source_document_type and lot.source_document:
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
				for serial in members:
					info = frappe.db.get_value(
						"Serial No", serial, ["warehouse", "batch_no"], as_dict=True
					)
					if not info or info.warehouse != lot.quality_warehouse:
						continue
					# a per-batch lot covers only its own batch's serials
					if lot.batch_no and info.batch_no and info.batch_no != lot.batch_no:
						continue
					serials.append(serial)
				serials.sort()
		elif self.child_row_reference:
			child_doctype = (
				"Stock Entry Detail"
				if self.reference_type == "Stock Entry"
				else self.reference_type + " Item"
			)
			row = frappe.db.get_value(
				child_doctype,
				self.child_row_reference,
				["serial_no", "serial_and_batch_bundle"],
				as_dict=True,
			)
			if row:
				serials = sorted(get_row_serial_nos(row))

		if len(serials) != cint(self.unit_quantity):
			return {}
		return {unit_no: serial for unit_no, serial in enumerate(serials, start=1)}

	def _validate_links(self):
		# frappe validates links before validate() runs, so the waiver must
		# intercept here rather than set a flag from validate
		if self._unborn_unit_serials_vouched_by_referenced_row():
			return
		super()._validate_links()

	def _unborn_unit_serials_vouched_by_referenced_row(self):
		"""Whether every unborn unit-reading serial is one the inspected document will create.

		An inward document inspected before submission (Block / Warn) types its
		serials on the row; they exist nowhere else yet. Unit readings may name
		them — the per-unit verdicts are exactly what the accepted/rejected
		split needs — so when every unborn serial is vouched for by the
		referenced row's typed serials, link validation stands down.
		"""
		unborn = {
			entry.serial_no
			for entry in self.get("unit_readings") or []
			if entry.serial_no and not frappe.db.exists("Serial No", entry.serial_no)
		}
		if not unborn:
			return False

		if self.reference_type == "Quality Control Lot" or not self.child_row_reference:
			return False

		from erpnext.stock.services.quality_trigger_resolution import get_row_serial_nos

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		row = frappe.db.get_value(
			child_doctype,
			self.child_row_reference,
			["serial_no", "serial_and_batch_bundle"],
			as_dict=True,
		)
		return bool(row) and not (unborn - set(get_row_serial_nos(row)))

	@frappe.whitelist()
	def get_qty_under_inspection(self):
		if self.reference_type == "Quality Control Lot" and self.reference_name:
			# inspections may decide the lot in parts: what remains to inspect
			# is what no submitted inspection has decided yet
			lot = frappe.db.get_value(
				"Quality Control Lot", self.reference_name, ["received_qty", "decided_qty"], as_dict=True
			)
			return flt(lot.received_qty) - flt(lot.decided_qty)

		if self.child_row_reference:
			child_doctype = (
				"Stock Entry Detail"
				if self.reference_type == "Stock Entry"
				else self.reference_type + " Item"
			)
			# returns carry negative quantities; inspection thinks in physical units
			return abs(flt(frappe.db.get_value(child_doctype, self.child_row_reference, "qty")))

		return None

	@frappe.whitelist()
	def get_item_specification_details(self):
		if not self.quality_inspection_template:
			return

		self.set("readings", [])
		parameters = get_template_details(self.quality_inspection_template)
		for d in parameters:
			child = self.append("readings", {})
			child.update(d)
			child.status = "Accepted"
			child.parameter_group = frappe.get_value(
				"Quality Inspection Parameter", d.specification, "parameter_group"
			)

	@frappe.whitelist()
	def get_quality_inspection_template(self):
		template = ""
		if self.bom_no:
			template = frappe.db.get_value("BOM", self.bom_no, "quality_inspection_template")

		if not template:
			template = frappe.db.get_value("BOM", self.item_code, "quality_inspection_template")

		self.quality_inspection_template = template
		self.get_item_specification_details()

	def on_update(self):
		self.update_qc_reference()

	def on_submit(self):
		self.update_qc_reference()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Serial and Batch Bundle",)
		self.update_qc_reference()

	def on_trash(self):
		self.update_qc_reference(remove_reference=True)

	def validate_readings_status_mandatory(self):
		for reading in self.readings:
			if not reading.status:
				frappe.throw(_("Row #{0}: Status is mandatory").format(reading.idx))

	def update_qc_reference(self, remove_reference=False):
		quality_inspection = self.name if self.docstatus < 2 and not remove_reference else ""

		if self.reference_type == "Quality Control Lot":
			if self.reference_name:
				if not quality_inspection:
					# fall back to the latest remaining verdict of the lot
					quality_inspection = (
						frappe.db.get_value(
							"Quality Inspection",
							{
								"reference_type": "Quality Control Lot",
								"reference_name": self.reference_name,
								"docstatus": 1,
								"name": ("!=", self.name),
							},
							"name",
							order_by="modified desc",
						)
						or ""
					)
				frappe.db.set_value(
					"Quality Control Lot", self.reference_name, "quality_inspection", quality_inspection
				)
			return

		if self.reference_type == "Job Card":
			if self.reference_name:
				ref = frappe.qb.DocType(self.reference_type)
				(
					frappe.qb.update(ref)
					.set(ref.quality_inspection, quality_inspection)
					.set(ref.modified, self.modified)
					.where((ref.name == self.reference_name) & (ref.production_item == self.item_code))
				).run()

		else:
			doctype = self.reference_type + " Item"

			if self.reference_type == "Stock Entry":
				doctype = "Stock Entry Detail"

			if doctype and self.reference_name:
				child_doc = frappe.qb.DocType(doctype)

				query = (
					frappe.qb.update(child_doc)
					.set(child_doc.quality_inspection, quality_inspection)
					.where(
						(child_doc.parent == self.reference_name) & (child_doc.item_code == self.item_code)
					)
				)

				if self.batch_no and self.docstatus < 2:
					query = query.where(child_doc.batch_no == self.batch_no)

				if self.docstatus == 2:  # if cancel, then remove qi link wherever same name
					query = query.where(child_doc.quality_inspection == self.name)

				if self.child_row_reference:
					query = query.where(child_doc.name == self.child_row_reference)

				query.run()

				frappe.db.set_value(
					self.reference_type,
					self.reference_name,
					"modified",
					self.modified,
				)

		if self.reference_type and self.reference_name:
			frappe.get_lazy_doc(self.reference_type, self.reference_name).notify_update()

	def inspect_and_set_status(self):
		for reading in self.readings:
			if not reading.manual_inspection:  # dont auto set status if manual
				if reading.formula_based_criteria:
					self.set_status_based_on_acceptance_formula(reading)
				else:
					# if not formula based check acceptance values set
					self.set_status_based_on_acceptance_values(reading)

		if not self.manual_inspection:
			self.status = "Accepted"
			for reading in self.readings:
				if reading.status == "Rejected":
					self.status = "Rejected"
					frappe.msgprint(
						_("Status set to rejected as there are one or more rejected readings."), alert=True
					)
					break

	def validate_reading_number_format(self):
		"""Reject newly entered readings that are not numbers in the user's format.

		They would otherwise be misread rather than refused, silently rejecting an
		inspection whose readings are in fact within the acceptance range. Readings
		already stored are left alone, so a document entered by a user in one locale
		stays saveable and submittable by a user in another."""
		number_format = get_reading_number_format()
		decimal_str, comma_str = get_reading_separators(number_format)
		before_save = self.get_doc_before_save()

		for reading in self.readings:
			if not cint(reading.numeric) or cint(reading.manual_inspection):
				continue

			stored = before_save and before_save.get("readings", {"name": reading.name})
			stored = stored[0] if stored else None

			for i in range(1, 11):
				field = "reading_" + str(i)
				value = reading.get(field)
				if value is None or not value.strip():
					continue

				if stored and stored.get(field) == value:
					continue

				if parse_reading(value, decimal_str, comma_str) is None:
					frappe.throw(
						_(
							"Row #{0}: Reading {1} {2} is not a valid number in the {3} number format. Use {4} as the decimal separator."
						).format(
							reading.idx,
							i,
							frappe.bold(value),
							frappe.bold(number_format.string),
							frappe.bold(decimal_str),
						),
						title=_("Invalid Reading"),
					)

	def set_status_based_on_acceptance_values(self, reading):
		# an unrecorded reading is a draft in progress, not a failure: leave its
		# status alone — submission separately demands that readings be recorded
		if not self.has_recorded_reading(reading):
			return

		if not cint(reading.numeric):
			# compare case-insensitively and ignore surrounding whitespace, so a
			# reading of "yes" passes an acceptance criteria of "Yes"
			reading_value = (reading.get("reading_value") or "").strip().casefold()
			value = (reading.get("value") or "").strip().casefold()
			result = reading_value == value
		else:
			# numeric readings
			result = self.min_max_criteria_passed(reading)

		reading.status = "Accepted" if result else "Rejected"

	@staticmethod
	def has_recorded_reading(reading):
		if not cint(reading.numeric):
			return bool((reading.get("reading_value") or "").strip())
		return any((reading.get(f"reading_{i}") or "").strip() for i in range(1, 11))

	def min_max_criteria_passed(self, reading):
		"""Determine whether all readings fall in the acceptable range."""
		has_reading = False
		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			if reading_value is not None and reading_value.strip():
				has_reading = True
				result = (
					flt(reading.get("min_value"))
					<= parse_float(reading_value)
					<= flt(reading.get("max_value"))
				)
				if not result:
					return False
		return has_reading

	def set_status_based_on_acceptance_formula(self, reading):
		if not reading.acceptance_formula:
			frappe.throw(
				_("Row #{0}: Acceptance Criteria Formula is required.").format(reading.idx),
				title=_("Missing Formula"),
			)

		condition = reading.acceptance_formula
		data = self.get_formula_evaluation_data(reading)

		try:
			result = frappe.safe_eval(condition, None, data)
			reading.status = "Accepted" if result else "Rejected"
		except NameError as e:
			field = frappe.bold(e.args[0].split()[1])
			frappe.throw(
				_(
					"Row #{0}: {1} is not a valid reading field. Please refer to the field description."
				).format(reading.idx, field),
				title=_("Invalid Formula"),
			)
		except Exception:
			frappe.throw(
				_("Row #{0}: Acceptance Criteria Formula is incorrect.").format(reading.idx),
				title=_("Invalid Formula"),
			)

	def get_formula_evaluation_data(self, reading):
		data = {}
		if not cint(reading.numeric):
			data = {"reading_value": reading.get("reading_value")}
		else:
			# numeric readings
			for i in range(1, 11):
				field = "reading_" + str(i)
				if reading.get(field) is None:
					data[field] = 0.0
					continue

				data[field] = parse_float(reading.get(field))
			data["mean"] = self.calculate_mean(reading)

		return data

	def calculate_mean(self, reading):
		"""Calculate mean of all non-empty readings."""
		from statistics import mean

		readings_list = []

		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			if reading_value is not None and reading_value.strip():
				readings_list.append(parse_float(reading_value))

		actual_mean = mean(readings_list) if readings_list else 0
		return actual_mean


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype: Any, txt: str | None, searchfield: Any, start: int, page_len: int, filters: dict):
	reference_doctype = filters.get("reference_doctype")

	if not reference_doctype:
		return []
	elif reference_doctype == "Job Card":
		production_item, item_name = frappe.get_value(
			"Job Card", filters.get("reference_name"), ["production_item", "item_name"]
		)
		return ((production_item, item_name),)
	elif reference_doctype == "Quality Control Lot":
		# a lot quarantines exactly one item; it has no items child table
		item_code = frappe.get_value("Quality Control Lot", filters.get("reference_name"), "item_code")
		if not item_code:
			return []
		return ((item_code, frappe.get_cached_value("Item", item_code, "item_name")),)
	else:
		# every item on the reference document is inspectable — already-linked
		# rows can carry further ad-hoc inspections, and the row link plus the
		# consistency gates do the bookkeeping
		my_filters = [
			["items.parent", "=", filters.get("reference_name")],
			"and",
			["items.item_code", "like", f"%{txt}%"],
			"and",
			["docstatus", "<", 2],
		]

		query = frappe.get_query(
			reference_doctype,
			fields=["items.item_code, items.item_name"],
			filters=my_filters,
			offset=start,
			limit=page_len,
			ignore_permissions=False,
			distinct=True,
		)
		# frappe's db_query drops ORDER BY for a distinct query on Postgres, which (with offset/limit)
		# changes both the order and the page contents vs MariaDB. Appending the order to the built
		# query instead keeps it -- item_code is in the DISTINCT select, so it is valid on Postgres.
		items_field = frappe.get_meta(reference_doctype).get_field("items")
		if items_field:
			child = frappe.qb.DocType(items_field.options)
			query = query.orderby(child.item_code)
		return query.run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def quality_inspection_query(
	doctype: Any, txt: str | None, searchfield: Any, start: int, page_len: int, filters: dict
):
	return frappe.get_all(
		"Quality Inspection",
		limit_start=start,
		limit_page_length=page_len,
		filters={
			"docstatus": ("<", 2),
			"name": ("like", "%%%s%%" % txt),
			"item_code": filters.get("item_code"),
			"reference_name": ("in", [filters.get("reference_name", ""), ""]),
			"child_row_reference": ("in", [filters.get("child_row_reference", ""), ""]),
		},
		as_list=1,
	)


@frappe.whitelist()
def make_quality_inspection(source_name: str, target_doc: str | dict | Document | None = None):
	def postprocess(source, doc):
		doc.inspected_by = frappe.session.user
		doc.get_quality_inspection_template()

	doc = get_mapped_doc(
		"BOM",
		source_name,
		{
			"BOM": {
				"doctype": "Quality Inspection",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {"name": "bom_no", "item": "item_code", "stock_uom": "uom", "stock_qty": "qty"},
			}
		},
		target_doc,
		postprocess,
	)

	return doc


def get_reading_number_format() -> NumberFormat:
	"""Number format the user enters readings in.

	User defaults fall back to the global default, so this is the same format the
	user's desk formats numbers with."""
	number_format = frappe.defaults.get_user_default("number_format")
	if number_format not in NUMBER_FORMAT_MAP:
		number_format = "#,###.##"

	return NumberFormat.from_string(number_format)


def get_reading_separators(number_format: NumberFormat) -> tuple[str, str]:
	"""Decimal and thousands separator a reading may be written with.

	A format with no decimal separator still has to accept decimal readings, so it
	falls back to a dot and gives up any grouping that would collide with it."""
	decimal_str = number_format.decimal_separator or "."
	comma_str = number_format.thousands_separator

	return decimal_str, "" if comma_str == decimal_str else comma_str


def parse_reading(value: str, decimal_str: str, comma_str: str) -> float | None:
	"""Reading as a float, or None when it is not a number in that format."""
	value = value.strip()
	integer_part = value.partition(decimal_str)[0]

	if comma_str and comma_str in integer_part:
		groups = integer_part.split(comma_str)
		lead = groups[0][1:] if groups[0][:1] in ("+", "-") else groups[0]
		if not 1 <= len(lead) <= 3 or len(groups[-1]) != 3:
			return None

		if any(len(group) not in (2, 3) for group in groups[1:-1]):
			return None

		value = value.replace(comma_str, "")

	if decimal_str != ".":
		value = value.replace(decimal_str, ".")

	try:
		number = float(value)
	except ValueError:
		return None

	return number if isfinite(number) else None


def parse_float(num: str) -> float:
	"""Since reading_# fields are `Data` field they might contain number which
	is representation in user's prefered number format instead of machine
	readable format. This function converts them to machine readable format."""

	decimal_str, comma_str = get_reading_separators(get_reading_number_format())

	return flt(parse_reading(num, decimal_str, comma_str))
