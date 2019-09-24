# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):

	columns = create_columns()
	data = get_record()
	return columns, data

def create_columns():
	return [
			{
				"label": _("Employee"),
				"fieldtype": "Data",
				"fieldname": "employee",
				"options": "Employee",
				"width": 200
			},
			{
				"label": _("Loan"),
				"fieldtype": "Link",
				"fieldname": "loan_name",
				"options": "Loan",
				"width": 200
			},
			{
				"label": _("Loan Amount"),
				"fieldtype": "Currency",
				"fieldname": "loan_amount",
				"options": "currency",
				"width": 100
			},
			{
				"label": _("Interest"),
				"fieldtype": "Data",
				"fieldname": "interest",
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
				"label": _("EMI"),
				"fieldtype": "Currency",
				"fieldname": "emi",
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
				"label": _("Outstanding Amount"),
				"fieldtype": "Currency",
				"fieldname": "out_amt",
				"options": "currency",
				"width": 100
			},
		]

def get_record():
	data = []
	loans = frappe.get_all("Loan",
		filters=[("status", "=", "Disbursed")],
		fields=["applicant", "applicant_name", "name", "loan_amount", "rate_of_interest",
			"total_payment", "monthly_repayment_amount", "total_amount_paid"]
	)

	for loan in loans:
		row = {
			"employee": loan.applicant + ": " + loan.applicant_name,
			"loan_name": loan.name,
			"loan_amount": loan.loan_amount,
			"interest": str(loan.rate_of_interest) + "%",
			"payable_amount": loan.total_payment,
			"emi": loan.monthly_repayment_amount,
			"paid_amount": loan.total_amount_paid,
			"out_amt": loan.total_payment - loan.total_amount_paid
		}

		data.append(row)

	return data
