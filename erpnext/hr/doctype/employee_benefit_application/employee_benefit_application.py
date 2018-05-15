# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.model.document import Document

class EmployeeBenefitApplication(Document):
	def before_submit(self):
		self.validate_duplicate_on_payroll_period()
		self.validate_max_benefit_for_component()

	def validate_max_benefit_for_component(self):
		if self.employee_benefits:
			for employee_benefit in self.employee_benefits:
				self.validate_max_benefit(employee_benefit.earning_component)

	def validate_max_benefit(self, earning_component_name):
		max_benefit_amount = frappe.db.get_value("Salary Component", earning_component_name, "max_benefit_amount")
		benefit_amount = 0
		for employee_benefit in self.employee_benefits:
			if employee_benefit.earning_component == earning_component_name:
				benefit_amount += employee_benefit.amount
		if benefit_amount > max_benefit_amount:
			frappe.throw(_("Maximum benefit amount of component {0} exceeds {1}").format(earning_component_name, max_benefit_amount))

	def validate_duplicate_on_payroll_period(self):
		application = frappe.db.exists(
			"Employee Benefit Application",
			{
				'employee': self.employee,
				'payroll_period': self.payroll_period,
				'docstatus': 1
			}
		)
		if application:
			frappe.throw(_("Employee {0} already submited an apllication {1} for the payroll period {2}").format(self.employee, application, self.payroll_period))

	def get_max_benefits(self):
		sal_struct = get_assigned_salary_sturecture(self.employee, self.date)
		if sal_struct:
			return frappe.db.get_value("Salary Structure", sal_struct[0][0], "max_benefits")


@frappe.whitelist()
def get_assigned_salary_sturecture(employee, _date):
	if not _date:
		_date = nowdate()
	salary_structure = frappe.db.sql("""
		select salary_structure from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and (
			(%(_date)s between from_date and ifnull(to_date, '2199-12-31'))
		)""", {
			'employee': employee,
			'_date': _date,
		})
	if salary_structure:
		return salary_structure
