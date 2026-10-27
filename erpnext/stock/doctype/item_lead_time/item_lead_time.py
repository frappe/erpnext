# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import ceil, cint, flt

MANUFACTURING_INPUT_FIELDS = (
	"shift_time_in_hours",
	"no_of_workstations",
	"no_of_shift",
	"manufacturing_time_in_mins",
)


class ItemLeadTime(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		buffer_time: DF.Int
		capacity_per_day: DF.Int
		daily_yield: DF.Percent
		item_code: DF.Link | None
		item_name: DF.Data | None
		manufacturing_time_in_mins: DF.Int
		no_of_shift: DF.Int
		no_of_units_produced: DF.Int
		no_of_workstations: DF.Int
		purchase_time: DF.Int
		shift_time_in_hours: DF.Int
		stock_uom: DF.Link | None
		total_workstation_time: DF.Int
	# end: auto-generated types

	def validate(self):
		self.set_capacity_per_day()

	def set_capacity_per_day(self):
		self.total_workstation_time = (
			cint(self.shift_time_in_hours) * cint(self.no_of_workstations) * cint(self.no_of_shift)
		)
		if self.total_workstation_time and cint(self.manufacturing_time_in_mins):
			units_produced = flt(self.total_workstation_time) / cint(self.manufacturing_time_in_mins) * 60
		elif self.has_manufacturing_inputs_changed():
			units_produced = 0
		else:
			return

		self.no_of_units_produced = cint(units_produced)
		self.capacity_per_day = ceil(flt(self.daily_yield) * units_produced / 100)

	def has_manufacturing_inputs_changed(self):
		return not self.is_new() and any(
			self.has_value_changed(fieldname) for fieldname in MANUFACTURING_INPUT_FIELDS
		)
