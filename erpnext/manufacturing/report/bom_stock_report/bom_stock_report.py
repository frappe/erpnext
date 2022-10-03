# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Floor, Sum
from pypika.terms import ExistsCriterion


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_bom_stock(filters)

	return columns, data


def get_columns():
	"""return columns"""
	columns = [
		_("Item") + ":Link/Item:150",
		_("Description") + "::300",
		_("BOM Qty") + ":Float:160",
		_("BOM UoM") + "::160",
		_("Required Qty") + ":Float:120",
		_("In Stock Qty") + ":Float:120",
		_("Enough Parts to Build") + ":Float:200",
	]

	return columns


def get_bom_stock(filters):
	qty_to_produce = filters.get("qty_to_produce") or 1
	if int(qty_to_produce) < 0:
		frappe.throw(_("Quantity to Produce can not be less than Zero"))

	if filters.get("show_exploded_view"):
		bom_item_table = "BOM Explosion Item"
	else:
		bom_item_table = "BOM Item"

	bin = frappe.qb.DocType("Bin")
	bom = frappe.qb.DocType("BOM")
	bom_item = frappe.qb.DocType(bom_item_table)

	query = (
		frappe.qb.from_(bom)
		.inner_join(bom_item)
		.on(bom.name == bom_item.parent)
		.left_join(bin)
		.on(bom_item.item_code == bin.item_code)
		.select(
			bom_item.item_code,
			bom_item.description,
			bom_item.stock_qty,
			bom_item.stock_uom,
			bom_item.stock_qty * qty_to_produce / bom.quantity,
			Sum(bin.actual_qty).as_("actual_qty"),
			Sum(Floor(bin.actual_qty / (bom_item.stock_qty * qty_to_produce / bom.quantity))),
		)
		.where((bom_item.parent == filters.get("bom")) & (bom_item.parenttype == "BOM"))
		.groupby(bom_item.item_code)
	)

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value(
			"Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1
		)

		if warehouse_details:
			wh = frappe.qb.DocType("Warehouse")
			query = query.where(
				ExistsCriterion(
					frappe.qb.from_(wh)
					.select(wh.name)
					.where(
						(wh.lft >= warehouse_details.lft)
						& (wh.rgt <= warehouse_details.rgt)
						& (bin.warehouse == wh.name)
					)
				)
			)
		else:
			query = query.where(bin.warehouse == filters.get("warehouse"))

	return query.run()
