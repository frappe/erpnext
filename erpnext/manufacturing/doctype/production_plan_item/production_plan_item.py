# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class ProductionPlanItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bom_no: DF.Link
		description: DF.TextEditor | None
		include_exploded_items: DF.Check
		item_code: DF.Link
		item_reference: DF.Data | None
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		ordered_qty: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pending_qty: DF.Float
		planned_qty: DF.Float
		planned_start_date: DF.Datetime
		produced_qty: DF.Float
		product_bundle_item: DF.Link | None
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		stock_uom: DF.Link
		temporary_name: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
