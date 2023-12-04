# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class RequestforQuotationItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		brand: DF.Link | None
		conversion_factor: DF.Float
		description: DF.TextEditor | None
		image: DF.Attach | None
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		project_name: DF.Link | None
		qty: DF.Float
		schedule_date: DF.Date
		stock_qty: DF.Float
		stock_uom: DF.Link
		supplier_part_no: DF.Data | None
		uom: DF.Link
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
