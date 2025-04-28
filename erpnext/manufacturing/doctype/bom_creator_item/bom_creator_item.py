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
<<<<<<< HEAD
=======
		backflush_from_wip_warehouse: DF.Check
>>>>>>> 7c4cf3e834 (Favicon.svg)
		base_amount: DF.Currency
		base_rate: DF.Currency
		bom_created: DF.Check
		conversion_factor: DF.Float
		description: DF.SmallText | None
		do_not_explode: DF.Check
		fg_item: DF.Link
		fg_reference_id: DF.Data | None
<<<<<<< HEAD
		instruction: DF.SmallText | None
		is_expandable: DF.Check
		is_phantom_item: DF.Check
=======
		fg_warehouse: DF.Link | None
		instruction: DF.SmallText | None
		is_expandable: DF.Check
>>>>>>> 7c4cf3e834 (Favicon.svg)
		is_subcontracted: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		operation: DF.Link | None
<<<<<<< HEAD
=======
		operation_time: DF.Int
>>>>>>> 7c4cf3e834 (Favicon.svg)
		parent: DF.Data
		parent_row_no: DF.Data | None
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		rate: DF.Currency
<<<<<<< HEAD
=======
		skip_material_transfer: DF.Check
		source_warehouse: DF.Link | None
>>>>>>> 7c4cf3e834 (Favicon.svg)
		sourced_by_supplier: DF.Check
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		uom: DF.Link | None
<<<<<<< HEAD
=======
		wip_warehouse: DF.Link | None
		workstation: DF.Link | None
		workstation_type: DF.Link | None
>>>>>>> 7c4cf3e834 (Favicon.svg)
	# end: auto-generated types

	pass
