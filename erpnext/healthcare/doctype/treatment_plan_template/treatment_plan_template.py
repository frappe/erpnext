# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TreatmentPlanTemplate(Document):
	def validate(self):
		self.validate_age()

	def validate_age(self):
		if self.patient_age_from and self.patient_age_from < 0:
			frappe.throw(_("Patient Age From cannot be less than 0"))
		if self.patient_age_to and self.patient_age_to < 0:
			frappe.throw(_("Patient Age To cannot be less than 0"))
		if self.patient_age_to and self.patient_age_from and self.patient_age_to < self.patient_age_from:
			frappe.throw(_("Patient Age To cannot be less than Patient Age From"))
