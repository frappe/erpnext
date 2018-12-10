# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2013, Tristar Enterprises and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate
from erpnext.stock.report.stock_balance.stock_balance import get_item_details, get_item_reorder_details, get_item_warehouse_map
from erpnext.stock.report.stock_ageing.stock_ageing import get_fifo_queue, get_average_age
from six import iteritems

def execute(filters=None):
	if not filters: filters = {}

	validate_filters(filters)

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters)
	warehouse_list = get_warehouse_list(filters)
	item_ageing = get_fifo_queue(filters)
	data = []
	item_balance = {}
	item_value = {}

	for (company, item, warehouse) in sorted(iwb_map):
		row = []
		qty_dict = iwb_map[(company, item, warehouse)]
		item_balance.setdefault((item, item_map[item]["item_group"]), [])
		total_stock_value = 0.00
		for wh in warehouse_list:
			row += [qty_dict.bal_qty] if wh.name in warehouse else [0.00]
			total_stock_value += qty_dict.bal_val if wh.name in warehouse else 0.00

		item_balance[(item, item_map[item]["item_group"])].append(row)
		item_value.setdefault((item, item_map[item]["item_group"]),[])
		item_value[(item, item_map[item]["item_group"])].append(total_stock_value)


	# sum bal_qty by item
	for (item, item_group), wh_balance in iteritems(item_balance):
		total_stock_value = sum(item_value[(item, item_group)])
		row = [item, item_group, total_stock_value]

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
		_("Item")+":Link/Item:180",
		_("Item Group")+"::100",
		_("Value")+":Currency:100",
		_("Age")+":Float:60",
	]
	return columns

def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))
	if not filters.get("company"):
		filters["company"] = frappe.defaults.get_user_default("Company")

def get_warehouse_list(filters):
	from frappe.defaults import get_user_permissions
	condition = ''
	user_permitted_warehouse = [d.get('doc') for d in get_user_permissions().get('Warehouse', []) \
		if d.get('doc')]
	value = ()
	if user_permitted_warehouse:
		condition = "and name in %s"
		value = set(user_permitted_warehouse)
	elif not user_permitted_warehouse and filters.get("warehouse"):
		condition = "and name = %s"
		value = filters.get("warehouse")

	return frappe.db.sql("""select name
		from `tabWarehouse` where is_group = 0
		{condition}""".format(condition=condition), value, as_dict=1)

def add_warehouse_column(columns, warehouse_list):
	if len(warehouse_list) > 1:
		columns += [_("Total Qty")+":Int:50"]

	for wh in warehouse_list:
		columns += [_(wh.name)+":Int:54"]
