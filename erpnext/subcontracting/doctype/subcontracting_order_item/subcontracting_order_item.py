# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractingOrderItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		additional_cost_per_qty: DF.Currency
		amount: DF.Currency
		bom: DF.Link
		conversion_factor: DF.Float
		cost_center: DF.Link | None
<<<<<<< HEAD
		description: DF.TextEditor | None
=======
		description: DF.TextEditor
>>>>>>> 7c4cf3e834 (Favicon.svg)
		expected_delivery_date: DF.Date | None
		expense_account: DF.Link | None
		image: DF.Attach | None
		include_exploded_items: DF.Check
		item_code: DF.Link
		item_name: DF.Data
<<<<<<< HEAD
		job_card: DF.Link | None
		manufacturer: DF.Link | None
		manufacturer_part_no: DF.Data | None
		material_request: DF.Link | None
		material_request_item: DF.Data | None
=======
		manufacturer: DF.Link | None
		manufacturer_part_no: DF.Data | None
>>>>>>> 7c4cf3e834 (Favicon.svg)
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
<<<<<<< HEAD
		production_plan_sub_assembly_item: DF.Data | None
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		project: DF.Link | None
		purchase_order_item: DF.Data | None
		qty: DF.Float
		rate: DF.Currency
		received_qty: DF.Float
		returned_qty: DF.Float
		rm_cost_per_qty: DF.Currency
		schedule_date: DF.Date | None
		service_cost_per_qty: DF.Currency
		stock_uom: DF.Link
<<<<<<< HEAD
		subcontracting_conversion_factor: DF.Float
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		warehouse: DF.Link
	# end: auto-generated types

	pass
