# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from math import isfinite
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, formatdate, get_link_to_form, get_number_format_info, getdate
from frappe.utils.number_format import NUMBER_FORMAT_MAP, NumberFormat

from erpnext.stock.doctype.quality_inspection.unit_readings import UnitReadingsMixin
from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)


class QualityInspection(UnitReadingsMixin, Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.quality_inspection_reading.quality_inspection_reading import (
			QualityInspectionReading,
		)
		from erpnext.stock.doctype.quality_inspection_reading_entry.quality_inspection_reading_entry import (
			QualityInspectionReadingEntry,
		)

		amended_from: DF.Link | None
		batch_no: DF.Link | None
		child_row_reference: DF.Data | None
		company: DF.Link | None
		description: DF.SmallText | None
		inspected_by: DF.Link
		inspection_basis: DF.Literal["", "Sample", "Each Quantity"]
		inspection_type: DF.Literal["", "Incoming", "Outgoing", "In Process"]
		item_code: DF.Link
		item_name: DF.Data | None
		serial_no: DF.SmallText | None
		stock_uom: DF.Link | None
		letter_head: DF.Link | None
		manual_inspection: DF.Check
		naming_series: DF.Literal["MAT-QA-.YYYY.-"]
		quality_inspection_template: DF.Link | None
		readings: DF.Table[QualityInspectionReading]
		reference_name: DF.DynamicLink
		reference_type: DF.Literal[
			"",
			"Purchase Receipt",
			"Goods Inward Note",
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
		status: DF.Literal["Accepted", "Partially Accepted", "Rejected"]
		verified_by: DF.Data | None

	# end: auto-generated types
	def on_discard(self):
		self.update_qc_reference()

	def before_validate(self):
		self.clear_unborn_identity()

	def clear_unborn_identity(self):
		"""A transaction row still without identity gets it at submission.

		Whatever the inspection names now cannot be that future identity — a
		typed batch or serial would only contradict the materialised row later.
		Lots hold their identity and custody records the supplier's, so both
		keep what is recorded.
		"""
		if not self.reference_type or self.reference_type in ("Quality Control Lot", "Goods Inward Note"):
			return
		if not self.batch_no and not (self.serial_no or "").strip():
			return

		self.set_child_row_reference()
		if not self.child_row_reference:
			return

		from erpnext.stock.services.quality_trigger_resolution import (
			get_reference_row_tracking,
			get_row_batch_nos,
			get_row_serial_nos,
		)

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		row = get_reference_row_tracking(child_doctype, self.child_row_reference)
		if not get_row_batch_nos(row):
			self.batch_no = None
		if not get_row_serial_nos(row):
			self.serial_no = None

	@frappe.whitelist()
	def get_reference_row_identity(self):
		"""What the referenced transaction row carries — drives the form's field toggles."""
		if self.reference_type in ("Quality Control Lot", "Goods Inward Note"):
			return None
		self.set_child_row_reference()
		if not self.child_row_reference:
			return None

		from erpnext.stock.services.quality_trigger_resolution import (
			get_reference_row_tracking,
			get_row_batch_nos,
			get_row_serial_nos,
		)

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		row = get_reference_row_tracking(child_doctype, self.child_row_reference)
		return {
			"has_batch": bool(get_row_batch_nos(row)),
			"has_serials": bool(get_row_serial_nos(row)),
		}

	def validate(self):
		self.set_inspection_basis_from_lot()
		self.set_batch_from_lot()
		# the reference must be resolved before the unit machinery runs: the
		# quantity under inspection comes off the referenced row or lot
		self.validate_item_belongs_to_reference()
		self.set_child_row_reference()

		if self.inspection_basis == "Each Quantity":
			# per-unit readings live in the unit readings table; rows lurking in
			# the hidden readings table would invisibly block submission
			self.set("readings", [])
			self.assign_unit_numbers_from_serials()
			if not cint(self.unit_quantity):
				self.unit_quantity = self._whole_quantity_under_inspection()
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
		self.validate_serial_nos()
		# named identity must describe the reference from the first save, not
		# only when the verdict lands
		self.validate_inspected_serials_against_reference()
		self.validate_inspected_batch_against_reference()
		# a sample larger than the stock it describes is wrong on a draft too
		self.validate_sample_within_quantity()
		self.validate_decision_follows_quarantine()
		self.validate_manual_status()
		self.set_company()

		# creation lands the draft even when its prefills disagree or its
		# readings are still empty (the dialog and the lot button create drafts
		# to be filled in); every save after that enforces what submission will
		if not self.is_new():
			self.validate_readings_status_mandatory()
			self.validate_readings_recorded()
			self.validate_serials_recorded()
			self.validate_sample_size()
			self.validate_unit_readings_complete()
			self.validate_unit_readings_coverage()
			self.validate_decided_quantity()
			self.validate_units_not_already_decided()

	def validate_manual_status(self):
		"""A hand-set verdict decides the whole quantity, so it is one or the other.

		Partially Accepted is the roll-up of a per-unit inspection and Cancelled is
		stamped when the inspection is discarded; neither describes what a person
		is deciding here. Both matter because the booking reads only "Rejected" and
		treats everything else as a full acceptance — so either would quietly
		release the lot entire.
		"""
		if not self.manual_inspection or self.status in ("Accepted", "Rejected"):
			return

		frappe.throw(
			_("A manual inspection is Accepted or Rejected — {0} is not a verdict to set by hand.").format(
				frappe.bold(_(self.status))
			),
			title=_("Invalid Manual Verdict"),
		)

	def validate_decision_follows_quarantine(self):
		"""A verdict cannot be dated before the stock it decides was quarantined."""
		if self.reference_type != "Quality Control Lot" or not self.reference_name:
			return

		quarantined_on = frappe.db.get_value(
			"Quality Control Lot", self.reference_name, "source_posting_datetime"
		)
		if not quarantined_on or not self.report_date:
			return

		if getdate(self.report_date) < getdate(quarantined_on):
			frappe.throw(
				_("Report Date {0} precedes the day Quality Control Lot {1} was quarantined ({2}).").format(
					frappe.bold(formatdate(self.report_date)),
					get_link_to_form("Quality Control Lot", self.reference_name),
					frappe.bold(formatdate(quarantined_on)),
				),
				title=_("Verdict Precedes Quarantine"),
			)

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
						get_link_to_form("Quality Control Lot", self.reference_name),
						get_link_to_form("Item", lot_item),
						get_link_to_form("Item", self.item_code),
					),
					title=_("Item Not On Reference"),
				)
			return

		if self.reference_type == "Job Card":
			production_item = frappe.db.get_value("Job Card", self.reference_name, "production_item")
			if production_item and production_item != self.item_code:
				frappe.throw(
					_("Job Card {0} produces item {1}, not {2}.").format(
						get_link_to_form("Job Card", self.reference_name),
						get_link_to_form("Item", production_item),
						get_link_to_form("Item", self.item_code),
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
					get_link_to_form("Item", self.item_code),
					_(self.reference_type),
					get_link_to_form(self.reference_type, self.reference_name),
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

		if self.reference_type == "Goods Inward Note":
			# a custody row may be inspected in batches: bind to the first row of
			# this item that still has undecided units in custody, past
			# inspections notwithstanding
			from erpnext.stock.doctype.goods_inward_note.goods_inward_note import get_custody_verdicts

			rows = frappe.get_all(
				doctype,
				filters={
					"parent": self.reference_name,
					"item_code": self.item_code,
					"docstatus": ("<", 2),
				},
				fields=["name", "stock_qty", "received_qty", "conversion_factor"],
				order_by="idx",
			)
			for row in rows:
				conversion = flt(row.conversion_factor) or 1
				in_custody = flt(row.stock_qty) - flt(row.received_qty) * conversion
				undecided = (
					flt(row.stock_qty) - get_custody_verdicts(row.name, exclude_inspection=self.name).decided
				)
				if min(in_custody, undecided) > 0:
					self.child_row_reference = row.name
					return
			if rows:
				# nothing left to inspect: bind anyway so the quantity resolves
				# to zero and submission is refused, instead of slipping the cap
				self.child_row_reference = rows[0].name
			return

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
			return

		# every row of this item already carries a verdict — a further one (say,
		# for another batch on the same row) binds the first row all the same
		fallback = frappe.get_all(
			doctype,
			filters={"parent": self.reference_name, "item_code": self.item_code, "docstatus": ("<", 2)},
			order_by="idx",
			limit=1,
			pluck="name",
		)
		if fallback:
			self.child_row_reference = fallback[0]

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

	def set_batch_from_lot(self):
		"""The lot holds the batch; a lot-referenced inspection mirrors it."""
		if self.reference_type == "Quality Control Lot" and self.reference_name:
			self.batch_no = frappe.db.get_value("Quality Control Lot", self.reference_name, "batch_no")

	def validate_serials_recorded(self):
		"""A serialized sample names the units it took — proof one was taken.

		Each Quantity is exempt: its identity lives per unit, where the unit
		machinery makes its own demands and a manual override stands on the
		inspector. Custody precedes stock identity and stays exempt, and a
		transaction row whose serials are born at submission has nothing to
		name yet (its field is cleared).
		"""
		if self.inspection_basis == "Each Quantity":
			return
		if not self.item_code or self.reference_type == "Goods Inward Note":
			return
		if not frappe.get_cached_value("Item", self.item_code, "has_serial_no"):
			return

		if self.reference_type != "Quality Control Lot":
			from erpnext.stock.services.quality_trigger_resolution import (
				get_reference_row_tracking,
				get_row_serial_nos,
			)

			if not self.child_row_reference:
				return
			child_doctype = (
				"Stock Entry Detail"
				if self.reference_type == "Stock Entry"
				else self.reference_type + " Item"
			)
			if not get_row_serial_nos(get_reference_row_tracking(child_doctype, self.child_row_reference)):
				return

		named = (self.serial_no or "").strip() or any(entry.serial_no for entry in self.get("unit_readings"))
		if not named:
			frappe.throw(
				_(
					"Record the sampled Serial Nos — {0} is serialized, and the verdict must "
					"show which units were actually taken."
				).format(get_link_to_form("Item", self.item_code)),
				title=_("Serial Nos Missing"),
			)

	@frappe.whitelist()
	def validate_serial_nos(self):
		"""The recorded serials must be real and the item's; they set the sample size.

		Each Quantity inspections record serials per unit in the unit readings,
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
				if self.reference_type == "Goods Inward Note":
					# custody precedes stock identity: the supplier's printed
					# serials exist on paper only until a receipt creates them
					continue
				frappe.throw(_("Serial No {0} does not exist.").format(frappe.bold(serial)))
			if info.item_code != self.item_code:
				frappe.throw(
					_("Serial No {0} belongs to item {1}, not {2}.").format(
						get_link_to_form("Serial No", serial),
						get_link_to_form("Item", info.item_code),
						get_link_to_form("Item", self.item_code),
					)
				)
			# both-tracked items: the serial's own batch is the truth the named
			# batch must agree with
			if self.batch_no and info.batch_no and info.batch_no != self.batch_no:
				frappe.throw(
					_("Serial No {0} belongs to batch {1}, not {2}.").format(
						get_link_to_form("Serial No", serial),
						get_link_to_form("Batch", info.batch_no),
						get_link_to_form("Batch", self.batch_no),
					),
					title=_("Serial and Batch Disagree"),
				)

		if serial_nos:
			self.sample_size = len(serial_nos)

	def _referenced_row_typed_serials(self):
		"""Serials typed on the referenced row — acceptable before they exist."""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if not self.child_row_reference or self.reference_type == "Quality Control Lot":
			return set()

		child_doctype = (
			"Stock Entry Detail" if self.reference_type == "Stock Entry" else self.reference_type + " Item"
		)
		from erpnext.stock.services.quality_trigger_resolution import get_reference_row_tracking

		typed = get_reference_row_tracking(child_doctype, self.child_row_reference).get("serial_no")
		return set(get_serial_nos(typed or ""))

	def validate_sample_size(self):
		"""A Sample inspection of zero units is a verdict about nothing.

		Creation-exempt: a fresh draft may carry no sample yet (the dialog and
		the lot button create drafts to be filled in). A manual verdict needs no
		counted sample. The sample-vs-quantity ceiling is a current-state check and runs
		on every save in validate_sample_within_quantity.
		"""
		if self.inspection_basis == "Each Quantity" or self.manual_inspection:
			return
		if flt(self.sample_size) <= 0:
			frappe.throw(
				_("A Sample inspection must inspect at least one unit — set the Sample Size."),
				title=_("Sample Size Missing"),
			)

	def validate_sample_within_quantity(self):
		"""A sample cannot be larger than the stock it claims to describe."""
		if self.inspection_basis == "Each Quantity" or flt(self.sample_size) <= 0:
			return

		qty_under_inspection = self.get_qty_under_inspection()
		if qty_under_inspection is None:
			return
		# custody rows resolve to zero once fully decided or departed — a sample
		# against nothing must be refused, not waved past the cap
		strict = self.reference_type == "Goods Inward Note"
		if (strict or flt(qty_under_inspection) > 0) and flt(self.sample_size) > flt(qty_under_inspection):
			frappe.throw(
				_("The sample of {0} unit(s) exceeds the {1} unit(s) under inspection.").format(
					self.sample_size, flt(qty_under_inspection)
				),
				title=_("Sample Larger Than Quantity"),
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
						get_link_to_form("Quality Control Lot", self.reference_name),
						get_link_to_form("Batch", lot_batch),
						get_link_to_form("Batch", self.batch_no),
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
				).format(get_link_to_form("Batch", self.batch_no)),
				title=_("Inspected Batch Mismatch"),
			)

	def validate_inspected_serials_against_reference(self):
		"""The inspected serials must belong to the stock under inspection.

		Lot-referenced inspections check against the serials that arrived through
		the lot's source document (falling back to "currently held in the lot's
		Quality Control warehouse"); transaction-referenced ones check against the
		referenced row when it already carries serials — the document-side gate at
		its submission is the authority there either way. Covers the sampled
		Serial Nos and the per-unit serials alike.
		"""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		from erpnext.stock.services.quality_trigger_resolution import get_row_serial_nos

		inspected = set(get_serial_nos(self.serial_no)) if (self.serial_no or "").strip() else set()
		inspected.update(entry.serial_no for entry in self.get("unit_readings") if entry.serial_no)
		if not inspected:
			return

		if self.reference_type == "Quality Control Lot" and self.reference_name:
			from erpnext.stock.services.quality_quarantine import get_lot_serial_members

			lot = frappe.db.get_value(
				"Quality Control Lot",
				self.reference_name,
				[
					"item_code",
					"quality_warehouse",
					"source_document_type",
					"source_document",
					"source_document_row",
				],
				as_dict=True,
			)

			members = get_lot_serial_members(lot)

			if members:
				missing = inspected - members
				if missing:
					frappe.throw(
						_(
							"Serial number(s) {0} did not arrive through {1}, the source of "
							"Quality Control Lot {2} — only the lot's own units can be inspected."
						).format(
							frappe.bold(", ".join(sorted(missing))),
							get_link_to_form(lot.source_document_type, lot.source_document),
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
							get_link_to_form("Warehouse", lot.quality_warehouse),
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
		from erpnext.stock.services.quality_trigger_resolution import get_reference_row_tracking

		row = get_reference_row_tracking(child_doctype, self.child_row_reference)
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
						reading.idx, get_link_to_form("Quality Inspection Parameter", reading.specification)
					),
					title=_("Reading Missing"),
				)

	@frappe.whitelist()
	def get_qty_under_inspection(self):
		# an unsaved form has no child row reference yet — resolve it the same
		# way saving would, so the quantity answers for the right row
		if not self.child_row_reference:
			self.set_child_row_reference()

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
			if self.reference_type == "Goods Inward Note":
				# only what still sits in custody, undecided, can be inspected —
				# received units became stock, and earlier batch inspections
				# keep their verdicts
				from erpnext.stock.doctype.goods_inward_note.goods_inward_note import (
					get_custody_verdicts,
				)

				row = frappe.db.get_value(
					child_doctype,
					self.child_row_reference,
					["stock_qty", "received_qty", "conversion_factor"],
					as_dict=True,
				)
				if not row:
					return None
				conversion = flt(row.conversion_factor) or 1
				in_custody = max(flt(row.stock_qty) - flt(row.received_qty) * conversion, 0)
				decided = get_custody_verdicts(self.child_row_reference, exclude_inspection=self.name).decided
				return min(in_custody, max(flt(row.stock_qty) - decided, 0))
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

	def on_update(self):
		self.update_qc_reference()

	def on_submit(self):
		from erpnext.stock.services.quality_release import process_inspection_result

		self.update_qc_reference()
		process_inspection_result(self)

	def before_cancel(self):
		self.protect_received_custody_verdict()

	def protect_received_custody_verdict(self):
		"""Units released into stock keep the verdict that released them.

		A receipt drawn from a Goods Inward Note stands on the custody
		verdicts; cancelling one from under it would leave received stock with
		no verdict behind it. Cancel the receipt first.
		"""
		if self.reference_type != "Goods Inward Note" or not self.child_row_reference:
			return

		from erpnext.stock.doctype.goods_inward_note.goods_inward_note import get_custody_verdicts

		row = frappe.db.get_value(
			"Goods Inward Note Item",
			self.child_row_reference,
			["stock_qty", "received_qty", "conversion_factor"],
			as_dict=True,
		)
		if not row or not flt(row.received_qty):
			return

		received_stock = flt(row.received_qty) * (flt(row.conversion_factor) or 1)
		decided_without = get_custody_verdicts(
			self.child_row_reference, exclude_inspection=self.name, row_qty=row.stock_qty
		).decided
		if flt(received_stock - decided_without, 6) > 0:
			frappe.throw(
				_(
					"{0} unit(s) of this custody row were already received on this verdict's "
					"strength. Cancel the receipt before cancelling the inspection."
				).format(received_stock),
				title=_("Verdict Already Acted On"),
			)

	def on_cancel(self):
		from erpnext.stock.services.quality_release import reverse_inspection_result

		self.ignore_linked_doctypes = ("Serial and Batch Bundle",)
		self.update_qc_reference()
		reverse_inspection_result(self)

	def on_trash(self):
		self.update_qc_reference(remove_reference=True)

	def validate_readings_status_mandatory(self):
		for reading in self.readings:
			if not reading.status:
				frappe.throw(_("Row #{0}: Status is mandatory").format(reading.idx))

	def update_qc_reference(self, remove_reference=False):
		quality_inspection = self.name if self.docstatus < 2 and not remove_reference else ""

		# lots and custody rows take several inspections each; theirs are found
		# by reference query, never through a single link field
		if self.reference_type in ("Quality Control Lot", "Goods Inward Note"):
			return

		if self.reference_type == "Job Card":
			if self.reference_name:
				job_card = frappe.qb.DocType("Job Card")
				(
					frappe.qb.update(job_card)
					.set(job_card.quality_inspection, quality_inspection)
					.set(job_card.modified, self.modified)
					.where(
						(job_card.name == self.reference_name) & (job_card.production_item == self.item_code)
					)
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

				# an unbound inspection falls back to the typed batch to find its
				# row — a bound one is already pinned, and bundle rows type none
				if (
					not self.child_row_reference
					and self.batch_no
					and self.docstatus < 2
					and frappe.get_meta(doctype).has_field("batch_no")
				):
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def readings_source_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None = None
):
	"""Inspections of stock that arrived on the same document as this one.

	Copying readings answers the several inspections one receipt produces, so
	the picker offers those siblings rather than every inspection of the item
	ever made.
	"""
	inspection = (filters or {}).get("inspection")
	if not inspection:
		return []

	current = frappe.db.get_value(
		"Quality Inspection", inspection, ["reference_type", "reference_name"], as_dict=True
	)
	if not current:
		return []

	source_type, source_name = _source_document_of(current.reference_type, current.reference_name)
	if not source_name:
		return []

	siblings = frappe.get_all(
		"Quality Control Lot",
		filters={"source_document_type": source_type, "source_document": source_name},
		pluck="name",
	)

	conditions = [
		["name", "!=", inspection],
		["inspection_basis", "!=", "Each Quantity"],
		["docstatus", "<", 2],
		["reference_name", "in", [*siblings, source_name]],
	]
	if txt:
		conditions.append(["name", "like", f"%{txt}%"])

	return frappe.get_all(
		"Quality Inspection",
		filters=conditions,
		fields=["name", "item_code", "reference_name"],
		order_by="creation desc",
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


def _source_document_of(reference_type: str, reference_name: str) -> tuple[str | None, str | None]:
	"""The transaction an inspection's stock arrived on, through its lot or directly."""
	if reference_type == "Quality Control Lot" and reference_name:
		lot = frappe.db.get_value(
			"Quality Control Lot",
			reference_name,
			["source_document_type", "source_document"],
			as_dict=True,
		)
		if lot:
			return lot.source_document_type, lot.source_document

	return reference_type, reference_name


@frappe.whitelist()
def get_readings_to_copy(source: str) -> list[dict]:
	"""The recorded readings of another inspection, to copy onto one being filled in.

	A document quarantining several lots is inspected once per lot, and where the
	same measurements answer for all of them the inspector would otherwise type
	them again per document. Carries the acceptance criteria alongside the values
	so an inspection with no template of its own has something to be judged
	against; the caller keeps its own criteria where it already has them. Status
	and the manual override never travel, so the copy reaches its own verdict
	when it saves.
	"""
	inspection = frappe.get_doc("Quality Inspection", source)
	inspection.check_permission("read")

	criteria = (
		"numeric",
		"value",
		"min_value",
		"max_value",
		"formula_based_criteria",
		"acceptance_formula",
	)

	return [
		{
			"specification": reading.specification,
			"reading_value": reading.reading_value,
			**{field: reading.get(field) for field in criteria},
			**{f"reading_{index}": reading.get(f"reading_{index}") for index in range(1, 11)},
		}
		for reading in inspection.readings
	]


def parse_float(num: str) -> float:
	"""Since reading_# fields are `Data` field they might contain number which
	is representation in user's prefered number format instead of machine
	readable format. This function converts them to machine readable format."""

	decimal_str, comma_str = get_reading_separators(get_reading_number_format())

	return flt(parse_reading(num, decimal_str, comma_str))
