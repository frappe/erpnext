# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

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

def get_sales_bom_items():
	sbom_item_map = {}
	for sbom in webnotes.conn.sql("""select parent, item_code, qty from `tabSales BOM Item` 
		where docstatus < 2""", as_dict=1):
			sbom_item_map.setdefault(sbom.parent, {}).setdefault(sbom.item_code, sbom.qty)
			
	return sbom_item_map

def get_item_details():
	item_map = {}
	for item in webnotes.conn.sql("""select name, item_name, description, stock_uom 
		from `tabItem`""", as_dict=1):
			item_map.setdefault(item.name, item)
			
	return item_map

def get_item_warehouse_quantity():
	iwq_map = {}
	bin = webnotes.conn.sql("""select item_code, warehouse, actual_qty from `tabBin` 
		where actual_qty > 0""")
	for item, wh, qty in bin:
		iwq_map.setdefault(item, {}).setdefault(wh, qty)
		
	return iwq_map

def get_item_warehouse_quantity_map():
	sbom_map = {}
	iwq_map = get_item_warehouse_quantity()
	sbom_item_map = get_sales_bom_items()
	
	for sbom, sbom_items in sbom_item_map.items():
		for item, child_qty in sbom_items.items():
			for wh, qty in iwq_map.get(item, {}).items():
				avail_qty = flt(qty) / flt(child_qty)
				sbom_map.setdefault(sbom, {}).setdefault(wh, {}) \
					.setdefault(item, avail_qty)

	return sbom_map