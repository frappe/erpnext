# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	columns = [
		{
			"label": _("Bank Transactions"),
			"fieldname": "bank_transaction",
			"fieldtype": "Link",
			"options": "Bank Transactions",
			"width": 240
		},
		{
			"label": _("Date"),
			"fieldname": "date",
			"width": 240
		},
		{
			"label": _("No Credit Note"),
			"fieldname": "no_credit_note",
			"width": 240
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Party Name"),
			"fieldname": "party_name",
			"width": 240
		},
		{
			"label": _("Remarks"),
			"fieldname": "remarks",
			"width": 240
		},
		{
			"label": _("Created By"),
			"fieldname": "created_by",
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
		row = [pay.name, pay.check_date_nc, pay.next_note_nc, pay.amount_nc, pay.person_name, pay.movement_detail, pay.created_by]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"check_date_nc": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	# conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "bank_account": "{}"'.format(filters.get("account"))
	conditions += ', "credit_note": 1'
	# conditions += ', "docstatus": 1'
	conditions += '}'

	return conditions
