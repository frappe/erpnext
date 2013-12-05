# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, cint, decode_dict, today
from webnotes.utils.email_lib import sendmail		
from webnotes.utils.email_lib.receive import POP3Mailbox
from core.doctype.communication.communication import make

class SupportMailbox(POP3Mailbox):	
	def setup(self, args=None):
		self.email_settings = webnotes.doc("Email Settings", "Email Settings")
		self.settings = args or webnotes._dict({
			"use_ssl": self.email_settings.support_use_ssl,
			"host": self.email_settings.support_host,
			"username": self.email_settings.support_username,
			"password": self.email_settings.support_password
		})
		
	def process_message(self, mail):
		if mail.from_email == self.email_settings.fields.get('support_email'):
			return
		thread_id = mail.get_thread_id()
		new_ticket = False

		if not (thread_id and webnotes.conn.exists("Support Ticket", thread_id)):
			new_ticket = True
		
		ticket = add_support_communication(mail.subject, mail.content, mail.from_email,
			docname=None if new_ticket else thread_id, mail=mail)
			
		if new_ticket and cint(self.email_settings.send_autoreply) and \
			"mailer-daemon" not in mail.from_email.lower():
				self.send_auto_reply(ticket.doc)

	def send_auto_reply(self, d):
		signature = self.email_settings.fields.get('support_signature') or ''
		response = self.email_settings.fields.get('support_autoreply') or ("""
A new Ticket has been raised for your query. If you have any additional information, please
reply back to this mail.
		
We will get back to you as soon as possible
----------------------
Original Query:

""" + d.description + "\n----------------------\n" + cstr(signature))

		sendmail(\
			recipients = [cstr(d.raised_by)], \
			sender = cstr(self.email_settings.fields.get('support_email')), \
			subject = '['+cstr(d.name)+'] ' + cstr(d.subject), \
			msg = cstr(response))
		
	def auto_close_tickets(self):
		webnotes.conn.sql("""update `tabSupport Ticket` set status = 'Closed' 
			where status = 'Replied' 
			and date_sub(curdate(),interval 15 Day) > modified""")

def get_support_mails():
	if cint(webnotes.conn.get_value('Email Settings', None, 'sync_support_mails')):
		SupportMailbox()
		
def add_support_communication(subject, content, sender, docname=None, mail=None):
	if docname:
		ticket = webnotes.bean("Support Ticket", docname)
		ticket.doc.status = 'Open'
		ticket.ignore_permissions = True
		ticket.doc.save()
	else:
		ticket = webnotes.bean([decode_dict({
			"doctype":"Support Ticket",
			"description": content,
			"subject": subject,
			"raised_by": sender,
			"content_type": mail.content_type if mail else None,
			"status": "Open",
		})])
		ticket.ignore_permissions = True
		ticket.insert()
	
	make(content=content, sender=sender, subject = subject,
		doctype="Support Ticket", name=ticket.doc.name,
		date=mail.date if mail else today(), sent_or_received="Received")

	if mail:
		mail.save_attachments_in_doc(ticket.doc)
		
	return ticket