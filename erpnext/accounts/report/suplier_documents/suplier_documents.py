# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	
	columns = [
		{
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "document_serie",
			"label": _("Document Serie"),
			"fieldtype": "Link",
			"options": "Supplier Documents",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "supplier_rtn",
			"label": _("Supplier RTN"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "document_number",
			"label": _("Document Number"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "document_type",
			"label": _("Type Transaction"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "cai",
			"label": _("CAI"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
	]
	
	data = return_data(filters)

	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)
	documents = frappe.get_all("Supplier Documents", ["*"], filters = conditions)

	for document in documents:
		row = [document.posting_date, document.name, document.status, document.supplier, document.rtn, document.transaction_number, document.type_transaction, document.cai, document.total_exempt]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("type_transaction"): conditions += ', "type_transaction": "{}"'.format(filters.get("type_transaction"))
	if filters.get("supplier"): conditions += ', "supplier": "{}"'.format(filters.get("supplier"))
	if filters.get("status"): conditions += ', "status": "{}"'.format(filters.get("status"))
	conditions += '}'

	return conditions