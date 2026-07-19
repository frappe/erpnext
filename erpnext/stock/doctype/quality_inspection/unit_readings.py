# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Per-unit readings for Each Quantity inspections.

One row per unit and template parameter lives in the inspection's unit
readings table; their roll-up decides the verdict, their serials drive
serial-precise releases, and a Quality Control Lot may be decided by several
inspections, each covering a tranche of units.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, get_link_to_form

from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)


class UnitReadingsMixin:
	def set_status_from_unit_readings(self):
		"""The per-unit roll-up decides the verdict unless the inspector overrides."""
		if self.accepted_unit_quantity and self.rejected_unit_quantity:
			self.status = "Partially Accepted"
		elif self.accepted_unit_quantity:
			self.status = "Accepted"
		else:
			self.status = "Rejected"

	def set_decided_quantity_default(self):
		"""A blank (or zero) Decided Quantity means everything still undecided."""
		if (
			self.reference_type in ("Quality Control Lot", "Goods Inward Note")
			and self.reference_name
			and (self.inspection_basis != "Each Quantity" or self.manual_inspection)
			and not flt(self.decided_quantity)
		):
			self.decided_quantity = flt(self.get_qty_under_inspection())

	def validate_decided_quantity(self):
		"""Resolve and bound how much of the stock this verdict decides.

		A lot — or a custody row, batch by batch — may be decided in parts.
		Each Quantity verdicts decide exactly their units. Sample and manual
		verdicts decide the stated quantity, defaulting to everything still
		undecided — and for serialized items a partial verdict must name its
		units, so it has to be on an Each Quantity basis.
		"""
		if self.reference_type not in ("Quality Control Lot", "Goods Inward Note") or not self.reference_name:
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
				_("This inspection decides {0} unit(s), but only {1} remain undecided on {2}.").format(
					self.decided_quantity,
					flt(undecided),
					get_link_to_form(self.reference_type, self.reference_name),
				),
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
			# custody precedes the receipt that mints serials: a partial custody
			# verdict need not name units it cannot know yet
			and self.reference_type != "Goods Inward Note"
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
		repeated = {entry.serial_no for entry in self.unit_readings if entry.serial_no} & decided_serials
		if repeated:
			frappe.throw(
				_("Serial number(s) {0} were already decided by an earlier inspection of this lot.").format(
					", ".join(get_link_to_form("Serial No", serial) for serial in sorted(repeated))
				),
				title=_("Serials Already Decided"),
			)

	def validate_unit_readings_coverage(self):
		"""An Each Quantity inspection must cover exactly the stock it decides."""
		if self.inspection_basis != "Each Quantity":
			return

		# a manual inspection's verdict overrides the per-unit machinery
		if self.manual_inspection:
			return

		inspected_qty = self.get_qty_under_inspection()
		if self.reference_type in ("Quality Control Lot", "Goods Inward Note"):
			# a lot or a custody row may be decided in parts, one batch of units
			# per inspection — but never beyond what is undecided
			if inspected_qty is not None and flt(self.unit_quantity) > flt(inspected_qty):
				frappe.throw(
					_("The unit readings inspect {0} unit(s), but only {1} remain undecided on {2}.").format(
						self.unit_quantity,
						flt(inspected_qty),
						get_link_to_form(self.reference_type, self.reference_name),
					),
					title=_("More Units Than Undecided"),
				)
		elif inspected_qty and flt(self.unit_quantity) != flt(inspected_qty):
			frappe.throw(
				_(
					"The unit readings inspect {0} unit(s), but {1} are under inspection — a "
					"verdict here cannot decide in parts. Inspect every unit, judge them all "
					"from a sample on the Sample basis, or inspect in parts through a Goods "
					"Inward Note."
				).format(self.unit_quantity, inspected_qty),
				title=_("Incomplete Per-Unit Readings"),
			)

	def _whole_quantity_under_inspection(self):
		"""Per-unit readings need whole units — refuse to truncate silently.

		A fractional quantity (12.5 kg) has no unit number 12.5; inspecting it
		per unit is incoherent, and rounding it down would quietly leave a
		fraction undecided forever.
		"""
		qty = flt(self.get_qty_under_inspection() or 0)
		if qty != cint(qty):
			frappe.throw(
				_(
					"{0} under inspection is fractional — per-unit readings need whole units. "
					"Inspect this stock on the Sample basis instead."
				).format(qty),
				title=_("Fractional Quantity"),
			)
		return cint(qty)

	def validate_units(self):
		units = {entry.unit_no for entry in self.unit_readings}
		if units and (min(units) < 1 or max(units) > cint(self.unit_quantity)):
			frappe.throw(
				_("Unit numbers must lie between 1 and the unit quantity ({0}).").format(self.unit_quantity)
			)

	def evaluate_unit_entry_statuses(self):
		"""Derive each unit entry's status from its reading, like the sampled readings.

		Numeric readings pass inside [min, max]; non-numeric readings are compared
		case-insensitively against the acceptance criteria value. Entries without a
		reading — or marked Manual Inspection — keep their manually chosen status.
		"""
		for entry in self.unit_readings:
			if entry.manual_inspection:
				continue
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
		status without anyone having looked at the unit. An entry marked
		Manual Inspection is a deliberate verdict, not an untouched row: it
		needs no reading.
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
					frappe.bold(", ".join(str(unit) for unit in missing_units))
				),
				title=_("Units Not Inspected"),
			)

		for entry in self.unit_readings:
			if entry.manual_inspection:
				continue
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
				_(
					"Unit(s) {0} have no Serial No — every unit of a serialized item must be identified."
				).format(frappe.bold(", ".join(str(unit) for unit in units_without_serial))),
				title=_("Unit Serials Missing"),
			)

		unit_serials = {}
		for entry in self.unit_readings:
			if entry.serial_no and unit_serials.setdefault(entry.unit_no, entry.serial_no) != entry.serial_no:
				frappe.throw(_("Unit {0} carries two different serials.").format(frappe.bold(entry.unit_no)))
		if len(set(unit_serials.values())) != len(unit_serials):
			frappe.throw(_("The same Serial No is recorded against more than one unit."))

	@frappe.whitelist()
	def populate_units(self):
		"""Generate one unit reading row per unit and template parameter."""
		parameters = get_template_details(self.quality_inspection_template)
		if not parameters:
			frappe.throw(_("Select a Quality Inspection Template with parameters first."))

		if not cint(self.unit_quantity):
			self.unit_quantity = self._whole_quantity_under_inspection()
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
					info = frappe.db.get_value("Serial No", serial, ["warehouse", "batch_no"], as_dict=True)
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
			from erpnext.stock.services.quality_trigger_resolution import get_reference_row_tracking

			row = get_reference_row_tracking(child_doctype, self.child_row_reference)
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
		from erpnext.stock.services.quality_trigger_resolution import get_reference_row_tracking

		row = get_reference_row_tracking(child_doctype, self.child_row_reference)
		return bool(row) and not (unborn - set(get_row_serial_nos(row)))
