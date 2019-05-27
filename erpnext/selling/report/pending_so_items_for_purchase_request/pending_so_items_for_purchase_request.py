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
			"fieldname": "material_request",
			"fieldtype": "Data",
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
	sales_order_entry = frappe.db.sql("""
		SELECT
			so_item.item_code,
			so_item.item_name,
			so_item.description,
			so.name,
			so.transaction_date,
			so.customer,
			so.territory,
			sum(so_item.qty) as net_qty,
			so.company
		FROM `tabSales Order` so, `tabSales Order Item` so_item
		WHERE
			so.docstatus = 1
			and so.name = so_item.parent
			and so.status not in  ("Closed","Completed","Cancelled")
		GROUP BY
			so.name,so_item.item_code
		""", as_dict = 1)

	mr_records = frappe.get_all("Material Request Item",
		{"sales_order_item": ("!=",""), "docstatus": 1},
		["parent", "qty", "sales_order", "item_code"])

	materials_request_dict = {}

	for record in mr_records:
		key = (record.sales_order, record.item_code)
		if key not in materials_request_dict:
			materials_request_dict.setdefault(key, {
				'qty': 0,
				'material_requests': [record.parent]
			})

		details = materials_request_dict.get(key)
		details['qty'] += record.qty

		if record.parent not in details.get('material_requests'):
			details['material_requests'].append(record.parent)

	pending_so=[]
	for so in sales_order_entry:
		# fetch all the material request records for a sales order item
		key = (so.name, so.item_code)
		materials_request = materials_request_dict.get(key) or {}

		# check for pending sales order
		if cint(so.net_qty) > cint(materials_request.get('qty')):
			so_record = {
				"item_code": so.item_code,
				"item_name": so.item_name,
				"description": so.description,
				"sales_order_no": so.name,
				"date": so.transaction_date,
				"material_request": ','.join(materials_request.get('material_requests', [])),
				"customer": so.customer,
				"territory": so.territory,
				"so_qty": so.net_qty,
				"requested_qty": cint(materials_request.get('qty')),
				"pending_qty": so.net_qty - cint(materials_request.get('qty')),
				"company": so.company
			}
			pending_so.append(so_record)
	return pending_so