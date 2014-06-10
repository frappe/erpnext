# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
from frappe.utils.email_lib.receive import POP3Mailbox
import _socket, poplib

class SupportEmailSettings(Document):

	def validate(self):
		"""
			Checks support ticket email settings
		"""
		if cint(self.sync_support_mails) and self.mail_server and not frappe.local.flags.in_patch:
			inc_email = frappe._dict(self.as_dict())
			# inc_email.encode()
			inc_email.host = self.mail_server
			inc_email.use_ssl = self.use_ssl
			try:
				err_msg = _('User Name or Support Password missing. Please enter and try again.')
				if not (self.mail_login and self.mail_password):
					raise AttributeError, err_msg
				inc_email.username = self.mail_login
				inc_email.password = self.mail_password
			except AttributeError, e:
				frappe.msgprint(err_msg)
				raise

			pop_mb = POP3Mailbox(inc_email)

			try:
				pop_mb.connect()
			except _socket.error, e:
				# Invalid mail server -- due to refusing connection
				frappe.msgprint(_('Invalid Mail Server. Please rectify and try again.'))
				raise
			except poplib.error_proto, e:
				frappe.msgprint(_('Invalid User Name or Support Password. Please rectify and try again.'))
				raise
