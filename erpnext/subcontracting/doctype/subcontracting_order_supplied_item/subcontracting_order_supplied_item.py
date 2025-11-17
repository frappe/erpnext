# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractingOrderSuppliedItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		bom_detail_no: DF.Data | None
		consumed_qty: DF.Float
		conversion_factor: DF.Float
		main_item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Currency
		reference_name: DF.Data | None
		required_qty: DF.Float
		reserve_warehouse: DF.Link | None
		returned_qty: DF.Float
		rm_item_code: DF.Link | None
		stock_reserved_qty: DF.Float
		stock_uom: DF.Link | None
		supplied_qty: DF.Float
		total_supplied_qty: DF.Float
	# end: auto-generated types

	pass
