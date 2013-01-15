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

class SupportMailbox(POP3Mailbox):
	def __init__(self):
		s = webnotes.doc('Support Email Settings')
		s.use_ssl = self.email_settings.support_use_ssl
		s.host = self.email_settings.support_host
		s.username = self.email_settings.support_username
		s.password = self.email_settings.support_password
		
		POP3Mailbox.__init__(self, s)
	
	def check_mails(self):
		self.auto_close_tickets()
		return webnotes.conn.sql("select user from tabSessions where \
			time_to_sec(timediff(now(), lastupdate)) < 1800")
	
	def process_message(self, mail):
		from home import update_feed
			
		thread_list = mail.get_thread_id()

		for thread_id in thread_list:
			exists = webnotes.conn.sql("""\
				SELECT name
				FROM `tabSupport Ticket`
				WHERE name=%s AND raised_by REGEXP %s
				""" , (thread_id, '(' + email_id + ')'))
			if exists and exists[0] and exists[0][0]:
				st = webnotes.get_obj('Support Ticket', thread_id)
				
				from core.doctype.communication.communication import make
				
				make(content=mail.content, sender=mail.from_email, 
					doctype="Support Ticket",
					name=thread_id, lead = st.doc.lead, contact=st.doc.contact)
				
				st.doc.status = 'Open'
				st.doc.save()
				
				update_feed(st, 'on_update')
				# extract attachments
				mail.save_attachments_in_doc(st.doc)
				return
				
		from webnotes.model.doctype import get_property
		opts = get_property('Support Ticket', 'options', 'naming_series')
		# new ticket
		from webnotes.model.doc import Document
		d = Document('Support Ticket')
		d.description = mail.content
		
		d.subject = mail.mail['Subject']
		
		d.raised_by = mail.from_email
		d.content_type = mail.content_type
		d.status = 'Open'
		d.naming_series = opts and opts.split("\n")[0] or 'SUP'
		try:
			d.save(1)
			mail.save_attachments_in_doc(d)
		except:
			d.description = 'Unable to extract message'
			d.save(1)
		else:
			# send auto reply
			if cint(self.email_settings.send_autoreply):
				if "mailer-daemon" not in d.raised_by.lower():
					self.send_auto_reply(d)
		
	def send_auto_reply(self, d):
		from webnotes.utils import cstr

		signature = self.email_settings.fields.get('support_signature') or ''

		response = self.email_settings.fields.get('support_autoreply') or ("""
A new Ticket has been raised for your query. If you have any additional information, please
reply back to this mail.
		
We will get back to you as soon as possible
----------------------
Original Query:

""" + d.description + "\n----------------------\n" + cstr(signature))

		from webnotes.utils.email_lib import sendmail		
		
		sendmail(\
			recipients = [cstr(d.raised_by)], \
			sender = cstr(self.email_settings.fields.get('support_email')), \
			subject = '['+cstr(d.name)+'] ' + cstr(d.subject), \
			msg = cstr(response))
		
	def auto_close_tickets(self):
		webnotes.conn.sql("""update `tabSupport Ticket` set status = 'Closed' 
			where status = 'Waiting for Customer' 
			and date_sub(curdate(),interval 15 Day) > modified""")


def get_support_mails():
	import webnotes
	from webnotes.utils import cint
	if cint(webnotes.conn.get_value('Email Settings', None, 'sync_support_mails')):
		SupportMailbox().get_messages()