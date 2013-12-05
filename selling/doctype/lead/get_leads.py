# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, cint
from webnotes.utils.email_lib.receive import POP3Mailbox
from core.doctype.communication.communication import make

def add_sales_communication(subject, content, sender, real_name, mail=None, 
	status="Open", date=None):
	lead_name = webnotes.conn.get_value("Lead", {"email_id": sender})
	contact_name = webnotes.conn.get_value("Contact", {"email_id": sender})

	if not (lead_name or contact_name):
		# none, create a new Lead
		lead = webnotes.bean({
			"doctype":"Lead",
			"lead_name": real_name or sender,
			"email_id": sender,
			"status": status,
			"source": "Email"
		})
		lead.ignore_permissions = True
		lead.insert()
		lead_name = lead.doc.name

	parent_doctype = "Contact" if contact_name else "Lead"
	parent_name = contact_name or lead_name

	message = make(content=content, sender=sender, subject=subject,
		doctype = parent_doctype, name = parent_name, date=date, sent_or_received="Received")
	
	if mail:
		# save attachments to parent if from mail
		bean = webnotes.bean(parent_doctype, parent_name)
		mail.save_attachments_in_doc(bean.doc)

class SalesMailbox(POP3Mailbox):	
	def setup(self, args=None):
		self.settings = args or webnotes.doc("Sales Email Settings", "Sales Email Settings")
		
	def process_message(self, mail):
		if mail.from_email == self.settings.email_id:
			return
		
		add_sales_communication(mail.subject, mail.content, mail.from_email, 
			mail.from_real_name, mail=mail, date=mail.date)

def get_leads():
	if cint(webnotes.conn.get_value('Sales Email Settings', None, 'extract_emails')):
		SalesMailbox()