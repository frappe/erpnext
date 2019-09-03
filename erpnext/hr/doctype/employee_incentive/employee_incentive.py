# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class EmployeeIncentive(Document):
	def on_submit(self):
		company = frappe.db.get_value('Employee', self.employee, 'company')
		additional_salary = frappe.db.exists('Additional Salary', {
				'employee': self.employee, 
				'salary_component': 'Arrear',
				'payroll_date': self.payroll_date, 
				'company': company,
				'docstatus': 1
			})

		if not additional_salary:
			additional_salary = frappe.new_doc('Additional Salary')
			additional_salary.employee = self.employee
			additional_salary.salary_component = 'Arrear'
			additional_salary.amount = self.incentive_amount
			additional_salary.payroll_date = self.payroll_date
			additional_salary.company = company
			additional_salary.submit()
			self.db_set('additional_salary', additional_salary.name)

		else:
			incentive_added = frappe.db.get_value('Additional Salary', additional_salary, 'amount') + self.incentive_amount
			frappe.db.set_value('Additional Salary', additional_salary, 'amount', incentive_added)
			self.db_set('additional_salary', additional_salary)

	def on_cancel(self):
		if self.additional_salary:
			from erpnext.hr.doctype.retention_bonus.retention_bonus import check_if_linked_document_exists
			linked_document_exists = check_if_linked_document_exists(self)

			if linked_document_exists:
				incentive_removed = frappe.db.get_value('Additional Salary', self.additional_salary, 'amount') - self.incentive_amount
				frappe.db.set_value('Additional Salary', self.additional_salary, 'amount', incentive_removed)
			else:
				frappe.get_doc('Additional Salary', self.additional_salary).cancel()

			self.db_set('additional_salary', '')

		
