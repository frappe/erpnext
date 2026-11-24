# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BOMCreatorItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		base_amount: DF.Currency
		base_rate: DF.Currency
		bom_created: DF.Check
		bom_no: DF.Link | None
		change_type: DF.Literal["", "Added", "Quantity Changed"]
		conversion_factor: DF.Float
		description: DF.SmallText | None
		design_quantity: DF.Float
		do_not_explode: DF.Check
		exclude_from_bom: DF.Check
		instruction: DF.SmallText | None
		is_expandable: DF.Check
		is_phantom_item: DF.Check
		item_code: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data | None
		model_file: DF.Attach | None
		node_id: DF.Int
		operation: DF.Link | None
		parent: DF.Data
		parent_node_id: DF.Int
		parentfield: DF.Data
		parenttype: DF.Data
		part_name: DF.Data | None
		part_number: DF.Data | None
		placements: DF.JSON | None
		qty: DF.Float
		rate: DF.Currency
		source: DF.Literal["CAD File", "Manual"]
		sourced_by_supplier: DF.Check
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		uom: DF.Link | None
	# end: auto-generated types

	pass
