import webnotes

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
			
		thread_id = mail.get_thread_id()

		if webnotes.conn.exists('Support Ticket', thread_id):
			from webnotes.model.code import get_obj
			
			st = get_obj('Support Ticket', thread_id)
			st.make_response_record(content, mail.mail['From'], content_type)
			webnotes.conn.set(st.doc, 'status', 'Open')
			update_feed(st.doc)
			return
				
		# new ticket
		from webnotes.model.doc import Document
		d = Document('Support Ticket')
		d.description = content
		d.subject = mail.mail['Subject']
		d.raised_by = mail.mail['From']
		d.content_type = content_type
		d.status = 'Open'
		try:
			d.save(1)
		except:
			d.description = 'Unable to extract message'
			d.save(1)

		# update feed
		update_feed(d)
		
		# send auto reply
		self.send_auto_reply(d)
		
	def send_auto_reply(self, d):
		"""
			Send auto reply to emails
		"""
		signature = self.email_settings.support_signature

		response = self.email_settings.support_autoreply or ("""
A new Ticket has been raised for your query. If you have any additional information, please
reply back to this mail.
		
We will get back to you as soon as possible

[This is an automatic response]

		""" + (signature or ''))

		from webnotes.utils.email_lib import sendmail
		
		sendmail(\
			recipients = [d.raised_by], \
			sender = self.email_settings.support_email, \
			subject = '['+d.name+'] ' + str(d.subject or ''), \
			msg = response)
		
	def auto_close_tickets(self):
		"""
			Auto Closes Waiting for Customer Support Ticket after 15 days
		"""
		webnotes.conn.sql("update `tabSupport Ticket` set status = 'Closed' where status = 'Waiting for Customer' and date_sub(curdate(),interval 15 Day) > modified")


def get_support_mails():
	"""
		Gets new emails from support inbox and updates / creates Support Ticket records
	"""
	SupportMailbox().get_messages()

