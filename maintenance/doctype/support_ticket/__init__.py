import webnotes

from webnotes.utils.email_lib.receive import POP3Mailbox

class SupportMailbox(POP3Mailbox):
	def __init__(self):
		"""
			settings_doc must contain
			is_ssl, host, username, password
		"""
		POP3Mailbox.__init__(self, 'Support Email Settings')
	
	def check_mails(self):
		"""
			returns true if there are active sessions
		"""
		return webnotes.conn.sql("select user from tabSessions where time_to_sec(timediff(now(), lastupdate)) < 1800")
	
	def process_message(self, mail):
		"""
			Updates message from support email as either new or reply
		"""
		from event_updates import update_feed

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
			webnotes.conn.set(st.doc, 'status', 'To Reply')
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

def get_support_mails():
	"""
		Gets new emails from support inbox and updates / creates Support Ticket records
	"""
	SupportMailbox().get_messages()