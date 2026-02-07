# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SlabHistory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		in_time: DF.Datetime
		job_card_number: DF.Data | None
		out_time: DF.Datetime | None
		oven_params: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		preliminary_qc: DF.Link | None
		quality_report_name: DF.Link | None
		station: DF.Data
		total_time_in_minutes: DF.Float
	# end: auto-generated types
	pass
