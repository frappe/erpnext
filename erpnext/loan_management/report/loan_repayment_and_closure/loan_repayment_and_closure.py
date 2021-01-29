# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
			{
				"label": _("Posting Date"),
				"fieldtype": "Date",
				"fieldname": "posting_date",
				"width": 100
			},
			{
				"label": _("Loan Repayment"),
				"fieldtype": "Link",
				"fieldname": "loan_repayment",
				"options": "Loan Repayment",
				"width": 100
			},
			{
				"label": _("Against Loan"),
				"fieldtype": "Link",
				"fieldname": "against_loan",
				"options": "Loan",
				"width": 200
			},
			{
				"label": _("Applicant"),
				"fieldtype": "Data",
				"fieldname": "applicant",
				"width": 150
			},
			{
				"label": _("Payment Type"),
				"fieldtype": "Data",
				"fieldname": "payment_type",
				"width": 150
			},
			{
				"label": _("Principal Amount"),
				"fieldtype": "Currency",
				"fieldname": "principal_amount",
				"options": "currency",
				"width": 100
			},
			{
				"label": _("Interest Amount"),
				"fieldtype": "Currency",
				"fieldname": "interest",
				"options": "currency",
				"width": 100
			},
			{
				"label": _("Penalty Amount"),
				"fieldtype": "Currency",
				"fieldname": "penalty",
				"options": "currency",
				"width": 100
			},
			{
				"label": _("Payable Amount"),
				"fieldtype": "Currency",
				"fieldname": "payable_amount",
				"options": "currency",
				"width": 100
			},
			{
				"label": _("Paid Amount"),
				"fieldtype": "Currency",
				"fieldname": "paid_amount",
				"options": "currency",
				"width": 100
			},
			{
				"label": _("Currency"),
				"fieldtype": "Link",
				"fieldname": "currency",
				"options": "Currency",
				"width": 100
			}
		]

def get_data(filters):
	data = []

	query_filters = {
		"docstatus": 1,
		"company": filters.get('company'),
	}

	if filters.get('applicant'):
		query_filters.update({
			"applicant": filters.get('applicant')
		})

	loan_repayments = frappe.get_all("Loan Repayment",
		filters = query_filters,
		fields=["posting_date", "applicant", "name", "against_loan", "payable_amount",
			"pending_principal_amount", "interest_payable", "penalty_amount", "amount_paid"]
	)

	default_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")

	for repayment in loan_repayments:
		row = {
			"posting_date": repayment.posting_date,
			"loan_repayment": repayment.name,
			"applicant": repayment.applicant,
			"payment_type": repayment.payment_type,
			"against_loan": repayment.against_loan,
			"principal_amount": repayment.pending_principal_amount,
			"interest": repayment.interest_payable,
			"penalty": repayment.penalty_amount,
			"payable_amount": repayment.payable_amount,
			"paid_amount": repayment.amount_paid,
			"currency": default_currency
		}

		data.append(row)

	return data