# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import flt, getdate, add_days


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
		{"label": _("Sanctioned Amount"), "fieldname": "sanctioned_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Disbursed Amount"), "fieldname": "disbursed_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Penalty Amount"), "fieldname": "penalty", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Accrued Interest"), "fieldname": "accrued_interest", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Total Repayment"), "fieldname": "total_repayment", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Principal Outstanding"), "fieldname": "principal_outstanding", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Interest Outstanding"), "fieldname": "interest_outstanding", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Total Outstanding"), "fieldname": "total_outstanding", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Undue Booked Interest"), "fieldname": "undue_interest", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Interest %"), "fieldname": "rate_of_interest", "fieldtype": "Percent", "width": 100},
		{"label": _("Penalty Interest %"), "fieldname": "penalty_interest", "fieldtype": "Percent", "width": 100},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Currency", "options": "Currency", "hidden": 1, "width": 100},
	]

	return columns

def get_active_loan_details(filters):

	filter_obj = {"status": ("!=", "Closed")}
	if filters.get('company'):
		filter_obj.update({'company': filters.get('company')})

	loan_details = frappe.get_all("Loan",
		fields=["name as loan", "applicant_type", "applicant as applicant_name", "loan_type",
		"disbursed_amount", "rate_of_interest", "total_payment", "total_principal_paid",
		"total_interest_payable", "written_off_amount", "status"],
		filters=filter_obj)

	loan_list = [d.loan for d in loan_details]

	sanctioned_amount_map = get_sanctioned_amount_map()
	penal_interest_rate_map = get_penal_interest_rate_map()
	payments = get_payments(loan_list)
	accrual_map = get_interest_accruals(loan_list)
	currency = erpnext.get_company_currency(filters.get('company'))

	for loan in loan_details:
		loan.update({
			"sanctioned_amount": flt(sanctioned_amount_map.get(loan.applicant_name)),
			"principal_outstanding": flt(loan.total_payment) - flt(loan.total_principal_paid) \
				- flt(loan.total_interest_payable) - flt(loan.written_off_amount),
			"total_repayment": flt(payments.get(loan.loan)),
			"accrued_interest": flt(accrual_map.get(loan.loan, {}).get("accrued_interest")),
			"interest_outstanding": flt(accrual_map.get(loan.loan, {}).get("interest_outstanding")),
			"penalty": flt(accrual_map.get(loan.loan, {}).get("penalty")),
			"penalty_interest": penal_interest_rate_map.get(loan.loan_type),
			"undue_interest": flt(accrual_map.get(loan.loan, {}).get("undue_interest")),
			"currency": currency
		})

		loan['total_outstanding'] = loan['principal_outstanding'] + loan['interest_outstanding'] \
			+ loan['penalty']

	return loan_details

def get_sanctioned_amount_map():
	return frappe._dict(frappe.get_all("Sanctioned Loan Amount", fields=["applicant", "sanctioned_amount_limit"],
		as_list=1))

def get_payments(loans):
	return frappe._dict(frappe.get_all("Loan Repayment", fields=["against_loan", "sum(amount_paid)"],
		filters={"against_loan": ("in", loans)}, group_by="against_loan", as_list=1))

def get_interest_accruals(loans):
	accrual_map = {}

	interest_accruals = frappe.get_all("Loan Interest Accrual",
		fields=["loan", "interest_amount", "posting_date", "penalty_amount",
		"paid_interest_amount", "accrual_type"], filters={"loan": ("in", loans)}, order_by="posting_date desc")

	for entry in interest_accruals:
		accrual_map.setdefault(entry.loan, {
			"accrued_interest": 0.0,
			"undue_interest": 0.0,
			"interest_outstanding": 0.0,
			"last_accrual_date": '',
			"due_date": ''
		})

		if entry.accrual_type == 'Regular':
			if not accrual_map[entry.loan]['due_date']:
				accrual_map[entry.loan]['due_date'] = add_days(entry.posting_date, 1)
			if not accrual_map[entry.loan]['last_accrual_date']:
				accrual_map[entry.loan]['last_accrual_date'] = entry.posting_date

		due_date = accrual_map[entry.loan]['due_date']
		last_accrual_date = accrual_map[entry.loan]['last_accrual_date']

		if due_date and getdate(entry.posting_date) < getdate(due_date):
			accrual_map[entry.loan]["interest_outstanding"] += entry.interest_amount - entry.paid_interest_amount
		else:
			accrual_map[entry.loan]['undue_interest'] += entry.interest_amount - entry.paid_interest_amount

		accrual_map[entry.loan]["accrued_interest"] += entry.interest_amount

		if last_accrual_date and getdate(entry.posting_date) == last_accrual_date:
			accrual_map[entry.loan]["penalty"] = entry.penalty_amount

	return accrual_map

def get_penal_interest_rate_map():
	return frappe._dict(frappe.get_all("Loan Type", fields=["name", "penalty_interest_rate"], as_list=1))