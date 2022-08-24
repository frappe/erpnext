# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns= [_("") + "::240", _("") + "::240"] 
	columns = [
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 240
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 240
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 240
		},
		{
			"label": _("No Check"),
			"fieldname": "no_checl",
			"width": 240
		},
		{
			"label": _("Status"),
			"fieldname": "status",
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

	transactions = frappe.get_all("Bank Transactions", ["*"], filters = conditions)

	for transaction in transactions:
		row = ["Bank Transactions", transaction.name, transaction.check_date, transaction.no_bank_check, transaction.status, transaction.amount, transaction.person_name, transaction.movement_detail, transaction.created_by]
		data.append(row)
	
	condition_payment = return_filters_payment_entry(filters, from_date, to_date)
	
	payments = frappe.get_all("Payment Entry", ["*"], filters = condition_payment)

	for pay in payments:
		row = ["Payment Entry", pay.name, pay.posting_date, pay.reference_no, pay.status, pay.paid_amount, pay.party, pay.remarks, pay.user]
		data.append(row)
	
	condition_voided = return_filters_voided_check(filters, from_date, to_date)
	
	voideds = frappe.get_all("Voided Check", ["*"], filters = condition_voided)

	for voided in voideds:
		row = ["Voided Check", voided.name, voided.posting_date, voided.no_bank_check, "Anulled", 0, "Anulled", voided.remarks, voided.created_by]
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

def return_filters_voided_check(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "bank_account": "{}"'.format(filters.get("account"))
	conditions += '}'

	return conditions
