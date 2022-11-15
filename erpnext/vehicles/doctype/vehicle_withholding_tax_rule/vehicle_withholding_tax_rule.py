# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, getdate
from frappe.model.document import Document

class VehicleWithholdingTaxRule(Document):
	def validate(self):
		self.check_date_overlap()
		self.validate_from_to_values()
		self.sort_slabs()
		self.validate_overlapping_slabs()

	def check_date_overlap(self):
		from_date = self.from_date or '2000-01-01'
		to_date = self.to_date or '3000-01-01'
		rules = get_applicable_rules(self.company, from_date, to_date, exclude=self.name if not self.is_new() else None)
		if rules:
			frappe.throw(_("Date range overlaps with Rule {0}").format(", ".join(rules)))

	def validate_from_to_values(self):
		zero_from_capacities = []
		zero_to_capacities = []

		for d in self.engine_capacity_slabs:
			self.round_floats_in(d)
			d.from_capacity = cint(d.from_capacity)
			d.to_capacity = cint(d.to_capacity)

			# values cannot be negative
			self.validate_value("from_capacity", ">=", 0, d)
			self.validate_value("to_capacity", ">=", 0, d)

			if not d.from_capacity:
				zero_from_capacities.append(d)
			elif not d.to_capacity:
				zero_to_capacities.append(d)
			elif d.from_capacity >= d.to_capacity:
				frappe.throw(_("From Capacity must be less than To Capacity in row {0}").format(d.idx))

		# check if more than two or more rows has To Value = 0
		if len(zero_from_capacities) >= 2:
			frappe.throw(_('There can only be one Engine Capacity Slab with 0 or blank value for "From Capacity"'))

	def sort_slabs(self):
		engine_capacity_slabs = sorted(self.engine_capacity_slabs, key=lambda d: cint(d.from_capacity))
		for i, d in enumerate(engine_capacity_slabs):
			d.idx = i + 1

	def validate_overlapping_slabs(self):
		def overlap_exists_between(num_range1, num_range2):
			(x1, x2), (y1, y2) = num_range1, num_range2
			separate = (x1 <= x2 < y1 <= y2) or (y1 <= y2 < x1 <= x2)
			return (not separate)

		overlaps = []
		for i in range(0, len(self.engine_capacity_slabs)):
			for j in range(i+1, len(self.engine_capacity_slabs)):
				d1, d2 = self.engine_capacity_slabs[i], self.engine_capacity_slabs[j]
				if d1.as_dict() != d2.as_dict():
					# in our case, to_capacity can be zero, hence pass the from_capacity if so
					range_a = (d1.from_capacity, d1.to_capacity or d1.from_capacity)
					range_b = (d2.from_capacity, d2.to_capacity or d2.from_capacity)
					if overlap_exists_between(range_a, range_b):
						overlaps.append([d1, d2])

		if overlaps:
			frappe.msgprint(_("Overlapping slabs found between:"))
			messages = []
			for d1, d2 in overlaps:
				messages.append("%sCC - %sCC " % (d1.from_capacity, d1.to_capacity) +
					_("and") + " %sCC - %sCC" % (d2.from_capacity, d2.to_capacity))

			frappe.throw("<br>".join(messages))

	def get_tax_amount(self, engine_capacity, tax_status):
		engine_capacity = cint(engine_capacity)

		applicable_slab = None
		for slab in self.engine_capacity_slabs:
			if not slab.to_capacity or (cint(slab.from_capacity) <= engine_capacity <= cint(slab.to_capacity)):
				applicable_slab = slab
				break

		if applicable_slab:
			if not tax_status:
				frappe.msgprint(_("Cannot determine Withholding Tax amount because Income Tax Status is not provided"),
					indicator="orange")
				return 0.0
			else:
				return applicable_slab.filer_amount if tax_status == "Filer" else applicable_slab.nonfiler_amount

		return 0.0


@frappe.whitelist()
def get_withholding_tax_amount(date, item_code, tax_status, company):
	if tax_status == "Exempt":
		return 0

	name = get_applicable_rules(company, date)
	name = name[0] if name else None
	if not name:
		return 0

	engine_capacity, item_exempt = frappe.get_cached_value("Item", item_code,
		["vehicle_engine_capacity", "exempt_from_vehicle_withholding_tax"])

	if item_exempt:
		return 0

	doc = frappe.get_cached_doc("Vehicle Withholding Tax Rule", name)
	return doc.get_tax_amount(engine_capacity, tax_status)


def get_applicable_rules(company, date, to_date=None, exclude=None):
	date = getdate(date)
	if to_date:
		to_date = getdate(to_date)
		date_condition = "'{0}' <= ifnull(to_date, '3000-01-01') and '{1}' >= ifnull(from_date, '2000-01-01')".format(date, to_date)
	else:
		date_condition = "'{0}' between ifnull(from_date, '2000-01-01') and ifnull(to_date, '3000-01-01')".format(date)

	exclude_condition = ""
	if exclude:
		exclude_condition = "and name != {0}".format(frappe.db.escape(exclude))

	return frappe.db.sql_list("""
		select name
		from `tabVehicle Withholding Tax Rule`
		where disabled = 0 and company = %s and {0} {1}
		order by ifnull(from_date, '2000-01-01') desc, creation desc
	""".format(date_condition, exclude_condition), company)
