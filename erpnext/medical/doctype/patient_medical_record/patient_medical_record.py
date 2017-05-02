# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PatientMedicalRecord(Document):
	def after_insert(self):
		if self.reference_doctype == "Patient Medical Record" :
			frappe.db.set_value("Patient Medical Record", self.name, "reference_name", self.name)
