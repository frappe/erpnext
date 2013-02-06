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

class SalesMailbox(POP3Mailbox):	
	def setup(self, args=None):
		self.settings = args or webnotes.doc("Sales Email Settings", "Sales Email Settings")
	
	def check_mails(self):
		return webnotes.conn.sql("select user from tabSessions where \
			time_to_sec(timediff(now(), lastupdate)) < 1800")
	
	def process_message(self, mail):
		if mail.from_email == self.settings.email_id:
			return
			
		name = webnotes.conn.get_value("Lead", {"email_id": mail.from_email}, "name")
		if name:
			lead = webnotes.model_wrapper("Lead", name)
			lead.doc.status = "Open"
			lead.doc.save()
		else:
			lead = webnotes.model_wrapper({
				"doctype":"Lead",
				"lead_name": mail.from_real_name or mail.from_email,
				"email_id": mail.from_email,
				"status": "Open",
				"source": "Email"
			})
			lead.insert()
		
		mail.save_attachments_in_doc(lead.doc)
				
		make(content=mail.content, sender=mail.from_email, 
			doctype="Lead", name=lead.doc.name, lead=lead.doc.name)

def get_leads():
	if cint(webnotes.conn.get_value('Sales Email Settings', None, 'extract_emails')):
		SalesMailbox()