# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class LoanSecurityShortfall(Document):
	pass


@frappe.whitelist()
def add_security(loan):
	loan_applicant = frappe.db.get_value("Loan", loan, 'applicant')

	loan_security_pledge = frappe.new_doc("Loan Security Pledge")
	loan_security_pledge.loan = loan
	loan_security_pledge.applicant = loan_applicant

	return loan_security_pledge.as_dict()

