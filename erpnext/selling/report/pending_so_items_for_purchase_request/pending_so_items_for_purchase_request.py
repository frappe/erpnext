# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint,cstr

def execute(filters=None):
	columns = get_columns()
	data = get_data()
	return columns, data

def get_columns():
	columns = [
		{
			"label": _("Item Code"),
			"options": "Item",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"width": 200
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("S.O. No."),
			"options": "Sales Order",
			"fieldname": "sales_order_no",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 140
		},
		{
			"label": _("Material Request"),
			"options": "Material Request",
			"fieldname": "material_request",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("SO Qty"),
			"fieldname": "so_qty",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Requested Qty"),
			"fieldname": "requested_qty",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Pending Qty"),
			"fieldname": "pending_qty",
			"fieldtype": "Float",
			"width": 140
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Data",
			"width": 140
		}
	]
	return columns

def get_data():
	sales_order_entry = frappe.db.sql("""select  so_item.item_code,
					so_item.item_name,
					so_item.description,
					so.name,
					so.transaction_date,
					so.customer,
					so.territory,
					sum(so_item.qty) as net_qty,
					so.company
					from `tabSales Order` so, `tabSales Order Item` so_item 
					where so.docstatus = 1
					and so.name = so_item.parent
					and so.status not in  ("Closed","Completed","Cancelled")
					group by so.name,so_item.item_code 	
					""", as_dict = 1)

	mr_records = frappe.get_all("Material Request Item", 
		{"sales_order_item": ("!=",""), "docstatus": 1}, 
		["parent", "qty", "sales_order", "item_code"])

	grouped_records = {}

	for record in mr_records:
		grouped_records.setdefault(record.sales_order, []).append(record)

	pending_so=[]
	for so in sales_order_entry:
		mr_list = grouped_records.get(so.name) or [{}]				
		mr_item_record = ([mr for mr in mr_list if mr.get('item_code') == so.item_code] or [{}])

		for mr in mr_item_record:
			if cint(so.net_qty) > cint(mr.get('qty')):
				so_record = {
					"item_code": so.item_code,
					"item_name": so.item_name,
					"description": so.description,
					"sales_order_no": so.name,
					"date": so.transaction_date,
					"material_request": cstr(mr.get('parent')),
					"customer": so.customer,
					"territory": so.territory,  
					"so_qty": so.net_qty, 
					"requested_qty": cint(mr.get('qty')),
					"pending_qty": so.net_qty - cint(mr.get('qty')),
					"company": so.company
				}
				pending_so.append(so_record)
	return pending_so