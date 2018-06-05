# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import date_diff, flt
from erpnext.hr.utils import validate_tax_declaration, calculate_eligible_hra_exemption

class EmployeeTaxExemptionProofSubmission(Document):
	def validate(self):
		validate_tax_declaration(self.tax_exemption_proofs)
		if self.house_rent_payment_amount:
			self.validate_house_rent_dates()
		self.get_monthly_hra()
		self.calculate_hra_exemption()
		self.calculate_total_exemption()

	def get_monthly_hra(self):
		factor = self.get_rented_days_factor()
		self.monthly_house_rent = self.house_rent_payment_amount / factor

	def validate_house_rent_dates(self):
		if date_diff(self.rented_to_date, self.rented_from_date) < 14:
			frappe.throw(_("House Rented dates should be atleast 15 days apart"))

		proofs = frappe.db.sql("""select name from `tabEmployee Tax Exemption Proof Submission`
			where docstatus=1 and employee='{0}' and payroll_period='{1}' and
			(rented_from_date between '{2}' and '{3}' or rented_to_date between
			'{2}' and '{2}')""".format(self.employee, self.payroll_period,
			self.rented_from_date, self.rented_to_date))
		if proofs:
			frappe.throw(_("House rent paid days overlap with {0}").format(proofs[0][0]))

	def calculate_hra_exemption(self):
		exemptions = calculate_eligible_hra_exemption(self.company, self.employee, \
						self.monthly_house_rent, self.rented_in_metro_city)
		self.monthly_hra_exemption = exemptions["monthly_exemption"]
		if self.monthly_hra_exemption:
			factor = self.get_rented_days_factor(rounded=False)
			self.total_eligible_hra_exemption = self.monthly_hra_exemption * factor
		else:
			self.monthly_hra_exemption, self.total_eligible_hra_exemption = 0, 0

	def get_rented_days_factor(self, rounded=True):
		factor = flt(date_diff(self.rented_to_date, self.rented_from_date) + 1)/30
		factor = round(factor * 2)/2
		return factor if factor else 0.5

	def calculate_total_exemption(self):
		self.total_amount = 0
		for proof in self.tax_exemption_proofs:
			self.total_amount += proof.amount
		if self.monthly_house_rent and self.total_eligible_hra_exemption:
			self.total_amount += self.total_eligible_hra_exemption
