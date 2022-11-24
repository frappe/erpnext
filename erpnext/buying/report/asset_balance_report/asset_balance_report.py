# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_data(filters):
	data = []
	to_exclude = []
	conditions = get_conditions(filters)
	return frappe.db.sql("""
			SELECT t.item_code, i.item_name, i.asset_category, i.asset_sub_category, t.cost_center, t.warehouse,
			SUM(IFNULL(t.received_qty,0)) total_qty,
			SUM(IFNULL(t.issued_qty,0)) issued_qty,
			SUM(IFNULL(t.received_qty,0))-SUM(IFNULL(t.issued_qty,0)) balance_qty,
			GROUP_CONCAT(IF(IFNULL(t.received_qty, 0)-IFNULL(t.issued_qty, 0) > 0, CONCAT('<a href="desk#Form/Purchase Receipt/',t.ref_doc,'">',t.ref_doc,'(',IFNULL(t.received_qty,0)-IFNULL(t.issued_qty, 0),')','</a>'),NULL)) purchase_receipt
			FROM(
			SELECT ar.item_code, ar.ref_doc, ar.cost_center, (select distinct pr.warehouse from `tabPurchase Receipt Item` pr where pr.parent = ar.ref_doc) as warehouse,
				SUM(ar.qty) received_qty,
				IFNULL((SELECT SUM(ai.qty)
					FROM `tabAsset Issue Details` ai
					WHERE ai.item_code = ar.item_code
					AND ai.issued_date BETWEEN '{from_date}' AND '{to_date}' 
					AND ai.purchase_receipt = ar.ref_doc
					AND ai.docstatus = 1
					),0) issued_qty
			FROM `tabAsset Received Entries` ar
			WHERE ar.received_date BETWEEN '{from_date}' AND '{to_date}'
			AND ar.docstatus = 1
			{cond}
			GROUP BY ar.item_code, ar.ref_doc
			) AS t, `tabItem` i
			WHERE i.name = t.item_code
			GROUP BY  t.item_code, i.item_name
		""".format(from_date=filters.get("from_date"), to_date=filters.get("to_date"), cond = conditions), as_dict=True)
	
def get_conditions(filters):
	if not filters.get("from_date"):
		frappe.throw(_("From Date is mandatory"))
	elif not filters.get("to_date"):
		frappe.throw(_("To Date is mandatory"))
		
	conditions = ""
	if filters.get("branch"):
		conditions += ' and ar.branch = "{}"'.format(filters.get("branch"))
	return conditions

def get_columns():
	return [
		{
		  "fieldname": "item_code",
		  "label": "Material Code",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "item_name",
		  "label": "Material Name",
		  "fieldtype": "Data",
		  "width": 200
		},
		{
		  "fieldname": "asset_category",
		  "label": "Asset Category",
		  "fieldtype": "Link",
		  "options": "Asset Category",
		  "width": 200
		},
		{
		  "fieldname": "asset_sub_category",
		  "label": "Asset Sub Category",
		  "fieldtype": "Data",
		  "width": 200
		},
		{
		  "fieldname": "cost_center",
		  "label": "Cost Center",
		  "fieldtype": "Link",
		  "options": "Cost Center",
		  "width": 200
		},
		{
		  "fieldname": "warehouse",
		  "label": "Warehouse",
		  "fieldtype": "Link",
		  "options": "Warehouse",
		  "width": 200
		},
		{
		  "fieldname": "total_qty",
		  "label": "Total Quantity",
		  "fieldtype": "Int",
		  "width": 120
		},
		{
		  "fieldname": "issued_qty",
		  "label": "Issued Quantity",
		  "fieldtype": "Int",
		  "width": 120
		},
		{
		  "fieldname": "balance_qty",
		  "label": "Balance Quantity",
		  "fieldtype": "Int",
		  "width": 120
		},
		{
			"fieldname": "purchase_receipt",
			"label": "Purchase Receipt",
			"fieldtype": "Data",
			"options": "Purchase Receipt",
			"width": 500
		}
	]
