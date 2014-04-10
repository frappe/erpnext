# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint
from frappe.utils.email_lib.receive import POP3Mailbox
from frappe.core.doctype.communication.communication import _make

class JobsMailbox(POP3Mailbox):	
	def setup(self, args=None):
		self.settings = args or frappe.get_doc("Jobs Email Settings", "Jobs Email Settings")
		
	def process_message(self, mail):
		if mail.from_email == self.settings.email_id:
			return
			
		name = frappe.db.get_value("Job Applicant", {"email_id": mail.from_email}, 
			"name")
		if name:
			applicant = frappe.get_doc("Job Applicant", name)
			if applicant.status!="Rejected":
				applicant.status = "Open"
			applicant.ignore_permissions = True
			applicant.save()
		else:
			name = (mail.from_real_name and (mail.from_real_name + " - ") or "") \
				+ mail.from_email
			applicant = frappe.get_doc({
				"creation": mail.date,
				"doctype":"Job Applicant",
				"applicant_name": name,
				"email_id": mail.from_email,
				"status": "Open"
			})
			applicant.ignore_permissions = True
			applicant.ignore_mandatory = True
			applicant.insert()
		
		mail.save_attachments_in_doc(applicant)
				
		_make(content=mail.content, sender=mail.from_email, subject=mail.subject or "No Subject",
			doctype="Job Applicant", name=applicant.name, sent_or_received="Received")

def get_job_applications():
	if cint(frappe.db.get_value('Jobs Email Settings', None, 'extract_emails')):
		JobsMailbox()