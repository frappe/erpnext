# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import Order
from frappe.utils import get_link_to_form, nowdate, nowtime


class PlantFloor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		floor_name: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	@frappe.whitelist()
	def make_stock_entry(self, kwargs):
		if isinstance(kwargs, str):
			kwargs = frappe.parse_json(kwargs)

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.update(
			{
				"company": kwargs.company,
				"from_warehouse": kwargs.from_warehouse,
				"to_warehouse": kwargs.to_warehouse,
				"purpose": kwargs.purpose,
				"stock_entry_type": kwargs.purpose,
				"posting_date": nowdate(),
				"posting_time": nowtime(),
				"items": self.get_item_details(kwargs),
			}
		)

		stock_entry.set_missing_values()

		return stock_entry

	def get_item_details(self, kwargs) -> list[dict]:
		item_details = frappe.db.get_value(
			"Item", kwargs.item_code, ["item_name", "stock_uom", "item_group", "description"], as_dict=True
		)
		item_details.update(
			{
				"qty": kwargs.qty,
				"uom": item_details.stock_uom,
				"item_code": kwargs.item_code,
				"conversion_factor": 1,
				"s_warehouse": kwargs.from_warehouse,
				"t_warehouse": kwargs.to_warehouse,
			}
		)

		return [item_details]


@frappe.whitelist()
def get_stock_summary(warehouse, start=0, item_code=None, item_group=None):
	stock_details = get_stock_details(warehouse, start=start, item_code=item_code, item_group=item_group)

	max_count = 0.0
	for d in stock_details:
		d.actual_or_pending = (
			d.projected_qty + d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract
		)
		d.pending_qty = 0
		d.total_reserved = d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract
		if d.actual_or_pending > d.actual_qty:
			d.pending_qty = d.actual_or_pending - d.actual_qty

		d.max_count = max(d.actual_or_pending, d.actual_qty, d.total_reserved, max_count)
		max_count = d.max_count
		d.item_link = get_link_to_form("Item", d.item_code)

	return stock_details


def get_stock_details(warehouse, start=0, item_code=None, item_group=None):
	item_table = frappe.qb.DocType("Item")
	bin_table = frappe.qb.DocType("Bin")

	query = (
		frappe.qb.from_(bin_table)
		.inner_join(item_table)
		.on(bin_table.item_code == item_table.name)
		.select(
			bin_table.item_code,
			bin_table.actual_qty,
			bin_table.projected_qty,
			bin_table.reserved_qty,
			bin_table.reserved_qty_for_production,
			bin_table.reserved_qty_for_sub_contract,
			bin_table.reserved_qty_for_production_plan,
			bin_table.reserved_stock,
			item_table.item_name,
			item_table.item_group,
			item_table.image,
		)
		.where(bin_table.warehouse == warehouse)
		.limit(20)
		.offset(start)
		.orderby(bin_table.actual_qty, order=Order.desc)
	)

	if item_code:
		query = query.where(bin_table.item_code == item_code)

	if item_group:
		query = query.where(item_table.item_group == item_group)

	return query.run(as_dict=True)
