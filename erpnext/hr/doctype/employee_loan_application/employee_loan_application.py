# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

from erpnext.hr.doctype.employee_loan.employee_loan import get_monthly_repayment_amount, check_repayment_method

class EmployeeLoanApplication(Document):
	def validate(self):
		check_repayment_method(self.repayment_method, self.loan_amount, self.repayment_amount, self.repayment_periods)
		self.validate_loan_amount()
		self.get_repayment_details()
		self.validate_emp()
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
				self.docstatus = 1
				self.docstatus = 2

	def validate_emp(self):
		 if self.get('__islocal'):
			if u'CEO' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By CEO"
			elif u'Director' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Director"
			elif u'Manager' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Manager"
			elif u'Line Manager' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Line Manager"
			elif u'Employee' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Pending"

	def validate_loan_amount(self):
		maximum_loan_limit = frappe.db.get_value('Loan Type', self.loan_type, 'maximum_loan_amount')
		if maximum_loan_limit and self.loan_amount > maximum_loan_limit:
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))

	def get_repayment_details(self):
		if self.repayment_method == "Repay over Number of Months":
			self.repayment_amount = get_monthly_repayment_amount(self.repayment_method, self.loan_amount, self.rate_of_interest, self.repayment_periods)

		if self.rate_of_interest>0:
			if self.repayment_method == "Repay Once":
				monthly_interest_rate = flt(self.rate_of_interest) / (12 *100)
				self.repayment_periods = math.ceil((math.log(self.repayment_amount) - math.log(self.repayment_amount - \
										(self.loan_amount*monthly_interest_rate)))/(math.log(1+monthly_interest_rate)))

			self.total_payable_amount = self.repayment_amount * self.repayment_periods
			self.total_payable_interest = self.total_payable_amount - self.loan_amount

@frappe.whitelist()
def make_employee_loan(source_name, target_doc = None):
	doclist = get_mapped_doc("Employee Loan Application", source_name, {
		"Employee Loan Application": {
			"doctype": "Employee Loan",
			"validation": {
				"docstatus": ["=", 1]
			}
		}
	}, target_doc)

	return doclist