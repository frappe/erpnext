# Copyright (c) 2017, Velometro Mobility Inc and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import flt, cint
import frappe

def execute(filters=None):
	prod_list = get_production_orders()
	data = get_item_list( prod_list, filters)
	columns = get_columns()
	return columns, data
	
def get_item_list(prod_list, filters):
	out = []
	
	low_price_data = []
	low_supplier = []
	
	# Get the default supplier of suppliers
	#Add a row for each item/qty
	for root in prod_list:
		bom = frappe.db.get_value("Production Order", root.name,"bom_no")
		warehouse = frappe.db.get_value("Production Order", root.name,"source_warehouse")
		warehouse = "Stores - VMI"
		desc = frappe.db.get_value("BOM", bom, "description")
		qty = frappe.db.get_value("Production Order", root.name,"qty")
		
		item_list = frappe.db.sql("""SELECT 
				bom_item.item_code as item_code,
				SUM(ifnull(ledger.actual_qty * conf_ledger.conversion_factor,0))/(bom_item.qty * conf_item.conversion_factor) as build_qty
			FROM
				`tabBOM Item` AS bom_item
				LEFT JOIN `tabBin` AS ledger	
					ON bom_item.item_code = ledger.item_code AND ledger.warehouse = ifnull(%(warehouse)s,%(filterhouse)s)
				LEFT JOIN `tabUOM Conversion Detail` AS conf_item
					ON conf_item.parent = bom_item.item_code  AND conf_item.uom = bom_item.stock_uom
				LEFT JOIN `tabUOM Conversion Detail` AS conf_ledger
					ON conf_ledger.parent = ledger.item_code  AND conf_ledger.uom = ledger.stock_uom
			WHERE
				bom_item.parent = %(bom)s 
			GROUP BY 
				bom_item.item_code""", {"bom": bom, "warehouse": warehouse, "filterhouse": filters.warehouse}, as_dict=1)
		stock_qty = 0
		count = 0
		for item in item_list:
			count = count + 1
			if item.build_qty >= qty:
				stock_qty = stock_qty + 1
		if count == stock_qty:
			build = "Y"
		else:
			build = "N"
		
		row = frappe._dict({
			"production_order": root.name,
			"status": root.status,
			"req_items": cint(count),
			"instock": stock_qty,
			"description": desc,
			"bom_no": bom,
			"qty": qty,
			"ready_to_build": build
		})
		
		out.append(row)

	return out
	
def get_production_orders():
	
	#out = []
	
	
	#prod_list = frappe.db.sql("""select name, status from `tabProduction Order` as prod where status != "Completed" and docstatus = 1""", {}, as_dict=1)
	out =  frappe.get_all("Production Order", filters={"docstatus": 1, "status": ( "!=","Completed")}, fields=["name","status"], order_by='name')
	#prod_list.sort(reverse=False)
	
	#for po in prod_list:
		#out.append(po)

	return out
	
def get_columns():
	columns = [{
		"fieldname": "production_order",
		"label": "Production Order",
		"fieldtype": "Link",
		"options": "Production Order",
		"width": 110
	},{
		"fieldname": "bom_no",
		"label": "BOM",
		"fieldtype": "Link",
		"options": "BOM",
		"width": 130
	},{
		"fieldname": "description",
		"label": "Description",
		"fieldtype": "Data",
		"options": "",
		"width": 250
	},{
		"fieldname": "qty",
		"label": "Qty to Build",
		"fieldtype": "Data",
		"options": "",
		"width": 110
	},{
		"fieldname": "status",
		"label": "Status",
		"fieldtype": "Data",
		"options": "",
		"width": 110
	},{
		"fieldname": "req_items",
		"label": "# of Required Items",
		"fieldtype": "Data",
		"options": "",
		"width": 135
	},{
		"fieldname": "instock",
		"label": "# of In Stock Items",
		"fieldtype": "Data",
		"options": "",
		"width": 135
	},	{
		"fieldname": "ready_to_build",
		"label": "Can Start?",
		"fieldtype": "Data",
		"options": "",
		"width": 75
	}]

	return columns
