# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.hr.utils import validate_tax_declaration, calculate_hra_exemption_for_period

class EmployeeTaxExemptionProofSubmission(Document):
	def validate(self):
		validate_tax_declaration(self.tax_exemption_proofs)
		self.exemption_amount = 0
		self.calculate_hra_exemption()
		for proof in self.tax_exemption_proofs:
			self.exemption_amount += proof.amount

	def calculate_hra_exemption(self):
		hra_exemption = calculate_hra_exemption_for_period(self)
		if hra_exemption:
			self.exemption_amount += hra_exemption["total_eligible_hra_exemption"]
			self.monthly_hra_exemption = hra_exemption["monthly_exemption"]
			self.monthly_house_rent = hra_exemption["monthly_house_rent"]
			self.total_eligible_hra_exemption = hra_exemption["total_eligible_hra_exemption"]
