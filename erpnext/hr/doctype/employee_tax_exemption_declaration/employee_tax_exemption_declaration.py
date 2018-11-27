# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.hr.utils import validate_tax_declaration, calculate_annual_eligible_hra_exemption

class EmployeeTaxExemptionDeclaration(Document):
	def validate(self):
		validate_tax_declaration(self.declarations)
		self.total_exemption_amount = 0
		self.calculate_hra_exemption()
		for item in self.declarations:
			self.total_exemption_amount += item.amount

	def before_submit(self):
		if frappe.db.exists({"doctype": "Employee Tax Exemption Declaration",
							"employee": self.employee,
							"payroll_period": self.payroll_period,
							"docstatus": 1}):
			frappe.throw(_("Tax Declaration of {0} for period {1} already submitted.")\
			.format(self.employee, self.payroll_period), frappe.DocstatusTransitionError)

	def calculate_hra_exemption(self):
		hra_exemption = calculate_annual_eligible_hra_exemption(self)
		if hra_exemption:
			self.total_exemption_amount += hra_exemption["annual_exemption"]
			self.salary_structure_hra = hra_exemption["hra_amount"]
			self.annual_hra_exemption = hra_exemption["annual_exemption"]
			self.monthly_hra_exemption = hra_exemption["monthly_exemption"]
