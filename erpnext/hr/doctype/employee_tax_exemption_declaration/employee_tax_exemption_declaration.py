# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, flt
from erpnext.hr.utils import validate_tax_declaration, get_salary_assignment
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip

class EmployeeTaxExemptionDeclaration(Document):
	def validate(self):
		validate_tax_declaration(self.declarations)
		self.calculate_hra_component()
		self.total_exemption_amount = 0
		for item in self.declarations:
			self.total_exemption_amount += item.amount
		if self.annual_hra:
			self.total_exemption_amount += self.annual_hra

	def before_submit(self):
		if frappe.db.exists({"doctype": "Employee Tax Exemption Declaration",
							"employee": self.employee,
							"payroll_period": self.payroll_period,
							"docstatus": 1}):
			frappe.throw(_("Tax Declaration of {0} for period {1} already submitted.")\
			.format(self.employee, self.payroll_period), frappe.DocstatusTransitionError)

	def calculate_hra_component(self):
		hra_component = frappe.db.get_value("Company", self.company, "hra_component")
		if hra_component:
			assignment = get_salary_assignment(self.employee, getdate())
			if assignment and frappe.db.exists("Salary Detail", {
				"parent": assignment.salary_structure,
				"salary_component": hra_component, "parentfield": "earnings"}):
				hra_amount = self.get_hra_from_salary_slip(assignment.salary_structure, hra_component)
				if hra_amount:
					self.salary_structure_hra = hra_amount
					if self.monthly_house_rent:
						self.annual_hra, self.monthly_hra = 0, 0
						annual_hra = self.calculate_eligible_hra_amount(assignment.salary_structure, assignment.base)
						if annual_hra > 0:
							self.annual_hra = annual_hra
							self.monthly_hra = annual_hra / 12

	def calculate_eligible_hra_amount(self, salary_structure, base):
		# TODO make this configurable
		exemptions = []
		frequency = frappe.get_value("Salary Structure", salary_structure, "payroll_frequency")
		# case 1: The actual amount allotted by the employer as the HRA.
		exemptions.append(self.get_annual_component_pay(frequency, self.salary_structure_hra))
		actual_annual_rent = self.monthly_house_rent * 12
		annual_base = self.get_annual_component_pay(frequency, base)
		# case 2: Actual rent paid less 10% of the basic salary.
		exemptions.append(flt(actual_annual_rent) - flt(annual_base * 0.1))
		# case 3: 50% of the basic salary, if the employee is staying in a metro city (40% for a non-metro city).
		exemptions.append(annual_base * 0.5 if self.rented_in_metro_city else annual_base * 0.4)
		# return minimum of 3 cases
		return min(exemptions)

	def get_annual_component_pay(self, frequency, amount):
		if frequency == "Daily":
			return amount * 365
		elif frequency == "Weekly":
			return amount * 52
		elif frequency == "Fortnightly":
			return amount * 26
		elif frequency == "Monthly":
			return amount * 12
		elif frequency == "Bimonthly":
			return amount * 6

	def get_hra_from_salary_slip(self, salary_structure, hra_component):
		salary_slip = make_salary_slip(salary_structure, employee=self.employee)
		for earning in salary_slip.earnings:
			if earning.salary_component == hra_component:
				return earning.amount
