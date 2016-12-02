# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class EmployeeLoanApplication(Document):
	def validate(self):
		self.validate_loan_amount()

	def validate_loan_amount(self):
		maximum_loan_limit = frappe.db.get_value('Loan Type',self.loan_type , 'maximum_loan_amount')
		if self.loan_amount > maximum_loan_limit:
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))