# Copyright (c) 2017, Velometro Mobility Inc and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import flt, cint
import frappe

def execute(filters=None):
	
	
	prod_list = get_production_orders()
	
	data = get_item_list( prod_list)
	
	columns = get_columns()
	
	return columns, data

	
def get_item_list(prod_list):
	
	out = []
	
	low_price_data = []
	low_supplier = []
	company = frappe.db.get_default("company")
	float_precision = cint(frappe.db.get_default("float_precision")) or 2
	company_currency = frappe.db.get_default("currency")
	# Get the default supplier of suppliers
	
		
	#Add a row for each item/qty
	for root in prod_list:
		bom = frappe.db.get_value("Production Order", root.name,"bom_no")
		desc = frappe.db.get_value("BOM", bom, "description")
		qty = frappe.db.get_value("Production Order", root.name,"qty")
		
		item_list = frappe.db.sql("""	SELECT 
											bom_item.item_code as item_code,
											SUM(ifnull(ledger.actual_qty,0))/bom_item.qty as build_qty
										FROM
											`tabBOM Item` AS bom_item 
											LEFT JOIN `tabStock Ledger Entry` AS ledger	
											ON bom_item.item_code = ledger.item_code 
										WHERE
											bom_item.parent=%(bom)s 
										GROUP BY 
											bom_item.item_code""", {"bom": bom}, as_dict=1)
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
			"ready_to_build": build
		})
		
		out.append(row)

	return out
	
def get_production_orders():
	
	out = []
	
	
	prod_list = frappe.db.sql("""select name, status from `tabProduction Order` as prod where status != "Completed" and docstatus = 1""", {}, as_dict=1)
	prod_list.sort(reverse=False)
	
	for po in prod_list:
		out.append(po)

	return out
	
def get_columns():
	columns = [{
		"fieldname": "production_order",
		"label": "Production Order",
		"fieldtype": "Link",
		"options": "Production Order",
		"width": 120
	},{
		"fieldname": "bom_no",
		"label": "BOM",
		"fieldtype": "Link",
		"options": "BOM",
		"width": 150
	},{
		"fieldname": "description",
		"label": "Description",
		"fieldtype": "Data",
		"options": "",
		"width": 275
	},{
		"fieldname": "status",
		"label": "Status",
		"fieldtype": "Data",
		"options": "",
		"width": 120
	},{
		"fieldname": "req_items",
		"label": "# of Required Items",
		"fieldtype": "Data",
		"options": "",
		"width": 150
	},{
		"fieldname": "instock",
		"label": "# of In Stock Items",
		"fieldtype": "Data",
		"options": "",
		"width": 150
	},	{
		"fieldname": "ready_to_build",
		"label": "Can Start?",
		"fieldtype": "Data",
		"options": "",
		"width": 80
	}]

	return columns
