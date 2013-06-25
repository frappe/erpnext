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
from webnotes.utils import cint

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	item_warehouse_quantity_map = get_item_warehouse_quantity_map()

	data = []
	for item, warehouse in item_warehouse_quantity_map.items():
		item_details = get_item_details(item)[0]
		total = 0
		total_qty = 0
		for wh, item_qty in warehouse.items():
			total += 1
			row = [item, item_details.item_name, item_details.description, \
			item_details.stock_uom, wh]
			for quantity in item_qty.items():
				max_qty = []
				max_qty.append(quantity[1])
			max_qty = min(max_qty)
			total_qty += cint(max_qty.qty)
			row += [max_qty.qty]
			data.append(row)
			if (total == len(warehouse)):
				row = ["", "", "Total", "", "", total_qty]
				data.append(row)

	return columns, data
	
def get_columns():
	columns = ["Item Code:Link/Item:100", "Item Name::100", "Description::120", \
			"UOM:Link/UOM:80", "Warehouse:Link/Warehouse:100", "Quantity::100"]

	return columns

def get_sales_bom():
	return webnotes.conn.sql("""select name from `tabSales BOM`""",	as_dict=1)

def get_sales_bom_items(item):
	return webnotes.conn.sql("""select parent, item_code, qty from `tabSales BOM Item` 
		where parent=%s""", (item), as_dict=1)

def get_item_details(item):
	return webnotes.conn.sql("""select name, item_name, description, stock_uom 
		from `tabItem` where name=%s""", (item), as_dict=1)

def get_item_warehouse_quantity(item):
	return webnotes.conn.sql("""select item_code, warehouse, actual_qty from `tabBin` 
		where item_code=%s""", (item), as_dict=1)

def get_item_warehouse_quantity_map():
	iwq_map = {}

	sales_bom = get_sales_bom()

	for item in sales_bom:
		child_item = get_sales_bom_items(item.name)
		for child in child_item:
			item_warehouse_quantity = get_item_warehouse_quantity(child.item_code)
			for iwq in item_warehouse_quantity:
				iwq_map.setdefault(item.name, {}).setdefault(iwq.warehouse, {}).\
				setdefault(child.item_code, webnotes._dict({
					"qty" : 0
				}))

				q_dict = iwq_map[item.name][iwq.warehouse][child.item_code]
				
				q_dict.qty = cint(iwq.actual_qty / child.qty)

	return iwq_map