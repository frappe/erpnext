# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document
from frappe.utils import flt

from erpnext.hr.utils import (
	calculate_hra_exemption_for_period,
	get_total_exemption_amount,
	validate_active_employee,
	validate_duplicate_exemption_for_payroll_period,
	validate_tax_declaration,
)


class EmployeeTaxExemptionProofSubmission(Document):
	def validate(self):
		validate_active_employee(self.employee)
		validate_tax_declaration(self.tax_exemption_proofs)
		self.set_total_actual_amount()
		self.set_total_exemption_amount()
		self.calculate_hra_exemption()
		validate_duplicate_exemption_for_payroll_period(
			self.doctype, self.name, self.payroll_period, self.employee
		)

	def set_total_actual_amount(self):
		self.total_actual_amount = flt(self.get("house_rent_payment_amount"))
		for d in self.tax_exemption_proofs:
			self.total_actual_amount += flt(d.amount)

	def set_total_exemption_amount(self):
		self.exemption_amount = flt(
			get_total_exemption_amount(self.tax_exemption_proofs), self.precision("exemption_amount")
		)

	def calculate_hra_exemption(self):
		self.monthly_hra_exemption, self.monthly_house_rent, self.total_eligible_hra_exemption = 0, 0, 0
		if self.get("house_rent_payment_amount"):
			hra_exemption = calculate_hra_exemption_for_period(self)
			if hra_exemption:
				self.exemption_amount += hra_exemption["total_eligible_hra_exemption"]
				self.exemption_amount = flt(self.exemption_amount, self.precision("exemption_amount"))
				self.monthly_hra_exemption = flt(
					hra_exemption["monthly_exemption"], self.precision("monthly_hra_exemption")
				)
				self.monthly_house_rent = flt(
					hra_exemption["monthly_house_rent"], self.precision("monthly_house_rent")
				)
				self.total_eligible_hra_exemption = flt(
					hra_exemption["total_eligible_hra_exemption"], self.precision("total_eligible_hra_exemption")
				)
