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

import webnotes
from webnotes.utils import cstr

from webnotes.utils.email_lib.receive import POP3Mailbox

class SupportMailbox(POP3Mailbox):
	def __init__(self):
		"""
			settings_doc must contain
			use_ssl, host, username, password
		"""
		from webnotes.model.doc import Document

		# extract email settings
		self.email_settings = Document('Email Settings','Email Settings')
		if not self.email_settings.fields.get('sync_support_mails'): return
		
		s = Document('Support Email Settings')
		s.use_ssl = self.email_settings.support_use_ssl
		s.host = self.email_settings.support_host
		s.username = self.email_settings.support_username
		s.password = self.email_settings.support_password
		
		POP3Mailbox.__init__(self, s)
	
	def check_mails(self):
		"""
			returns true if there are active sessions
		"""
		self.auto_close_tickets()
		return webnotes.conn.sql("select user from tabSessions where time_to_sec(timediff(now(), lastupdate)) < 1800")
	
	def process_message(self, mail):
		"""
			Updates message from support email as either new or reply
		"""
		from home import update_feed

		content, content_type = '[Blank Email]', 'text/plain'
		if mail.text_content:
			content, content_type = mail.text_content, 'text/plain'
		else:
			content, content_type = mail.html_content, 'text/html'
			
		thread_list = mail.get_thread_id()


		email_id = mail.mail['From']
		if "<" in mail.mail['From']:
			import re
			re_result = re.findall('(?<=\<)(\S+)(?=\>)', mail.mail['From'])
			if re_result and re_result[0]: email_id = re_result[0]


		for thread_id in thread_list:
			exists = webnotes.conn.sql("""\
				SELECT name
				FROM `tabSupport Ticket`
				WHERE name=%s AND raised_by REGEXP %s
				""" , (thread_id, '(' + email_id + ')'))
			if exists and exists[0] and exists[0][0]:
				from webnotes.model.code import get_obj
				
				st = get_obj('Support Ticket', thread_id)
				st.make_response_record(content, mail.mail['From'], content_type)
				webnotes.conn.set(st.doc, 'status', 'Open')
				update_feed(st.doc, 'on_update')
				webnotes.conn.commit()
				# extract attachments
				self.save_attachments(st.doc, mail.attachments)
				return
				
		from webnotes.model.doctype import get_property
		opts = get_property('Support Ticket', 'options', 'naming_series')
		# new ticket
		from webnotes.model.doc import Document
		d = Document('Support Ticket')
		d.description = content
		d.subject = mail.mail['Subject']
		d.raised_by = mail.mail['From']
		d.content_type = content_type
		d.status = 'Open'
		d.naming_series = opts and opts.split("\n")[0] or 'SUP'
		try:
			d.save(1)
		except:
			d.description = 'Unable to extract message'
			d.save(1)

		else:
			# update feed
			update_feed(d, 'on_update')

			# send auto reply
			self.send_auto_reply(d)

			webnotes.conn.commit()
			
			# extract attachments
			self.save_attachments(d, mail.attachments)
			

	def save_attachments(self, doc, attachment_list=[]):
		"""
			Saves attachments from email

			attachment_list is a list of dict containing:
			'filename', 'content', 'content-type'
		"""
		from webnotes.utils.file_manager import save_file, add_file_list
		for attachment in attachment_list:
			webnotes.conn.begin()
			fid = save_file(attachment['filename'], attachment['content'], 'Support')
			status = add_file_list('Support Ticket', doc.name, attachment['filename'], fid)
			if not status:
				doc.description = doc.description \
					+ "\nCould not attach: " + cstr(attachment['filename'])
				doc.save()
			webnotes.conn.commit()

		
	def send_auto_reply(self, d):
		"""
			Send auto reply to emails
		"""
		from webnotes.utils import cstr
		signature = self.email_settings.fields.get('support_signature') or ''

		response = self.email_settings.fields.get('support_autoreply') or ("""
A new Ticket has been raised for your query. If you have any additional information, please
reply back to this mail.
		
We will get back to you as soon as possible

[This is an automatic response]

		""" + cstr(signature))

		from webnotes.utils.email_lib import sendmail
		
		sendmail(\
			recipients = [cstr(d.raised_by)], \
			sender = cstr(self.email_settings.fields.get('support_email')), \
			subject = '['+cstr(d.name)+'] ' + cstr(d.subject), \
			msg = cstr(response))
		
	def auto_close_tickets(self):
		"""
			Auto Closes Waiting for Customer Support Ticket after 15 days
		"""
		webnotes.conn.sql("update `tabSupport Ticket` set status = 'Closed' where status = 'Waiting for Customer' and date_sub(curdate(),interval 15 Day) > modified")


def get_support_mails():
	"""
		Gets new emails from support inbox and updates / creates Support Ticket records
	"""
	import webnotes
	if webnotes.conn.get_value('Email Settings', None, 'sync_support_mails'):
		SupportMailbox().get_messages()