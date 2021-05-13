# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from erpnext.healthcare.doctype.healthcare_insurance_contract.healthcare_insurance_contract import validate_insurance_contract

class HealthcareInsuranceCoveragePlan(Document):
	def validate(self):
		validate_insurance_contract(self.insurance_company)
