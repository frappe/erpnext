# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class MaintenanceScheduleItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.TextEditor | None
		end_date: DF.Date
		item_code: DF.Link
		item_name: DF.Data | None
		no_of_visits: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		periodicity: DF.Literal["", "Weekly", "Monthly", "Quarterly", "Half Yearly", "Yearly", "Random"]
		sales_order: DF.Link | None
		sales_person: DF.Link | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.SmallText | None
		start_date: DF.Date
	# end: auto-generated types

	pass
