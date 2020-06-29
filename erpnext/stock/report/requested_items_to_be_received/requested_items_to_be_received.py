# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_data(filters,columns)
	return columns, data

def get_columns():
	return [
		{
			"label": _("Material Request"),
			"fieldname": "material_request",
			"fieldtype": "Link",
			"options": "Material Request",
			"width": 130
		},
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130
		},
		{
			"label": _("Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Received Qty"),
			"fieldname": "received_qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Pending Qty"),
			"fieldname": "pending_qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 130
		},
	]

def get_data(filters,columns):
	condition = ''
	if 'company' in filters:
		condition += 'and company = "' + filters['company'] + '" '
	if 'item_code' in filters:
		condition += 'and item_code = "' + filters['item_code'] + '"'
	data = frappe.db.sql(
		"""
		select 
			mr.name as "material_request",
			mr.transaction_date as "date",
			mr_item.item_code as "item_Code",
			mr_item.qty as "qty",
			mr_item.received_qty as "received_qty", 
			(mr_item.qty - ifnull(mr_item.received_qty, 0)) as "pending_qty",
			mr_item.item_name as "item_name",
			mr_item.description as "description",
			mr.company as "company"
		from
			`tabMaterial Request` mr, `tabMaterial Request Item` mr_item
		where
			mr_item.parent = mr.name
			and mr.material_request_type = "Purchase"
			and mr.docstatus = 1
			and ifnull(mr_item.received_qty, 0) < ifnull(mr_item.qty, 0)
			{0}
		order by mr.transaction_date desc
		""".format(condition), as_dict=True)
	return data