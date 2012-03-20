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
sql = webnotes.conn.sql
	
from webnotes.utils import cint, cstr

class DocType:
	def __init__(self,doc,doclist):
		self.doc,self.doclist = doc,doclist

	def validate(self):
		"""
			Checks connectivity to email servers before saving
		"""
		self.validate_outgoing()
		self.validate_incoming()

	
	def validate_outgoing(self):
		"""
			Checks incoming email settings
		"""
		if self.doc.outgoing_mail_server:
			from webnotes.utils import cint
			import _socket
			from webnotes.utils.email_lib.send import EMail
			import smtplib
			out_email = EMail()
			out_email.server = self.doc.outgoing_mail_server.encode('utf-8')
			out_email.port = cint(self.doc.mail_port)
			out_email.use_ssl = self.doc.use_ssl
			try:
				out_email.login = self.doc.mail_login.encode('utf-8')
				out_email.password =  self.doc.mail_password.encode('utf-8')
			except AttributeError, e:
				webnotes.msgprint('Login Id or Mail Password missing. Please enter and try again.')
				webnotes.msgprint(e)
			
			try:
				sess = out_email.smtp_connect()
				try:
					sess.quit()
				except:
					pass
			except _socket.error, e:
				# Invalid mail server -- due to refusing connection
				webnotes.msgprint('Invalid Outgoing Mail Server. Please rectify and try again.')
				webnotes.msgprint(e)
			except smtplib.SMTPAuthenticationError, e:
				webnotes.msgprint('Invalid Login Id or Mail Password. Please rectify and try again.')
			except smtplib.SMTPException, e:
				webnotes.msgprint('There is something wrong with your Outgoing Mail Settings. \
				Please contact us at support@erpnext.com')
				webnotes.msgprint(e)
		

	def validate_incoming(self):
		"""
			Checks support ticket email settings
		"""
		if self.doc.sync_support_mails and self.doc.support_host:
			from webnotes.utils.email_lib.receive import POP3Mailbox
			from webnotes.model.doc import Document
			import _socket, poplib
			inc_email = Document('Incoming Email Settings')
			inc_email.host = self.doc.support_host.encode('utf-8')
			inc_email.use_ssl = self.doc.support_use_ssl
			try:
				inc_email.username = self.doc.support_username.encode('utf-8')
				inc_email.password = self.doc.support_password.encode('utf-8')
			except AttributeError, e:
				webnotes.msgprint('User Name or Support Password missing. Please enter and try again.')
				webnotes.msgprint(e)

			pop_mb = POP3Mailbox(inc_email)
			
			try:
				pop_mb.connect()
			except _socket.error, e:
				# Invalid mail server -- due to refusing connection
				webnotes.msgprint('Invalid POP3 Mail Server. Please rectify and try again.')
				webnotes.msgprint(e)
			except poplib.error_proto, e:
				webnotes.msgprint('Invalid User Name or Support Password. Please rectify and try again.')
				webnotes.msgprint(e)
