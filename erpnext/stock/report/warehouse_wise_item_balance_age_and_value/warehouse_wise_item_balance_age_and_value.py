# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2013, Tristar Enterprises and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import cint, flt, getdate

from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.report.stock_analytics.stock_analytics import (
	get_item_details,
	get_items,
	get_stock_ledger_entries,
)
from erpnext.stock.report.stock_balance.stock_balance import filter_items_with_no_transactions
from erpnext.stock.utils import is_reposting_item_valuation_in_progress


def execute(filters=None):
	is_reposting_item_valuation_in_progress()
	if not filters:
		filters = {}

	validate_filters(filters)

	columns = get_columns(filters)

	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	item_map = get_item_details(items, sle)
	iwb_map = get_item_warehouse_map(filters, sle)
	warehouse_list = get_warehouse_list(filters)
	item_ageing = FIFOSlots(filters).generate()
	data = []
	item_balance = {}
	item_value = {}

	for company, item, warehouse in sorted(iwb_map):
		if not item_map.get(item):
			continue

		row = []
		qty_dict = iwb_map[(company, item, warehouse)]
		item_balance.setdefault((item, item_map[item]["item_group"]), [])
		total_stock_value = 0.00
		for wh in warehouse_list:
			row += [qty_dict.bal_qty] if wh.name == warehouse else [0.00]
			total_stock_value += qty_dict.bal_val if wh.name == warehouse else 0.00

		item_balance[(item, item_map[item]["item_group"])].append(row)
		item_value.setdefault((item, item_map[item]["item_group"]), [])
		item_value[(item, item_map[item]["item_group"])].append(total_stock_value)

	itemwise_brand = frappe._dict(get_itemwise_brand(items))
	# sum bal_qty by item
	for (item, item_group), wh_balance in item_balance.items():
		if not item_ageing.get(item):
			continue

		total_stock_value = sum(item_value[(item, item_group)])
		row = [item, item_map[item]["item_name"], item_group, itemwise_brand.get(item), total_stock_value]

		fifo_queue = item_ageing[item]["fifo_queue"]
		average_age = 0.00
		if fifo_queue:
			average_age = get_average_age(fifo_queue, filters["to_date"])

		row += [average_age]

		bal_qty = [sum(bal_qty) for bal_qty in zip(*wh_balance, strict=False)]
		total_qty = sum(bal_qty)
		if len(warehouse_list) > 1:
			row += [total_qty]
		row += bal_qty

		if total_qty > 0:
			data.append(row)
		elif not filters.get("filter_total_zero_qty"):
			data.append(row)
	add_warehouse_column(columns, warehouse_list)
	return columns, data


def get_itemwise_brand(items):
	return frappe.get_all("Item", filters={"name": ("in", items)}, fields=["name", "brand"], as_list=1)


def get_columns(filters):
	"""return columns"""

	columns = [
		_("Item") + ":Link/Item:150",
		_("Item Name") + ":Link/Item:150",
		_("Item Group") + "::120",
		_("Brand") + ":Link/Brand:120",
		_("Value") + ":Currency:120",
		_("Age") + ":Float:120",
	]
	return columns


def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		table = frappe.qb.DocType("Stock Ledger Entry")
		sle_count = flt(
			frappe.qb.from_(table).select(Count(table.name)).where(table.is_cancelled == 0).run()[0][0]
		)
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))


def get_warehouse_list(filters):
	if not filters.get("warehouse"):
		return frappe.get_all(
			"Warehouse",
			filters={"company": filters.get("company"), "is_group": 0},
			fields=["name"],
			order_by="name",
		)

	warehouse = frappe.qb.DocType("Warehouse")
	lft, rgt = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"])

	return (
		frappe.qb.from_(warehouse)
		.select("name")
		.where((warehouse.lft >= lft) & (warehouse.rgt <= rgt))
		.run(as_dict=True)
	)


def add_warehouse_column(columns, warehouse_list):
	if len(warehouse_list) > 1:
		columns += [_("Total Qty") + ":Int:120"]

	for wh in warehouse_list:
		columns += [_(wh.name) + ":Int:100"]


def get_item_warehouse_map(filters, sle):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	for d in sle:
		group_by_key = get_group_by_key(d)
		if group_by_key not in iwb_map:
			iwb_map[group_by_key] = frappe._dict(
				{
					"opening_qty": 0.0,
					"opening_val": 0.0,
					"in_qty": 0.0,
					"in_val": 0.0,
					"out_qty": 0.0,
					"out_val": 0.0,
					"bal_qty": 0.0,
					"bal_val": 0.0,
					"val_rate": 0.0,
				}
			)

		qty_dict = iwb_map[group_by_key]
		if d.voucher_type == "Stock Reconciliation" and not d.batch_no:
			qty_diff = flt(d.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date:
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(qty_diff, float_precision) >= 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	iwb_map = filter_items_with_no_transactions(iwb_map, float_precision)

	return iwb_map


def get_group_by_key(row) -> tuple:
	return (row.company, row.item_code, row.warehouse)
