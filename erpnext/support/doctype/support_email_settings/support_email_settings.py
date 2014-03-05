# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		"""
			Checks support ticket email settings
		"""
		if self.doc.sync_support_mails and self.doc.mail_server:
			from frappe.utils.email_lib.receive import POP3Mailbox
			from frappe.model.doc import Document
			import _socket, poplib
			
			inc_email = Document('Incoming Email Settings')
			inc_email.encode()
			inc_email.host = self.doc.mail_server
			inc_email.use_ssl = self.doc.use_ssl
			try:
				err_msg = 'User Name or Support Password missing. Please enter and try again.'
				if not (self.doc.mail_login and self.doc.mail_password):
					raise AttributeError, err_msg
				inc_email.username = self.doc.mail_login
				inc_email.password = self.doc.mail_password
			except AttributeError, e:
				frappe.msgprint(err_msg)
				raise

			pop_mb = POP3Mailbox(inc_email)
			
			try:
				pop_mb.connect()
			except _socket.error, e:
				# Invalid mail server -- due to refusing connection
				frappe.msgprint('Invalid POP3 Mail Server. Please rectify and try again.')
				raise
			except poplib.error_proto, e:
				frappe.msgprint('Invalid User Name or Support Password. Please rectify and try again.')
				raise
		