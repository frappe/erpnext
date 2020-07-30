# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, add_to_date, get_datetime, get_timestamp, get_datetime_str
from six import iteritems

class LoanSecurityPrice(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):

		if self.valid_from > self.valid_upto:
			frappe.throw(_("Valid From Time must be lesser than Valid Upto Time."))

		existing_loan_security = frappe.db.sql(""" SELECT name from `tabLoan Security Price`
			WHERE loan_security = %s AND name != %s AND (valid_from BETWEEN %s and %s OR valid_upto BETWEEN %s and %s) """,
			(self.loan_security, self.name, self.valid_from, self.valid_upto, self.valid_from, self.valid_upto))

		if existing_loan_security:
			frappe.throw(_("Loan Security Price overlapping with {0}").format(existing_loan_security[0][0]))

@frappe.whitelist()
def get_loan_security_price(loan_security, valid_time=None):
	if not valid_time:
		valid_time = get_datetime()

	loan_security_price = frappe.db.get_value("Loan Security Price", {
		'loan_security': loan_security,
		'valid_from': ("<=",valid_time),
		'valid_upto': (">=", valid_time)
	}, 'loan_security_price')

	if not loan_security_price:
		frappe.throw(_("No valid Loan Security Price found for {0}").format(frappe.bold(loan_security)))
	else:
		return loan_security_price









