# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class MaterialRequestItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		amount: DF.Currency
		bom_no: DF.Link | None
		brand: DF.Link | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		description: DF.TextEditor | None
		expense_account: DF.Link | None
		from_warehouse: DF.Link | None
		image: DF.AttachImage | None
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		job_card_item: DF.Data | None
		lead_time_date: DF.Date | None
		manufacturer: DF.Link | None
		manufacturer_part_no: DF.Data | None
		material_request_plan_item: DF.Data | None
		min_order_qty: DF.Float
		ordered_qty: DF.Float
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		price_list_rate: DF.Currency
		production_plan: DF.Link | None
		project: DF.Link | None
		projected_on_hand: DF.Float
		projected_qty: DF.Float
		qty: DF.Float
		rate: DF.Currency
		received_qty: DF.Float
		reorder_level: DF.Float
		reorder_qty: DF.Float
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		schedule_date: DF.Date
		stock_qty: DF.Float
		stock_uom: DF.Link
		uom: DF.Link
		warehouse: DF.Link | None
		wip_composite_asset: DF.Link | None
	# end: auto-generated types

	pass


def on_doctype_update():
	frappe.db.add_index("Material Request Item", ["item_code", "warehouse"])
