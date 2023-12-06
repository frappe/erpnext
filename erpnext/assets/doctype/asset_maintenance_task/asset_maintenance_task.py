# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class AssetMaintenanceTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		assign_to: DF.Link | None
		assign_to_name: DF.ReadOnly | None
		certificate_required: DF.Check
		description: DF.TextEditor | None
		end_date: DF.Date | None
		last_completion_date: DF.Date | None
		maintenance_status: DF.Literal["Planned", "Overdue", "Cancelled"]
		maintenance_task: DF.Data
		maintenance_type: DF.Literal["Preventive Maintenance", "Calibration"]
		next_due_date: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		periodicity: DF.Literal[
			"", "Daily", "Weekly", "Monthly", "Quarterly", "Half-yearly", "Yearly", "2 Yearly", "3 Yearly"
		]
		start_date: DF.Date
	# end: auto-generated types

	pass
