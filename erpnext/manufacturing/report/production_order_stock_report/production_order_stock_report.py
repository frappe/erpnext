# Copyright (c) 2017, Velometro Mobility Inc and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import flt, cint
import frappe

def execute(filters=None):
	prod_list = get_production_orders()
	data = get_item_list(prod_list, filters)
	columns = get_columns()
	return columns, data
	
def get_item_list(prod_list, filters):
	out = []
	
	low_price_data = []
	low_supplier = []
	
	#Add a row for each item/qty
	for prod_order in prod_list:
		bom = frappe.db.get_value("Production Order", prod_order.name, "bom_no")
		warehouse = frappe.db.get_value("Production Order", prod_order.name, "source_warehouse")
		desc = frappe.db.get_value("BOM", bom, "description")
		qty = frappe.db.get_value("Production Order", prod_order.name, "qty")
		produced_value = frappe.db.get_value("Production Order", prod_order.name, "produced_qty")
		item_list = frappe.db.sql("""SELECT 
				bom_item.item_code as item_code,
				ifnull(ledger.actual_qty,0)/(bom_item.qty) as build_qty
			FROM
				`tabBOM Item` AS bom_item
				LEFT JOIN `tabBin` AS ledger	
					ON bom_item.item_code = ledger.item_code 
					AND ledger.warehouse = ifnull(%(warehouse)s,%(filterhouse)s)
			WHERE
				bom_item.parent = %(bom)s 
			GROUP BY 
				bom_item.item_code""", {"bom": bom, "warehouse": warehouse, "filterhouse": filters.warehouse}, as_dict=1)
		stock_qty = 0
		count = 0
		buildable_qty = qty
		for item in item_list:
			count = count + 1
			if item.build_qty >= (qty-produced_value):
				stock_qty = stock_qty + 1
			elif buildable_qty > item.build_qty:
				buidable_qty = item.build_qty
					
		if count == stock_qty:
			build = "Y"
		else:
			build = "N"
		
		row = frappe._dict({
			"production_order": prod_order.name,
			"status": prod_order.status,
			"req_items": cint(count),
			"instock": stock_qty,
			"description": desc,
			"bom_no": bom,
			"qty": qty,
			"buildable_qty": buildable_qty,
			"ready_to_build": build
		})
		
		out.append(row)

	return out
	
def get_production_orders():
	
	out =  frappe.get_all("Production Order", filters={"docstatus": 1, "status": ( "!=","Completed")}, fields=["name","status"], order_by='name')
	return out
	
def get_columns():
	columns = [{
		"fieldname": "production_order",
		"label": "Production Order",
		"fieldtype": "Link",
		"options": "Production Order",
		"width": 110
	}, {
		"fieldname": "bom_no",
		"label": "BOM",
		"fieldtype": "Link",
		"options": "BOM",
		"width": 130
	}, {
		"fieldname": "description",
		"label": "Description",
		"fieldtype": "Data",
		"options": "",
		"width": 250
	}, {
		"fieldname": "qty",
		"label": "Qty to Build",
		"fieldtype": "Data",
		"options": "",
		"width": 110
	}, {
		"fieldname": "status",
		"label": "Status",
		"fieldtype": "Data",
		"options": "",
		"width": 110
	}, {
		"fieldname": "req_items",
		"label": "# of Required Items",
		"fieldtype": "Data",
		"options": "",
		"width": 135
	}, {
		"fieldname": "instock",
		"label": "# of In Stock Items",
		"fieldtype": "Data",
		"options": "",
		"width": 135
	}, {
		"fieldname": "ready_to_build",
		"label": "Can Start?",
		"fieldtype": "Data",
		"options": "",
		"width": 75
	}]

	return columns
