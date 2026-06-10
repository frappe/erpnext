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

	def validate_completeness(self):
		"""An Each Quantity inspection means every unit was actually inspected.

		On submission every declared unit must have readings, and every entry must
		carry one — otherwise untouched rows would pass on their default status
		without anyone having looked at the unit.
		"""
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

		self.set("entries", [])
		for unit_no in range(1, (self.quantity or 0) + 1):
			for parameter in parameters:
				self.append(
					"entries",
					{
						"unit_no": unit_no,
						"specification": parameter.specification,
						"numeric": parameter.numeric,
						"value": parameter.value,
						"min_value": parameter.min_value,
						"max_value": parameter.max_value,
						"status": "Accepted",
					},
				)
