# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import get_datetime, flt
from frappe.model.document import Document
from six import iteritems
from erpnext.loan_management.doctype.loan_security_unpledge.loan_security_unpledge import get_pledged_security_qty

class LoanSecurityShortfall(Document):
	pass

def update_shortfall_status(loan, security_value, on_cancel=0):
	loan_security_shortfall = frappe.db.get_value("Loan Security Shortfall",
		{"loan": loan, "status": "Pending"}, ['name', 'shortfall_amount'], as_dict=1)

	if not loan_security_shortfall:
		return

	if security_value >= loan_security_shortfall.shortfall_amount:
		frappe.db.set_value("Loan Security Shortfall", loan_security_shortfall.name, {
			"status": "Completed",
			"shortfall_amount": loan_security_shortfall.shortfall_amount,
			"shortfall_percentage": 0
		})
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

	loans = frappe.get_all('Loan', fields=['name', 'loan_amount', 'total_principal_paid', 'total_payment',
		'total_interest_payable', 'disbursed_amount', 'status'],
		filters={'status': ('in',['Disbursed','Partially Disbursed']), 'is_secured_loan': 1})

	loan_shortfall_map = frappe._dict(frappe.get_all("Loan Security Shortfall",
		fields=["loan", "name"], filters={"status": "Pending"}, as_list=1))

	loan_security_map = {}

	for loan in loans:
		if loan.status == 'Disbursed':
			outstanding_amount = flt(loan.total_payment) - flt(loan.total_interest_payable) \
				- flt(loan.total_principal_paid)
		else:
			outstanding_amount = flt(loan.disbursed_amount) - flt(loan.total_interest_payable) \
				- flt(loan.total_principal_paid)

		pledged_securities = get_pledged_security_qty(loan.name)
		ltv_ratio = ''
		security_value = 0.0

		for security, qty in pledged_securities.items():
			if not ltv_ratio:
				ltv_ratio = get_ltv_ratio(security)
			security_value += flt(loan_security_price_map.get(security)) * flt(qty)

		current_ratio = (outstanding_amount/security_value) * 100 if security_value else 0

		if current_ratio > ltv_ratio:
			shortfall_amount = outstanding_amount - ((security_value * ltv_ratio) / 100)
			create_loan_security_shortfall(loan.name, outstanding_amount, security_value, shortfall_amount,
				current_ratio, process_loan_security_shortfall)
		elif loan_shortfall_map.get(loan.name):
			shortfall_amount = outstanding_amount - ((security_value * ltv_ratio) / 100)
			if shortfall_amount <= 0:
				shortfall = loan_shortfall_map.get(loan.name)
				update_pending_shortfall(shortfall)

def create_loan_security_shortfall(loan, loan_amount, security_value, shortfall_amount, shortfall_ratio,
	process_loan_security_shortfall):
	existing_shortfall = frappe.db.get_value("Loan Security Shortfall", {"loan": loan, "status": "Pending"}, "name")

	if existing_shortfall:
		ltv_shortfall = frappe.get_doc("Loan Security Shortfall", existing_shortfall)
	else:
		ltv_shortfall = frappe.new_doc("Loan Security Shortfall")
		ltv_shortfall.loan = loan

	ltv_shortfall.shortfall_time = get_datetime()
	ltv_shortfall.loan_amount = loan_amount
	ltv_shortfall.security_value = security_value
	ltv_shortfall.shortfall_amount = shortfall_amount
	ltv_shortfall.shortfall_percentage = shortfall_ratio
	ltv_shortfall.process_loan_security_shortfall = process_loan_security_shortfall
	ltv_shortfall.save()

def get_ltv_ratio(loan_security):
	loan_security_type = frappe.db.get_value('Loan Security', loan_security, 'loan_security_type')
	ltv_ratio = frappe.db.get_value('Loan Security Type', loan_security_type, 'loan_to_value_ratio')
	return ltv_ratio

def update_pending_shortfall(shortfall):
	# Get all pending loan security shortfall
	frappe.db.set_value("Loan Security Shortfall", shortfall,
		{
			"status": "Completed",
			"shortfall_amount": 0,
			"shortfall_percentage": 0
		})

