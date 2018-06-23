# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	iwq_map = get_item_warehouse_quantity_map()
	item_map = get_item_details()

	data = []	
	for sbom, warehouse in iwq_map.items():
		total = 0
		total_qty = 0
		
		for wh, item_qty in warehouse.items():
			total += 1
			row = [sbom, item_map.get(sbom).item_name, item_map.get(sbom).description, 
				item_map.get(sbom).stock_uom, wh]
			available_qty = min(item_qty.values())
			total_qty += flt(available_qty)
			row += [available_qty]
			
			if available_qty:
				data.append(row)
				if (total == len(warehouse)):
					row = ["", "", "Total", "", "", total_qty]
					data.append(row)

	return columns, data
	
def get_columns():
	columns = ["Item Code:Link/Item:100", "Item Name::100", "Description::120", \
			"UOM:Link/UOM:80", "Warehouse:Link/Warehouse:100", "Quantity::100"]

	return columns

def get_product_bundle_items():
	sbom_item_map = {}
	for sbom in frappe.db.sql("""select pb.new_item_code as parent, pbi.item_code, pbi.qty 
			from `tabProduct Bundle Item` as pbi, `tabProduct Bundle` as pb
		where pb.docstatus < 2 and pb.name = pbi.parent""", as_dict=1):
			sbom_item_map.setdefault(sbom.parent, {}).setdefault(sbom.item_code, sbom.qty)
			
	return sbom_item_map

def get_item_details():
	item_map = {}
	for item in frappe.db.sql("""select name, item_name, description, stock_uom 
		from `tabItem`""", as_dict=1):
			item_map.setdefault(item.name, item)
			
	return item_map

def get_item_warehouse_quantity():
	iwq_map = {}
	bin = frappe.db.sql("""select item_code, warehouse, actual_qty from `tabBin` 
		where actual_qty > 0""")
	for item, wh, qty in bin:
		iwq_map.setdefault(item, {}).setdefault(wh, qty)
		
	return iwq_map

def get_item_warehouse_quantity_map():
	sbom_map = {}
	iwq_map = get_item_warehouse_quantity()
	sbom_item_map = get_product_bundle_items()
	
	for sbom, sbom_items in sbom_item_map.items():
		for item, child_qty in sbom_items.items():
			for wh, qty in iwq_map.get(item, {}).items():
				avail_qty = flt(qty) / flt(child_qty)
				sbom_map.setdefault(sbom, {}).setdefault(wh, {}) \
					.setdefault(item, avail_qty)

	return sbom_map