# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SanctionedLoanAmount(Document):
	def validate(self):
		if frappe.db.exists('Sanctioned Loan Amount', {'applicant': self.applicant, 'company': self.company}):
			frappe.throw("Sanctioned Loan Amount already exists for {0} against company {1}".format(
				frappe.bold(self.applicant), frappe.bold(self.company)
			))
