# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


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

	pass
