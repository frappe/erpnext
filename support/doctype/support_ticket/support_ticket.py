import webnotes

from utilities.transaction_base import TransactionBase
from home import update_feed

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def send_response(self):
		"""
			Adds a new response to the ticket and sends an email to the sender
		"""
		if not self.doc.new_response:
			webnotes.msgprint("Please write something as a response", raise_exception=1)
		
		subject = '[' + self.doc.name + '] ' + self.doc.subject
		
		response = self.doc.new_response + '\n\n[Please do not change the subject while responding.]'

		signature = webnotes.conn.get_value('Email Settings',None,'support_signature')
		if signature:
			response += '\n\n' + signature

		from webnotes.utils.email_lib import sendmail
		
		sendmail(\
			recipients = [self.doc.raised_by], \
			sender=webnotes.conn.get_value('Email Settings',None,'support_email'), \
			subject=subject, \
			msg=response)

		self.doc.new_response = None
		webnotes.conn.set(self.doc,'status','Waiting for Customer')
		self.make_response_record(response)
	
	def make_response_record(self, response, from_email = None, content_type='text/plain'):
		"""
			Creates a new Support Ticket Response record
		"""
		# add to Support Ticket Response
		from webnotes.model.doc import Document
		d = Document('Support Ticket Response')
		d.from_email = from_email or webnotes.user.name
		d.parent = self.doc.name
		d.mail = response
		d.content_type = content_type
		d.save(1)
		
	def close_ticket(self):
		webnotes.conn.set(self.doc,'status','Closed')
		update_feed(self.doc)

	def reopen_ticket(self):
		webnotes.conn.set(self.doc,'status','Open')		
		update_feed(self.doc)		
