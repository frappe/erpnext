# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, get_first_day, getdate


def execute(filters=None):
	columns = get_columns(filters)
	data = get_active_loan_details(filters)
	return columns, data

def get_columns(filters):
	columns = [
		{"label": _("Loan"), "fieldname": "loan", "fieldtype": "Link", "options": "Loan", "width": 160},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 160},
		{"label": _("Applicant Type"), "fieldname": "applicant_type", "options": "DocType", "width": 100},
		{"label": _("Applicant Name"), "fieldname": "applicant_name", "fieldtype": "Dynamic Link", "options": "applicant_type", "width": 150},
		{"label": _("Loan Type"), "fieldname": "loan_type", "fieldtype": "Link", "options": "Loan Type", "width": 100},
		{"label": _("Sanctioned Amount"), "fieldname": "sanctioned_amount", "fieldtype": "Currency", "options": "Currency", "width": 120},
		{"label": _("Disbursed Amount"), "fieldname": "disbursed_amount", "fieldtype": "Currency", "options": "Currency", "width": 120},
		{"label": _("Interest For The Month"), "fieldname": "month_interest", "fieldtype": "Currency", "options": "Currency", "width": 100},
		{"label": _("Penalty For The Month"), "fieldname": "month_penalty", "fieldtype": "Currency", "options": "Currency", "width": 100},
		{"label": _("Accrued Interest"), "fieldname": "accrued_interest", "fieldtype": "Currency", "options": "Currency", "width": 100},
		{"label": _("Total Repayment"), "fieldname": "total_repayment", "fieldtype": "Currency", "options": "Currency", "width": 100},
		{"label": _("Principal Outstanding"), "fieldname": "principal_outstanding", "fieldtype": "Currency", "options": "Currency", "width": 100},
		{"label": _("Interest Outstanding"), "fieldname": "interest_outstanding", "fieldtype": "Currency", "options": "Currency", "width": 100},
		{"label": _("Total Outstanding"), "fieldname": "total_payment", "fieldtype": "Currency", "options": "Currency", "width": 100},
		{"label": _("Interest %"), "fieldname": "rate_of_interest", "fieldtype": "Percent", "width": 100},
		{"label": _("Penalty Interest %"), "fieldname": "precentage_percentage", "fieldtype": "Percent", "width": 100},
	]

	return columns

def get_active_loan_details(filters):
	loan_details = frappe.get_all("Loan",
		fields=["name as loan", "applicant_type", "applicant as applicant_name", "loan_type",
		"disbursed_amount", "rate_of_interest", "total_payment", "total_principal_paid",
		"total_interest_payable", "written_off_amount", "status"],
		filters={"status": ("!=", "Closed")})

	loan_list = [d.loan for d in loan_details]

	sanctioned_amount_map = get_sanctioned_amount_map()
	payments = get_payments(loan_list)
	accrual_map = get_interest_accruals(loan_list)

	for loan in loan_details:
		loan.update({
			"sanctioned_amount": flt(sanctioned_amount_map.get(loan.applicant_name)),
			"principal_outstanding": flt(loan.total_payment) - flt(loan.total_principal_paid) \
				- flt(loan.total_interest_payable) - flt(loan.written_off_amount),
			"total_repayment": flt(payments.get(loan.loan)),
			"month_interest": flt(accrual_map.get(loan.loan, {}).get("month_interest")),
			"accrued_interest": flt(accrual_map.get(loan.loan, {}).get("accrued_interest"))
		})
	return loan_details

def get_sanctioned_amount_map():
	return frappe._dict(frappe.get_all("Sanctioned Loan Amount", fields=["applicant", "sanctioned_amount_limit"],
		as_list=1))

def get_payments(loans):
	return frappe._dict(frappe.get_all("Loan Repayment", fields=["against_loan", "sum(amount_paid)"],
		filters={"against_loan": ("in", loans)}, group_by="against_loan", as_list=1))

def get_interest_accruals(loans):
	accrual_map = {}
	current_month_start = get_first_day(getdate())

	interest_accruals = frappe.get_all("Loan Interest Accrual",
		fields=["loan", "interest_amount", "posting_date", "penalty_amount"],
		filters={"loan": ("in", loans)})

	for entry in interest_accruals:
		accrual_map.setdefault(entry.loan, {
			'month_interest': 0.0,
			'accrued_interest': 0.0
		})

		if getdate(entry.posting_date) < getdate(current_month_start):
			accrual_map[entry.loan]['accrued_interest'] += entry.interest_amount
		else:
			accrual_map[entry.loan]['month_interest'] += entry.interest_amount

	return accrual_map