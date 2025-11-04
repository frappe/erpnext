# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class MaintenanceScheduleDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_date: DF.Date | None
		completion_status: DF.Literal["Pending", "Partially Completed", "Fully Completed"]
		item_code: DF.Link | None
		item_name: DF.Data | None
		item_reference: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		sales_person: DF.Link | None
		scheduled_date: DF.Date
		serial_no: DF.SmallText | None
	# end: auto-generated types

	pass
