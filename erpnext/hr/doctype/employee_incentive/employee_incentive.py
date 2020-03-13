# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class EmployeeIncentive(Document):
	def on_submit(self):
		company = frappe.db.get_value('Employee', self.employee, 'company')

		additional_salary = frappe.new_doc('Additional Salary')
		additional_salary.employee = self.employee
		additional_salary.salary_component = self.salary_component
		additional_salary.amount = self.incentive_amount
		additional_salary.payroll_date = self.payroll_date
		additional_salary.company = company
		additional_salary.ref_doctype = self.doctype
		additional_salary.ref_docname = self.name
		additional_salary.submit()
