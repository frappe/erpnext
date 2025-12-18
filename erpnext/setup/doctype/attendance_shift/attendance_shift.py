# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AttendanceShift(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		break_end_time: DF.Time | None
		break_start_time: DF.Time | None
		code: DF.Data
		does_span_next_day: DF.Check
		end_time: DF.Time
		is_active: DF.Check
		is_break_enabled: DF.Check
		shift_name: DF.Data
		start_time: DF.Time
	# end: auto-generated types
	pass
