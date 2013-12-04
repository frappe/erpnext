# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

def execute(filters=None):
	columns = get_columns()
	if not filters.get("company"):
		webnotes.throw(_("Company is mandatory"))
		
	data = webnotes.conn.sql("""select 
			item.name, item.item_name, description, brand, warehouse, item.stock_uom, 
			actual_qty, planned_qty, indented_qty, ordered_qty, reserved_qty, 
			projected_qty, item.re_order_level, item.re_order_qty
		from `tabBin` bin, 
			(select name, company from tabWarehouse {warehouse_conditions}) wh,
			(select name, item_name, description, stock_uom, brand, re_order_level, re_order_qty
				from `tabItem` {item_conditions}) item
		where item_code = item.name and warehouse = wh.name
		order by item.name, wh.name"""\
		.format(item_conditions=get_item_conditions(filters),
			warehouse_conditions=get_warehouse_conditions(filters)), filters, debug=1)
	
	return columns, data
	
def get_columns():
	return ["Item Code:Link/Item:140", "Item Name::100", "Description::200", 
		"Brand:Link/Brand:100", "Warehouse:Link/Warehouse:120", "UOM:Link/UOM:100", 
		"Actual Qty:Float:100", "Planned Qty:Float:100", "Requested Qty:Float:110", 
		"Ordered Qty:Float:100", "Reserved Qty:Float:100", "Projected Qty:Float:100", 
		"Reorder Level:Float:100", "Reorder Qty:Float:100"]
	
def get_item_conditions(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("name=%(item_code)s")
	if filters.get("brand"):
		conditions.append("brand=%(brand)s")
	
	return "where {}".format(" and ".join(conditions)) if conditions else ""
	
def get_warehouse_conditions(filters):
	conditions = []
	if not filters.get("company"):
		webnotes.throw(_("Company is mandatory"))
	else:
		conditions.append("company=%(company)s")
		
	if filters.get("warehouse"):
		conditions.append("name=%(warehouse)s")
	
	return "where {}".format(" and ".join(conditions)) if conditions else ""