# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
		
	data = frappe.db.sql("""select 
			item.name, item.item_name, description, item_group, brand, warehouse, item.stock_uom, 
			actual_qty, planned_qty, indented_qty, ordered_qty, reserved_qty, 
			projected_qty, item.re_order_level, item.re_order_qty, 
			(item.re_order_level - projected_qty) as shortage_qty
		from `tabBin` bin, 
			(select name, company from tabWarehouse 
				{warehouse_conditions}) wh,
			(select name, item_name, description, stock_uom, item_group, 
				brand, re_order_level, re_order_qty 
				from `tabItem` {item_conditions}) item
		where item_code = item.name and warehouse = wh.name
		order by item.name, wh.name"""\
		.format(item_conditions=get_item_conditions(filters),
			warehouse_conditions=get_warehouse_conditions(filters)), filters)
	
	return columns, data
	
def get_columns():
	return [_("Item Code") + ":Link/Item:140", _("Item Name") + "::100", _("Description") + "::200", 
		_("Item Group") + ":Link/Item Group:100", _("Brand") + ":Link/Brand:100", _("Warehouse") + ":Link/Warehouse:120", 
		_("UOM") + ":Link/UOM:100", _("Actual Qty") + ":Float:100", _("Planned Qty") + ":Float:100", 
		_("Requested Qty") + ":Float:110", _("Ordered Qty") + ":Float:100", _("Reserved Qty") + ":Float:100", 
		_("Projected Qty") + ":Float:100", _("Reorder Level") + ":Float:100", _("Reorder Qty") + ":Float:100", 
		_("Shortage Qty") + ":Float:100"]
	
def get_item_conditions(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("name=%(item_code)s")
	if filters.get("brand"):
		conditions.append("brand=%(brand)s")
	
	return "where {}".format(" and ".join(conditions)) if conditions else ""
	
def get_warehouse_conditions(filters):
	conditions = []
	if filters.get("company"):
		conditions.append("company=%(company)s")
	if filters.get("warehouse"):
		conditions.append("name=%(warehouse)s")
		
	return "where {}".format(" and ".join(conditions)) if conditions else ""