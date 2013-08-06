# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters)
	
	data = []
	for company in sorted(iwb_map):
		for item in sorted(iwb_map[company]):
			for wh in sorted(iwb_map[company][item]):
				qty_dict = iwb_map[company][item][wh]
				data.append([item, item_map[item]["item_name"], 
					item_map[item]["description"], wh, 
					qty_dict.opening_qty, qty_dict.in_qty, 
					qty_dict.out_qty, qty_dict.bal_qty, company
				])
	
	return columns, data

def get_columns(filters):
	"""return columns based on filters"""
	
	columns = ["Item:Link/Item:100", "Item Name::150", "Description::150", \
	"Warehouse:Link/Warehouse:100", "Opening Qty:Float:90", \
	"In Qty:Float:80", "Out Qty:Float:80", "Balance Qty:Float:90", "Company:Link/Company:100"]

	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		webnotes.msgprint("Please enter From Date", raise_exception=1)

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % filters["to_date"]
	else:
		webnotes.msgprint("Please enter To Date", raise_exception=1)
		
	return conditions

#get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return webnotes.conn.sql("""select item_code, warehouse, 
		posting_date, actual_qty, company 
		from `tabStock Ledger Entry` 
		where ifnull(is_cancelled, 'No') = 'No' %s order by item_code, warehouse""" %
		conditions, as_dict=1)

def get_item_warehouse_map(filters):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	for d in sle:
		iwb_map.setdefault(d.company, {}).setdefault(d.item_code, {}).\
		setdefault(d.warehouse, webnotes._dict({\
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
			}))
		qty_dict = iwb_map[d.company][d.item_code][d.warehouse]
		if d.posting_date < filters["from_date"]:
			qty_dict.opening_qty += flt(d.actual_qty)
		elif d.posting_date >= filters["from_date"] and d.posting_date <= filters["to_date"]:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty += flt(d.actual_qty)
			else:
				qty_dict.out_qty += abs(flt(d.actual_qty))

		qty_dict.bal_qty += flt(d.actual_qty)

	return iwb_map

def get_item_details(filters):
	item_map = {}
	for d in webnotes.conn.sql("select name, item_name, description from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map