# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2013, Tristar Enterprises and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import flt

from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.report.stock_balance.stock_balance import (
	get_item_details,
	get_item_warehouse_map,
	get_items,
	get_stock_ledger_entries,
)
from erpnext.stock.utils import is_reposting_item_valuation_in_progress


def execute(filters=None):
	is_reposting_item_valuation_in_progress()
	if not filters:
		filters = {}

	validate_filters(filters)

	columns = get_columns(filters)

	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	item_map = get_item_details(items, sle, filters)
	iwb_map = get_item_warehouse_map(filters, sle)
	warehouse_list = get_warehouse_list(filters)
	item_ageing = FIFOSlots(filters).generate()
	data = []
	item_balance = {}
	item_value = {}

	for (company, item, warehouse) in sorted(iwb_map):
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

	# sum bal_qty by item
	for (item, item_group), wh_balance in item_balance.items():
		if not item_ageing.get(item):
			continue

		total_stock_value = sum(item_value[(item, item_group)])
		row = [item, item_map[item]["item_name"], item_group, total_stock_value]

		fifo_queue = item_ageing[item]["fifo_queue"]
		average_age = 0.00
		if fifo_queue:
			average_age = get_average_age(fifo_queue, filters["to_date"])

		row += [average_age]

		bal_qty = [sum(bal_qty) for bal_qty in zip(*wh_balance)]
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


def get_columns(filters):
	"""return columns"""

	columns = [
		_("Item") + ":Link/Item:150",
		_("Item Name") + ":Link/Item:150",
		_("Item Group") + "::120",
		_("Value") + ":Currency:120",
		_("Age") + ":Float:120",
	]
	return columns


def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = flt(frappe.qb.from_("Stock Ledger Entry").select(Count("name")).run()[0][0])
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))
	if not filters.get("company"):
		filters["company"] = frappe.defaults.get_user_default("Company")


def get_warehouse_list(filters):
	from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

	wh = frappe.qb.DocType("Warehouse")
	query = frappe.qb.from_(wh).select(wh.name).where(wh.is_group == 0)

	user_permitted_warehouse = get_permitted_documents("Warehouse")
	if user_permitted_warehouse:
		query = query.where(wh.name.isin(set(user_permitted_warehouse)))
	elif filters.get("warehouse"):
		query = query.where(wh.name == filters.get("warehouse"))

	return query.run(as_dict=True)


def add_warehouse_column(columns, warehouse_list):
	if len(warehouse_list) > 1:
		columns += [_("Total Qty") + ":Int:120"]

	for wh in warehouse_list:
		columns += [_(wh.name) + ":Int:100"]
