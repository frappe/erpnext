# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.hr.utils import (
	calculate_annual_eligible_hra_exemption,
	get_total_exemption_amount,
	validate_active_employee,
	validate_duplicate_exemption_for_payroll_period,
	validate_tax_declaration,
)


class EmployeeTaxExemptionDeclaration(Document):
	def validate(self):
		validate_active_employee(self.employee)
		validate_tax_declaration(self.declarations)
		validate_duplicate_exemption_for_payroll_period(
			self.doctype, self.name, self.payroll_period, self.employee
		)
		self.set_total_declared_amount()
		self.set_total_exemption_amount()
		self.calculate_hra_exemption()

	def set_total_declared_amount(self):
		self.total_declared_amount = 0.0
		for d in self.declarations:
			self.total_declared_amount += flt(d.amount)

	def set_total_exemption_amount(self):
		self.total_exemption_amount = get_total_exemption_amount(self.declarations)

	def calculate_hra_exemption(self):
		self.salary_structure_hra, self.annual_hra_exemption, self.monthly_hra_exemption = 0, 0, 0
		if self.get("monthly_house_rent"):
			hra_exemption = calculate_annual_eligible_hra_exemption(self)
			if hra_exemption:
				self.total_exemption_amount += hra_exemption["annual_exemption"]
				self.salary_structure_hra = hra_exemption["hra_amount"]
				self.annual_hra_exemption = hra_exemption["annual_exemption"]
				self.monthly_hra_exemption = hra_exemption["monthly_exemption"]


@frappe.whitelist()
def make_proof_submission(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Employee Tax Exemption Declaration",
		source_name,
		{
			"Employee Tax Exemption Declaration": {
				"doctype": "Employee Tax Exemption Proof Submission",
				"field_no_map": ["monthly_house_rent", "monthly_hra_exemption"],
			},
			"Employee Tax Exemption Declaration Category": {
				"doctype": "Employee Tax Exemption Proof Submission Detail",
				"add_if_empty": True,
			},
		},
		target_doc,
	)

	return doclist
