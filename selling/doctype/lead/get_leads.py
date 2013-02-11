# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, cint
from webnotes.utils.email_lib.receive import POP3Mailbox
from core.doctype.communication.communication import make

def add_sales_communication(subject, content, sender, real_name, mail=None):
	def set_status_open(doctype, name):
		w = webnotes.model_wrapper(doctype, name)
		w.ignore_permissions = True
		w.doc.status = "Open"
		w.doc.save()
		if mail:
			mail.save_attachments_in_doc(w.doc)

	lead_name = webnotes.conn.get_value("Lead", {"email_id": sender})
	contact_name = webnotes.conn.get_value("Contact", {"email_id": sender})
	is_system_user = webnotes.conn.get_value("Profile", sender)
	
	if not is_system_user:
		if contact_name:
			set_status_open("Contact", contact_name)
		elif lead_name:
			set_status_open("Lead", lead_name)
		else:
			# none, create a new Lead
			lead = webnotes.model_wrapper({
				"doctype":"Lead",
				"lead_name": real_name or sender,
				"email_id": sender,
				"status": "Open",
				"source": "Email"
			})
			lead.ignore_permissions = True
			lead.insert()
			if mail:
				mail.save_attachments_in_doc(lead.doc)

	make(content=content, sender=sender, subject=subject,
		lead=lead_name, contact=contact_name)

class SalesMailbox(POP3Mailbox):	
	def setup(self, args=None):
		self.settings = args or webnotes.doc("Sales Email Settings", "Sales Email Settings")
	
	def check_mails(self):
		return webnotes.conn.sql("select user from tabSessions where \
			time_to_sec(timediff(now(), lastupdate)) < 1800")
	
	def process_message(self, mail):
		if mail.from_email == self.settings.email_id:
			return
		
		add_sales_communication(mail.subject, mail.content, mail.form_email, 
			mail.from_real_name, mail)

def get_leads():
	if cint(webnotes.conn.get_value('Sales Email Settings', None, 'extract_emails')):
		SalesMailbox()