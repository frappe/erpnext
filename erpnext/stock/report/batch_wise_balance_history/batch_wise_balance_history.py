# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters)

	data = []
	for item in sorted(iwb_map):
		for wh in sorted(iwb_map[item]):
			for batch in sorted(iwb_map[item][wh]):
				qty_dict = iwb_map[item][wh][batch]
				data.append([item, item_map[item]["item_name"],
					item_map[item]["description"], wh, batch,
					qty_dict.opening_qty, qty_dict.in_qty,
					qty_dict.out_qty, qty_dict.bal_qty
				])

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item") + ":Link/Item:100"] + [_("Item Name") + "::150"] + [_("Description") + "::150"] + \
	[_("Warehouse") + ":Link/Warehouse:100"] + [_("Batch") + ":Link/Batch:100"] + [_("Opening Qty") + "::90"] + \
	[_("In Qty") + "::80"] + [_("Out Qty") + "::80"] + [_("Balance Qty") + "::90"]

	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))

	return conditions

#get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select item_code, batch_no, warehouse,
		posting_date, actual_qty
		from `tabStock Ledger Entry`
		where docstatus < 2 %s order by item_code, warehouse""" %
		conditions, as_dict=1)

def get_item_warehouse_batch_map(filters):
	float_precision = cint(frappe.db.get_default("float_precision")) or 3
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < filters["from_date"]:
			qty_dict.opening_qty += flt(d.actual_qty, float_precision)
		elif d.posting_date >= filters["from_date"] and d.posting_date <= filters["to_date"]:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty += flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty += abs(flt(d.actual_qty, float_precision))

		qty_dict.bal_qty += flt(d.actual_qty, float_precision)

	return iwb_map

def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_name, description from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map
