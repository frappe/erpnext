# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class MaintenanceVisitPurpose(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.TextEditor | None
		item_code: DF.Link | None
		item_name: DF.Data | None
		maintenance_schedule_detail: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		prevdoc_docname: DF.DynamicLink | None
		prevdoc_doctype: DF.Link | None
		serial_no: DF.Link | None
		service_person: DF.Link
		work_done: DF.SmallText
	# end: auto-generated types

	pass
