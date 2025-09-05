# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Floor, Sum
from frappe.utils import cint


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_bom_stock(filters)

	return columns, data


def get_columns():
	return [
		_("Item") + ":Link/Item:150",
		_("Item Name") + "::240",
		_("Description") + "::300",
		_("BOM Qty") + ":Float:160",
		_("BOM UoM") + "::160",
		_("Required Qty") + ":Float:120",
		_("In Stock Qty") + ":Float:120",
		_("Enough Parts to Build") + ":Float:200",
	]


def get_bom_stock(filters):
	qty_to_produce = filters.get("qty_to_produce")
	if cint(qty_to_produce) <= 0:
		frappe.throw(_("Quantity to Produce should be greater than zero."))

	bom_item_table = "BOM Explosion Item" if filters.get("show_exploded_view") else "BOM Item"

	warehouse = filters.get("warehouse")
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)

	BOM = frappe.qb.DocType("BOM")
	BOM_ITEM = frappe.qb.DocType(bom_item_table)
	BIN = frappe.qb.DocType("Bin")
	WH = frappe.qb.DocType("Warehouse")

	if warehouse_details:
		bin_subquery = (
			frappe.qb.from_(BIN)
			.join(WH)
			.on(BIN.warehouse == WH.name)
			.select(BIN.item_code, Sum(BIN.actual_qty).as_("actual_qty"))
			.where((WH.lft >= warehouse_details.lft) & (WH.rgt <= warehouse_details.rgt))
			.groupby(BIN.item_code)
		)
	else:
		bin_subquery = (
			frappe.qb.from_(BIN)
			.select(BIN.item_code, Sum(BIN.actual_qty).as_("actual_qty"))
			.where(BIN.warehouse == warehouse)
			.groupby(BIN.item_code)
		)

	QUERY = (
		frappe.qb.from_(BOM)
		.join(BOM_ITEM)
		.on(BOM.name == BOM_ITEM.parent)
		.left_join(bin_subquery)
		.on(BOM_ITEM.item_code == bin_subquery.item_code)
		.select(
			BOM_ITEM.item_code,
			BOM_ITEM.item_name,
			BOM_ITEM.description,
			Sum(BOM_ITEM.stock_qty),
			BOM_ITEM.stock_uom,
			(Sum(BOM_ITEM.stock_qty) * qty_to_produce) / BOM.quantity,
			bin_subquery.actual_qty,
			Floor(bin_subquery.actual_qty / ((Sum(BOM_ITEM.stock_qty) * qty_to_produce) / BOM.quantity)),
		)
		.where((BOM_ITEM.parent == filters.get("bom")) & (BOM_ITEM.parenttype == "BOM"))
		.groupby(BOM_ITEM.item_code)
	)

	return QUERY.run()
