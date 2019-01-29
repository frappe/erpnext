# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import comma_and, validate_email_add

sender_field = "email_id"

class DuplicationError(frappe.ValidationError): pass

class JobApplicant(Document):
	def onload(self):
		job_offer = frappe.get_all("Job Offer", filters={"job_applicant": self.name})
		if job_offer:
			self.get("__onload").job_offer = job_offer[0].name

	def autoname(self):
		keys = filter(None, (self.applicant_name, self.email_id, self.job_title))
		if not keys:
			frappe.throw(_("Name or Email is mandatory"), frappe.NameError)
		self.name = " - ".join(keys)

	def validate(self):
		self.check_email_id_is_unique()
		if self.email_id:
			validate_email_add(self.email_id, True)

		if not self.applicant_name and self.email_id:
			guess = self.email_id.split('@')[0]
			self.applicant_name = ' '.join([p.capitalize() for p in guess.split('.')])

	def check_email_id_is_unique(self):
		if self.email_id:
			names = frappe.db.sql_list("""select name from `tabJob Applicant`
				where email_id=%s and name!=%s and job_title=%s""", (self.email_id, self.name, self.job_title))

			if names:
				frappe.throw(_("Email Address must be unique, already exists for {0}").format(comma_and(names)), frappe.DuplicateEntryError)

