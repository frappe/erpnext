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
from webnotes.model.doc import make_autoname

from utilities.transaction_base import TransactionBase
from home import update_feed

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def onload(self):
		self.add_communication_list()
			
	def send_response(self):
		"""
			Adds a new response to the ticket and sends an email to the sender
		"""
		if not self.doc.new_response:
			webnotes.msgprint("Please write something as a response", raise_exception=1)
		
		import markdown2
		self.doc.new_response = markdown2.markdown(self.doc.new_response)
		
		subject = '[' + self.doc.name + '] ' + (self.doc.subject or 'No Subject Specified')
		
		response = self.doc.new_response + '<p>[Please do not change the subject while responding.]</p>'

		# add last response to new response
		response += self.last_response()

		signature = webnotes.conn.get_value('Email Settings',None,'support_signature')
		if signature:
			response += '<p>' + signature + '</p>'

		from webnotes.utils.email_lib import sendmail
		
		sendmail(\
			recipients = [self.doc.raised_by], \
			sender=webnotes.conn.get_value('Email Settings',None,'support_email'), \
			subject=subject, \
			msg=response)

		self.doc.new_response = None
		webnotes.conn.set(self.doc, 'status', 'Waiting for Customer')
		self.make_response_record(response)
		self.add_communication_list()
	
	def last_response(self):
		"""return last response"""
		tmp = webnotes.conn.sql("""select content from `tabCommunication`
			where support_ticket = %s order by creation desc limit 1
			""", self.doc.name)
			
		if not tmp:
			tmp = webnotes.conn.sql("""
				SELECT description from `tabSupport Ticket`
				where name = %s
			""", self.doc.name)

		response_title = "=== In response to ==="

		if tmp and tmp[0][0]:
			return "\n\n" + response_title + "\n\n" + tmp[0][0].split(response_title)[0]
		else:
			return ""

		
	def make_response_record(self, response, from_email = None, content_type='text/plain'):
		"""
			Creates a new Communication record
		"""
		# add to Communication
		d = webnotes.doc('Communication')
		d.subject = self.doc.subject
		d.email_address = from_email or webnotes.user.name
		self.set_lead_and_contact(d)
		d.support_ticket = self.doc.name
		d.content = response
		d.communication_medium = "Email"
		d.save(1)
	
	def set_lead_and_contact(self, d):
		import email.utils
		email_addr = email.utils.parseaddr(d.email_address)
		# set contact
		if self.doc.contact:
			d.contact = self.doc.contact
		else:
			d.contact = webnotes.conn.get_value("Contact", {"email_id": email_addr[1]}, "name") or None
			if d.contact:
				webnotes.conn.set(self.doc, "contact", d.contact)

		if self.doc.lead:
			d.lead = self.doc.lead
		else:
			d.lead = webnotes.conn.get_value("Lead", {"email_id": email_addr[1]}, "name") or None
			if d.lead:
				webnotes.conn.set(self.doc, "lead", d.lead)

		# not linked to any lead / contact, create new lead
		if not d.lead and not d.contact:
			d.lead = self.make_lead(d, email_addr[0])
			webnotes.conn.set(self.doc, "lead", d.lead)
		
	def make_lead(self, d, real_name):
		d = webnotes.doc("Lead")
		d.lead_name = real_name or d.email_address
		d.email_id = d.email_address
		d.source = "Email"
		d.save(1)
		return d.name
	
	def close_ticket(self):
		webnotes.conn.set(self.doc,'status','Closed')
		update_feed(self.doc)

	def reopen_ticket(self):
		webnotes.conn.set(self.doc,'status','Open')		
		update_feed(self.doc)
		
	def on_trash(self):
		webnotes.conn.sql("""update `tabCommunication set support_ticket="" 
			where support_ticket=%s`""", self.doc.name)
