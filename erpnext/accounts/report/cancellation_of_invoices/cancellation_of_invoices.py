# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	
	columns = [
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Data",
			"width": 240
		},
		{
			"fieldname": "entry",
			"label": _("Document"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 300
		},
		{
			"fieldname": "total_amount",
			"label": _("Total Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "reason_for_return",
			"label": _("Reason For Cancellation"),
			"fieldtype": "Data",
			"width": 240
		},
		{
			"fieldname": "cashier",
			"label": _("Cashier"),
			"fieldtype": "Data",
			"width": 240
		},
	]
	data = return_data(filters)

	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)
	cancellations = frappe.get_all("Cancellation Of Invoices", ["*"], filters = conditions)

	for cancellation in cancellations:
		invoice = frappe.get_doc("Sales Invoice", cancellation.sale_invoice)

		row = [invoice.posting_date, invoice.name, invoice.rounded_total, cancellation.reason_for_return, invoice.cashier]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "docstatus": 1'
	if filters.get("reason_for_return"): conditions += ', "reason_for_return": "{}"'.format(filters.get("reason_for_return"))
	conditions += '}'

	return conditions