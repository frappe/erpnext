# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, cint
from webnotes.utils.email_lib.receive import POP3Mailbox
from core.doctype.communication.communication import make

class JobsMailbox(POP3Mailbox):	
	def setup(self, args=None):
		self.settings = args or webnotes.doc("Jobs Email Settings", "Jobs Email Settings")
		
	def process_message(self, mail):
		if mail.from_email == self.settings.email_id:
			return
			
		name = webnotes.conn.get_value("Job Applicant", {"email_id": mail.from_email}, 
			"name")
		if name:
			applicant = webnotes.bean("Job Applicant", name)
			if applicant.doc.status!="Rejected":
				applicant.doc.status = "Open"
			applicant.doc.save()
		else:
			name = (mail.from_real_name and (mail.from_real_name + " - ") or "") \
				+ mail.from_email
			applicant = webnotes.bean({
				"creation": mail.date,
				"doctype":"Job Applicant",
				"applicant_name": name,
				"email_id": mail.from_email,
				"status": "Open"
			})
			applicant.insert()
		
		mail.save_attachments_in_doc(applicant.doc)
				
		make(content=mail.content, sender=mail.from_email, 
			doctype="Job Applicant", name=applicant.doc.name, sent_or_received="Received")

def get_job_applications():
	if cint(webnotes.conn.get_value('Jobs Email Settings', None, 'extract_emails')):
		JobsMailbox()