# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.hr.utils import validate_tax_declaration, calculate_eligible_hra_exemption

class EmployeeTaxExemptionDeclaration(Document):
	def validate(self):
		validate_tax_declaration(self.declarations)
		self.calculate_hra_exemption()
		self.total_exemption_amount = 0
		for item in self.declarations:
			self.total_exemption_amount += item.amount
		if self.annual_hra_exemption:
			self.total_exemption_amount += self.annual_hra_exemption

	def before_submit(self):
		if frappe.db.exists({"doctype": "Employee Tax Exemption Declaration",
							"employee": self.employee,
							"payroll_period": self.payroll_period,
							"docstatus": 1}):
			frappe.throw(_("Tax Declaration of {0} for period {1} already submitted.")\
			.format(self.employee, self.payroll_period), frappe.DocstatusTransitionError)

	def calculate_hra_exemption(self):
		exemptions = calculate_eligible_hra_exemption(self.company, self.employee, \
						self.monthly_house_rent, self.rented_in_metro_city)
		self.salary_structure_hra = exemptions["hra_amount"]
		self.annual_hra_exemption = exemptions["annual_exemption"]
		self.monthly_hra_exemption = exemptions["monthly_exemption"]
