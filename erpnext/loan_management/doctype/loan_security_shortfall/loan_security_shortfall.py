# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

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

