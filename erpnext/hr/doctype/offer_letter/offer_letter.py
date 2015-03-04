# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class OfferLetter(Document):
	def validate(self):
		self.set_applicant_name()
		
	def set_applicant_name(self):
		self.applicant_name = frappe.db.get_value("Job Applicant", self.job_applicant, "applicant_name")
