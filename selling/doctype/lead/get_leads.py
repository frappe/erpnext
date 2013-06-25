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

def add_sales_communication(subject, content, sender, real_name, mail=None, 
	status="Open", date=None):
	def set_status(doctype, name):
		w = webnotes.bean(doctype, name)
		w.ignore_permissions = True
		w.doc.status = is_system_user and "Replied" or status
		w.doc.save()
		if mail:
			mail.save_attachments_in_doc(w.doc)

	lead_name = webnotes.conn.get_value("Lead", {"email_id": sender})
	contact_name = webnotes.conn.get_value("Contact", {"email_id": sender})
	is_system_user = webnotes.conn.get_value("Profile", sender)

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

	make(content=content, sender=sender, subject=subject,
		lead=lead_name, contact=contact_name, date=date)
	
	if contact_name:
		set_status("Contact", contact_name)
	elif lead_name:
		set_status("Lead", lead_name)
	

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