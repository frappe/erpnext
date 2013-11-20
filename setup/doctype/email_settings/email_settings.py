# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
	
from webnotes.utils import cint

class DocType:
	def __init__(self,doc,doclist):
		self.doc,self.doclist = doc,doclist

	def validate(self):
		"""Checks connectivity to email servers before saving"""
		self.validate_outgoing()
		self.validate_incoming()

	def validate_outgoing(self):
		"""Checks incoming email settings"""
		self.doc.encode()
		if self.doc.outgoing_mail_server:
			from webnotes.utils import cint
			from webnotes.utils.email_lib.smtp import SMTPServer
			smtpserver = SMTPServer(login = self.doc.mail_login,
				password = self.doc.mail_password,
				server = self.doc.outgoing_mail_server,
				port = cint(self.doc.mail_port),
				use_ssl = self.doc.use_ssl
			)
						
			# exceptions are handled in session connect
			sess = smtpserver.sess

	def validate_incoming(self):
		"""
			Checks support ticket email settings
		"""
		if self.doc.sync_support_mails and self.doc.support_host:
			from webnotes.utils.email_lib.receive import POP3Mailbox
			from webnotes.model.doc import Document
			import _socket, poplib
			
			inc_email = Document('Incoming Email Settings')
			inc_email.encode()
			inc_email.host = self.doc.support_host
			inc_email.use_ssl = self.doc.support_use_ssl
			try:
				err_msg = 'User Name or Support Password missing. Please enter and try again.'
				if not (self.doc.support_username and self.doc.support_password):
					raise AttributeError, err_msg
				inc_email.username = self.doc.support_username
				inc_email.password = self.doc.support_password
			except AttributeError, e:
				webnotes.msgprint(err_msg)
				raise

			pop_mb = POP3Mailbox(inc_email)
			
			try:
				pop_mb.connect()
			except _socket.error, e:
				# Invalid mail server -- due to refusing connection
				webnotes.msgprint('Invalid POP3 Mail Server. Please rectify and try again.')
				raise
			except poplib.error_proto, e:
				webnotes.msgprint('Invalid User Name or Support Password. Please rectify and try again.')
				raise
