# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class WorkOrderItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_alternative_item: DF.Check
		amount: DF.Currency
		available_qty_at_source_warehouse: DF.Float
		available_qty_at_wip_warehouse: DF.Float
		consumed_qty: DF.Float
		description: DF.Text | None
		include_item_in_manufacturing: DF.Check
		item_code: DF.Link | None
		item_name: DF.Data | None
		operation: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Currency
		required_qty: DF.Float
		returned_qty: DF.Float
		source_warehouse: DF.Link | None
		transferred_qty: DF.Float
	# end: auto-generated types

	pass


def on_doctype_update():
	frappe.db.add_index("Work Order Item", ["item_code", "source_warehouse"])
