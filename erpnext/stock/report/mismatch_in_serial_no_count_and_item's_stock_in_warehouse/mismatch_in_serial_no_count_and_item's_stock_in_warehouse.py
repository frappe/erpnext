# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	print(filters)
	columns = get_columns()
	data = get_data(filters.warehouse)
	return columns, data

def get_columns():
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Total no of Serial Nos"),
			"fieldname": "total",
			"fieldtype": "Float",
			"width": 150
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "balance",
			"fieldtype": "Float",
			"width": 150
		},
		{
			"label": _("Difference"),
			"fieldname": "difference",
			"fieldtype": "Float",
			"width": 150
		},
	]

	return columns

def get_data(warehouse):
	serial_item_list = frappe.get_all("Item", filters={
		'has_serial_no': True,
	}, fields=['item_code', 'item_name'])

	data = []
	for item in serial_item_list:
		total_serial_no = frappe.db.count("Serial No", filters={"item_code": item.item_code, "status": "Active", "warehouse": warehouse})

		if not total_serial_no:
			total_serial_no = 0

		actual_qty = frappe.db.get_value('Bin', fieldname=['actual_qty'], filters={"warehouse": warehouse, "item_code": item.item_code})

		if not actual_qty:
			actual_qty = 0

		difference = total_serial_no - actual_qty

		row = {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"total": total_serial_no,
			"balance": actual_qty,
			"difference": difference,
		}

		data.append(row)

	return data