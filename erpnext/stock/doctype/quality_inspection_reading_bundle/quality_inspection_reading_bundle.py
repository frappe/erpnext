# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Per-unit readings for "Each Quantity" inspections.

Mirrors the Serial and Batch Bundle pattern: a large repeating sub-structure
(units x parameters) lives in a separate document, referenced from the Quality
Inspection by a single link, instead of bloating the inspection itself. The
long/flat entries table holds one row per unit and parameter, which also
accommodates templates with any number of parameters.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class QualityInspectionReadingBundle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.quality_inspection_reading_entry.quality_inspection_reading_entry import (
			QualityInspectionReadingEntry,
		)

		accepted_qty: DF.Int
		amended_from: DF.Link | None
		entries: DF.Table[QualityInspectionReadingEntry]
		item_code: DF.Link
		quality_inspection: DF.Link | None
		quality_inspection_template: DF.Link | None
		quantity: DF.Int
		rejected_qty: DF.Int
	# end: auto-generated types

	def validate(self):
		self.validate_units()
		self.evaluate_entry_statuses()
		self.roll_up_unit_results()

	def before_submit(self):
		self.validate_completeness()

	def _get_unit_serials_for_population(self):
		"""Map units to serials when the stock under inspection names them.

		Lot flow: the serials that arrived through the lot's source document and
		still sit in its Quality Control warehouse. Row flow: the referenced
		row's serials. Only an unambiguous one-serial-per-unit match prefills.
		"""
		from erpnext.stock.services.quality_trigger_resolution import get_row_serial_nos

		if not self.quality_inspection or not frappe.get_cached_value(
			"Item", self.item_code, "has_serial_no"
		):
			return {}

		inspection = frappe.db.get_value(
			"Quality Inspection",
			self.quality_inspection,
			["reference_type", "reference_name", "child_row_reference"],
			as_dict=True,
		)
		if not inspection:
			return {}

		serials = []
		if inspection.reference_type == "Quality Control Lot" and inspection.reference_name:
			lot = frappe.db.get_value(
				"Quality Control Lot",
				inspection.reference_name,
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
				serials = []
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
		elif inspection.child_row_reference:
			child_doctype = (
				"Stock Entry Detail"
				if inspection.reference_type == "Stock Entry"
				else inspection.reference_type + " Item"
			)
			row = frappe.db.get_value(
				child_doctype,
				inspection.child_row_reference,
				["serial_no", "serial_and_batch_bundle"],
				as_dict=True,
			)
			if row:
				# typed serials on an inward row may not exist yet — a Link
				# entry cannot name an unborn serial
				serials = sorted(
					serial
					for serial in get_row_serial_nos(row)
					if frappe.db.exists("Serial No", serial)
				)

		if len(serials) != (self.quantity or 0):
			return {}
		return {unit_no: serial for unit_no, serial in enumerate(serials, start=1)}

	def validate_completeness(self):
		"""An Each Quantity inspection means every unit was actually inspected.

		On submission every declared unit must have readings, and every entry must
		carry one — otherwise untouched rows would pass on their default status
		without anyone having looked at the unit.
		"""
		self._validate_unit_serials()
		inspected_units = {entry.unit_no for entry in self.entries}
		missing_units = sorted(set(range(1, (self.quantity or 0) + 1)) - inspected_units)
		if missing_units:
			frappe.throw(
				_("Unit(s) {0} have no readings. Every unit must be inspected before submission.").format(
					frappe.bold(", ".join(map(str, missing_units)))
				),
				title=_("Units Not Inspected"),
			)

		for entry in self.entries:
			if not (entry.reading_value or "").strip():
				frappe.throw(
					_("Row #{0}: Record a reading for unit {1} ({2}) before submission.").format(
						entry.idx, entry.unit_no, entry.specification
					),
					title=_("Reading Missing"),
				)

	def on_cancel(self):
		inspection = frappe.db.exists("Quality Inspection", {"reading_bundle": self.name, "docstatus": 1})
		if inspection:
			frappe.throw(
				_("Cannot cancel: Quality Inspection {0} was decided on this reading bundle.").format(
					frappe.bold(inspection)
				)
			)

	def _validate_unit_serials(self):
		"""Lot-flow bundles of serialized items must name every unit's serial.

		Without them the release falls back to picking units by age instead of
		by verdict. Row-referenced bundles are exempt — inward serials may not
		exist before the document submits.
		"""
		if not frappe.get_cached_value("Item", self.item_code, "has_serial_no"):
			return
		if not self.quality_inspection:
			return
		if (
			frappe.db.get_value("Quality Inspection", self.quality_inspection, "reference_type")
			!= "Quality Control Lot"
		):
			return

		units_without_serial = sorted(
			{entry.unit_no for entry in self.entries if not entry.serial_no}
			- {entry.unit_no for entry in self.entries if entry.serial_no}
		)
		if units_without_serial:
			frappe.throw(
				_("Unit(s) {0} have no Serial No — every unit of a serialized item must be identified.").format(
					frappe.bold(", ".join(map(str, units_without_serial)))
				),
				title=_("Unit Serials Missing"),
			)

		unit_serials = {}
		for entry in self.entries:
			if entry.serial_no and unit_serials.setdefault(entry.unit_no, entry.serial_no) != entry.serial_no:
				frappe.throw(
					_("Unit {0} carries two different serials.").format(frappe.bold(entry.unit_no))
				)
		if len(set(unit_serials.values())) != len(unit_serials):
			frappe.throw(_("The same Serial No is recorded against more than one unit."))

	def get_unit_serials(self, status):
		"""Serial numbers of units whose roll-up matches the status.

		A unit is rejected if any of its readings rejected. Units without a
		recorded serial are skipped — quantity accounting covers them.
		"""
		rejected_units = {entry.unit_no for entry in self.entries if entry.status == "Rejected"}
		serial_by_unit = {}
		for entry in self.entries:
			if entry.serial_no:
				serial_by_unit.setdefault(entry.unit_no, entry.serial_no)

		if status == "Accepted":
			units = set(serial_by_unit) - rejected_units
		else:
			units = set(serial_by_unit) & rejected_units
		return sorted(serial_by_unit[unit] for unit in units)

	def evaluate_entry_statuses(self):
		"""Derive each entry's status from its reading, like the inspection readings.

		Numeric readings pass inside [min, max]; non-numeric readings are compared
		case-insensitively against the acceptance criteria value. Entries without a
		reading keep their manually chosen status.
		"""
		for entry in self.entries:
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

	def validate_units(self):
		units = {entry.unit_no for entry in self.entries}
		if units and (min(units) < 1 or max(units) > self.quantity):
			frappe.throw(
				_("Unit numbers must lie between 1 and the inspected quantity ({0}).").format(self.quantity)
			)

	def roll_up_unit_results(self):
		"""A unit is accepted only if every one of its readings is accepted."""
		rejected_units = {entry.unit_no for entry in self.entries if entry.status == "Rejected"}
		inspected_units = {entry.unit_no for entry in self.entries}

		self.rejected_qty = len(rejected_units)
		self.accepted_qty = len(inspected_units - rejected_units)

	@frappe.whitelist()
	def populate_units(self):
		"""Generate one row per unit and template parameter."""
		from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
			get_template_details,
		)

		parameters = get_template_details(self.quality_inspection_template)
		if not parameters:
			frappe.throw(_("Select a Quality Inspection Template with parameters first."))

		unit_serials = self._get_unit_serials_for_population()
		self.set("entries", [])
		for unit_no in range(1, (self.quantity or 0) + 1):
			for parameter in parameters:
				self.append(
					"entries",
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
