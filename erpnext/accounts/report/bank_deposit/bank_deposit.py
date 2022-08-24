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
			"width": 240
		},
		{
			"fieldname": "document_number",
			"label": _("No Document"),
			"fieldtype": "Link",
			"options": "Bank Transactions",
			"width": 300
		},
		{
			"fieldname": "no_bank_deposit",
			"label": _("No Bank Deposit"),
			"fieldtype": "Data",
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
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Data",
			"width": 240
		},

		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 240
		},

		{
			"fieldname": "created_by",
			"label": _("Created By"),
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

	payments = frappe.get_all("Bank Transactions", ["*"], filters = conditions)

	for pay in payments:
		row = [pay.deposit_date, pay.name, pay.document, pay.amount_bd, pay.person_name, pay.movement_detail, pay.created_by]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"deposit_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	# conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "bank_account": "{}"'.format(filters.get("account"))
	conditions += ', "bank_deposit": 1'
	# conditions += ', "docstatus": 1'
	conditions += '}'

	return conditions
