# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe import _
from frappe.utils.data import date_diff, today
from datetime import date


def execute(filters=None):
	columns=get_columns(filters)
	data = get_data(filters)
	return columns,data


def get_columns(filters):
	columns=[
			{
				"label": _("Work Order"),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": "Work Order",
				"width": 140
			},
			{
				"label": _("Status"),
				"fieldname": 'status',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Item To Manufacturer "),
				"fieldname": 'production_item',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},
			{
				"label": _("FG Item Name"),
				"fieldname": 'item_name',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("FG Item Qty "),
				"fieldname": 'qty',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("FG item UOM"),
				"fieldname": 'stock_uom',
				"fieldtype": "Data",
				"width": 100
			},

			{
				"label": _("Work Order Item "),
				"fieldname": 'item_code',
				"fieldtype": "Link",
				"options":"Item",
				"width": 100
			},
			{
				"label": _("WO Item Name "),
				"fieldname": 'item_name',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("WO Item Qty"),
				"fieldname": 'required_qty',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("WO Item UOM"),
				"fieldname": 'uom1',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("WO Item stock"),
				"fieldname": 'available_qty_at_source_warehouse',
				"fieldtype": "Link",
				"options":"Batch",
				"width": 100
			},
			{
				"label": _("Alternate Item Name "),
				"fieldname": 'alternative_item_code',
				"fieldtype": "Link",
				"options":"Batch",
				"width": 100
			},
			{
				"label": _("Alternate item stock "),
				"fieldname": 'actual_qty',
				"fieldtype": "Data",
				"width": 100
			},
		
	]
	return columns


def get_condition(filters):

	conditions=" "
	if filters.get("from_date"):
		conditions += " AND ip.planned_start_date>='%s'" % filters.get('from_date')
	if filters.get("to_date"):
		conditions += " AND ip.planned_end_date<='%s'" % filters.get('to_date')
	if filters.get("item_code"):
		conditions += "AND wo.production_item = '%s'" % filters.get('item_code')
	if filters.get("name"):
		conditions += "AND wo.name = '%s'" % filters.get('name')
	return conditions


def get_data(filters):
	
	conditions = get_condition(filters)
	doc = frappe.db.sql("""select wo.name ,wo.status,wo.production_item,wo.item_name,wo.qty,wo.stock_uom,woi.item_code,
						woi.item_name,woi.required_qty,i.stock_uom as uom1,woi.available_qty_at_source_warehouse,
						case
						when ai.alternative_item_code is not null then ai.alternative_item_code
						when ai.alternative_item_code is null then null
						end as alternative_item_code,sum(ledger.actual_qty) as actual_qty
						from `tabWork Order` wo inner Join  `tabWork Order Item` woi ON woi.parent=wo.name
						inner join `tabItem` i ON i.item_code=woi.item_code
						left outer Join `tabItem Alternative` ai ON ai.item_code=woi.item_code 
						left outer Join `tabBin` ledger on ai.alternative_item_code=ledger.item_code and ledger.actual_qty != 0
						left outer JOIN `tabWarehouse` warehouse
							ON warehouse.name = ledger.warehouse
						where wo.docstatus=1 {conditions}
						group by wo.name
						""".format(conditions=conditions),filters, as_dict=1)
	return doc