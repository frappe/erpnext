# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class MaterialRequestPlanItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		conversion_factor: DF.Float
		description: DF.TextEditor | None
		from_warehouse: DF.Link | None
		item_code: DF.Link
		item_name: DF.Data | None
		material_request_type: DF.Literal[
			"", "Purchase", "Material Transfer", "Material Issue", "Manufacture", "Customer Provided"
		]
		min_order_qty: DF.Float
		ordered_qty: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		projected_qty: DF.Float
		quantity: DF.Float
		requested_qty: DF.Float
		required_bom_qty: DF.Float
		reserved_qty_for_production: DF.Float
		safety_stock: DF.Float
		sales_order: DF.Link | None
		schedule_date: DF.Date | None
		uom: DF.Link | None
		warehouse: DF.Link
	# end: auto-generated types

	pass
