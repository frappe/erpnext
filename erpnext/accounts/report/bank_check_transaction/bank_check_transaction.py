# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns= [_("Date") + "::240", _("Bank Check No") + "::240", _("Amount") + ":Currency:120", _("Party Name") + "::240", _("Remarks") + "::240", _("Created for user") + "::240"] 
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []

	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")

	conditions = return_filters(filters, from_date, to_date)

	payments = frappe.get_all("Payment Entry", ["*"], filters = conditions)

	for pay in payments:
		row = [pay.posting_date, pay.name, pay.paid_amount, pay.party_name, pay.remarks, pay.user]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "mode_of_payment": "Cheque"'
	conditions += ', "paid_to": "{}"'.format(filters.get("account"))
	# conditions += ', "docstatus": 1'
	conditions += '}'

	return conditions