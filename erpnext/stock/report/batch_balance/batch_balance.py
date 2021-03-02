# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate

def execute(filters=None):
	if not filters: filters = {}

	db_qty_precision = 6 if cint(frappe.db.get_default("float_precision")) <= 6 else 9

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters)

	data = []
	for item in sorted(iwb_map):
		for wh in sorted(iwb_map[item]):
			for batch in sorted(iwb_map[item][wh]):
				qty_dict = iwb_map[item][wh][batch]
				if flt(qty_dict.bal_qty, db_qty_precision) or not filters.get('hide_empty_batches'):
					if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
						data.append([item, item_map[item]["item_name"], wh, batch,
							flt(qty_dict.opening_qty, db_qty_precision), flt(qty_dict.in_qty, db_qty_precision),
							flt(qty_dict.out_qty, db_qty_precision), flt(qty_dict.bal_qty, db_qty_precision),
							 item_map[item]["stock_uom"]
						])

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item") + ":Link/Item:100"] + [_("Item Name") + "::150"] + \
	[_("Warehouse") + ":Link/Warehouse:120"] + [_("Batch") + ":Link/Batch:140"] + [_("Opening Qty") + ":Float:90"] + \
	[_("In Qty") + ":Float:80"] + [_("Out Qty") + ":Float:80"] + [_("Balance Qty") + ":Float:90"] + \
	[_("UOM") + "::90"]


	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= %(to_date)s"
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get("batch_no"):
		conditions += " and batch_no = %(batch_no)s"

	if filters.get("warehouse"):
		conditions += " and warehouse = %(warehouse)s"

	return conditions

def get_item_conditions(filters):
	from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_source"):
			conditions.append("item.item_source=%(item_source)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	item_conditions_sql = ''
	if items:
		item_conditions_sql = ' and sle.item_code in ({})' \
			.format(', '.join([frappe.db.escape(i) for i in items]))

	return item_conditions_sql

# get all details
def get_stock_ledger_entries(filters):
	item_conditions = get_item_conditions(filters)
	conditions = get_conditions(filters)

	return frappe.db.sql("""select item_code, batch_no, warehouse,
		posting_date, actual_qty
		from `tabStock Ledger Entry` sle
		where docstatus < 2 and ifnull(batch_no, '') != '' {0} {1} order by item_code, warehouse
		""".format(conditions, item_conditions), filters, as_dict=1)

def get_item_warehouse_batch_map(filters):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < from_date:
			qty_dict.opening_qty = qty_dict.opening_qty + d.actual_qty
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = qty_dict.in_qty + d.actual_qty
			else:
				qty_dict.out_qty = qty_dict.out_qty + abs(d.actual_qty)

		qty_dict.bal_qty = qty_dict.bal_qty + d.actual_qty

	return iwb_map

def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_name, description, stock_uom from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map
