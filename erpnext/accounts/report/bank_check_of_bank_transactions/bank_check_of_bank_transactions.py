# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns= [_("Date") + "::240", _("No Check") + "::240", _("Status") + "::240", _("Amount") + ":Currency:120", _("Party Name") + "::240", _("Remarks") + "::240", _("Created By") + "::240"] 
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []

	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")

	conditions = return_filters(filters, from_date, to_date)

	transactions = frappe.get_all("Bank Transactions", ["*"], filters = conditions)

	for transaction in transactions:
		row = [transaction.check_date, transaction.no_bank_check, transaction.status, transaction.amount, transaction.person_name, transaction.movement_detail, transaction.created_by]
		data.append(row)
	
	condition_payment = return_filters_payment_entry(filters, from_date, to_date)
	
	payments = frappe.get_all("Payment Entry", ["*"], filters = condition_payment)

	for pay in payments:
		row = [pay.posting_date, pay.reference_no, pay.status, pay.paid_amount, pay.party, pay.remarks, pay.user]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"check_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	# conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "bank_account": "{}"'.format(filters.get("account"))
	conditions += ', "check": 1'
	# conditions += ', "docstatus": 1'
	conditions += '}'

	return conditions

def return_filters_payment_entry(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "bank_account": "{}"'.format(filters.get("account"))
	conditions += ', "mode_of_payment": "Cheque"'
	conditions += '}'

	return conditions
