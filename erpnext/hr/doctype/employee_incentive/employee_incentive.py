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
				'salary_component': self.salary_component,
				'payroll_date': self.payroll_date, 
				'company': company,
				'docstatus': 1
			})

		if not additional_salary:
			additional_salary = frappe.new_doc('Additional Salary')
			additional_salary.employee = self.employee
			additional_salary.salary_component = self.salary_component
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
			incentive_removed = frappe.db.get_value('Additional Salary', self.additional_salary, 'amount') - self.incentive_amount
			if incentive_removed == 0:
				frappe.get_doc('Additional Salary', self.additional_salary).cancel()
			else:
				frappe.db.set_value('Additional Salary', self.additional_salary, 'amount', incentive_removed)

			self.db_set('additional_salary', '')
	
	def confidentials(self):
		confidentials_list = frappe.get_all("Confidential Payroll Employee", ["*"])

		if len(confidentials_list):
			employees = frappe.get_all("Confidential Payroll Detail", ["*"], filters = {"parent":confidentials_list[0].name, "employee": self.employee})
			
			if len(employees) > 0:
				user = frappe.session.user

				users = frappe.get_all("User", ["*"], filters = {"name": user})

				roles = frappe.get_all("Has Role", ["*"], filters = {"parent": users[0].name})

				roles_arr = []

				for role in roles:
					roles_arr.append(role.role)

				if confidentials_list[0].rol in roles_arr:
					self.db_set('confidential', 1, update_modified=False)
				else:
					self.db_set('confidential', 0, update_modified=False)
			else:
				self.db_set('confidential', 1, update_modified=False)
		else:
			self.db_set('confidential', 1, update_modified=False)

		
