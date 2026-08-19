# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class BOMExplosionItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		description: DF.TextEditor | None
		image: DF.Attach | None
		include_item_in_manufacturing: DF.Check
		is_sub_assembly_item: DF.Check
		item_code: DF.Link | None
		item_name: DF.Data | None
		operation: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty_consumed_per_unit: DF.Float
		rate: DF.Currency
		source_warehouse: DF.Link | None
		sourced_by_supplier: DF.Check
		stock_qty: DF.Float
		stock_uom: DF.Link | None
	# end: auto-generated types

	pass
