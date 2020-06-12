# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import get_datetime
from frappe.model.document import Document
from six import iteritems

class LoanSecurityShortfall(Document):
	pass

def update_shortfall_status(loan, security_value):
	loan_security_shortfall = frappe.db.get_value("Loan Security Shortfall",
		{"loan": loan, "status": "Pending"}, ['name', 'shortfall_amount'], as_dict=1)

	if not loan_security_shortfall:
		return

	if security_value >= loan_security_shortfall.shortfall_amount:
		frappe.db.set_value("Loan Security Shortfall", loan_security_shortfall.name, "status", "Completed")
	else:
		frappe.db.set_value("Loan Security Shortfall", loan_security_shortfall.name,
			"shortfall_amount", loan_security_shortfall.shortfall_amount - security_value)


@frappe.whitelist()
def add_security(loan):
	loan_details = frappe.db.get_value("Loan", loan, ['applicant', 'company', 'applicant_type'], as_dict=1)

	loan_security_pledge = frappe.new_doc("Loan Security Pledge")
	loan_security_pledge.loan = loan
	loan_security_pledge.company = loan_details.company
	loan_security_pledge.applicant_type = loan_details.applicant_type
	loan_security_pledge.applicant = loan_details.applicant

	return loan_security_pledge.as_dict()

def check_for_ltv_shortfall(process_loan_security_shortfall):

	update_time = get_datetime()

	loan_security_price_map = frappe._dict(frappe.get_all("Loan Security Price",
		fields=["loan_security", "loan_security_price"],
		filters = {
			"valid_from": ("<=", update_time),
			"valid_upto": (">=", update_time)
		}, as_list=1))

	ltv_ratio_map = frappe._dict(frappe.get_all("Loan Security Type",
		fields=["name", "loan_to_value_ratio"], as_list=1))

	loans = frappe.db.sql(""" SELECT l.name, l.loan_amount, l.total_principal_paid, lp.loan_security, lp.haircut, lp.qty, lp.loan_security_type
		FROM `tabLoan` l, `tabPledge` lp , `tabLoan Security Pledge`p WHERE lp.parent = p.name and p.loan = l.name and l.docstatus = 1
		and l.is_secured_loan and l.status = 'Disbursed' and p.status = 'Pledged'""", as_dict=1)

	loan_security_map = {}

	for loan in loans:
		loan_security_map.setdefault(loan.name, {
			"loan_amount": loan.loan_amount - loan.total_principal_paid,
			"security_value": 0.0
		})

		current_loan_security_amount = loan_security_price_map.get(loan.loan_security, 0) * loan.qty
		ltv_ratio = ltv_ratio_map.get(loan.loan_security_type)

		loan_security_map[loan.name]['security_value'] += current_loan_security_amount - (current_loan_security_amount * loan.haircut/100)

	for loan, value in iteritems(loan_security_map):
		if (value["loan_amount"]/value['security_value'] * 100) > ltv_ratio:
			create_loan_security_shortfall(loan, value, process_loan_security_shortfall)

def create_loan_security_shortfall(loan, value, process_loan_security_shortfall):

	existing_shortfall = frappe.db.get_value("Loan Security Shortfall", {"loan": loan, "status": "Pending"}, "name")

	if existing_shortfall:
		ltv_shortfall = frappe.get_doc("Loan Security Shortfall", existing_shortfall)
	else:
		ltv_shortfall = frappe.new_doc("Loan Security Shortfall")
		ltv_shortfall.loan = loan

	ltv_shortfall.shortfall_time = get_datetime()
	ltv_shortfall.loan_amount = value["loan_amount"]
	ltv_shortfall.security_value = value["security_value"]
	ltv_shortfall.shortfall_amount = value["loan_amount"] - value["security_value"]
	ltv_shortfall.process_loan_security_shortfall = process_loan_security_shortfall
	ltv_shortfall.save()

