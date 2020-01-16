# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	columns = [{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 120
		}]
	
	if not filters.get('bom_no'):
		columns.extend([
			{
				"label": _("BOM No"),
				"fieldname": "bom_no",
				"fieldtype": "Link",
				"options": "BOM",
				"width": 180
			}
		])
	
	columns.extend([
		{
			"label": _("Finished Good"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"label": _("Ordered Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 120
		},
		{
			"label": _("Produced Qty"),
			"fieldname": "produced_qty",
			"fieldtype": "Float",
			"width": 120
		},
		{
			"label": _("Raw Material"),
			"fieldname": "raw_material_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"label": _("Required Qty"),
			"fieldname": "required_qty",
			"fieldtype": "Float",
			"width": 120
		},
		{
			"label": _("Consumed Qty"),
			"fieldname": "consumed_qty",
			"fieldtype": "Float",
			"width": 120
		}
	])

	return columns
	
def get_data(filters):
	cond = "1=1"

	if filters.get('bom_no') and not filters.get('work_order'):
		cond += " and bom_no = '%s'" % filters.get('bom_no')

	if filters.get('work_order'):
		cond += " and name = '%s'" % filters.get('work_order')

	results = []
	for d in frappe.db.sql(""" select name as work_order, qty, produced_qty, production_item, bom_no
		from `tabWork Order` where produced_qty > qty and docstatus = 1 and {0}""".format(cond), as_dict=1):
		results.append(d)

		for data in frappe.get_all('Work Order Item', fields=["item_code as raw_material_code",
			"required_qty", "consumed_qty"], filters={'parent': d.work_order, 'parenttype': 'Work Order'}):
			results.append(data)

	return results

@frappe.whitelist()
def get_work_orders(doctype, txt, searchfield, start, page_len, filters):
	cond = "1=1"
	if filters.get('bom_no'):
		cond += " and bom_no = '%s'" % filters.get('bom_no')

	return frappe.db.sql("""select name from `tabWork Order`
		where name like %(name)s and {0} and produced_qty > qty and docstatus = 1
		order by name limit {1}, {2}""".format(cond, start, page_len),{
			'name': "%%%s%%" % txt
		}, as_list=1)
