import webnotes
sql = webnotes.conn.sql
	
from webnotes.utils import cint, cstr

class DocType:
	def __init__(self,doc,doclist):
		self.doc,self.doclist = doc,doclist

	def set_vals(self):
		res = sql("select field, value from `tabSingles` where doctype = 'Control Panel' and field IN ('outgoing_mail_server','mail_login','mail_password','auto_email_id','mail_port','use_ssl')")
		ret = {}
		for r in res:
			ret[cstr(r[0])]=r[1] and cstr(r[1]) or ''
				
		return ret

	def set_cp_value(self, key):
		"""
			Update value in control panel
		"""
		if self.doc.fields.get(key):
			webnotes.conn.set_value('Control Panel', None, key, self.doc.fields[key])

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
		if self.doc.support_host:
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

		
	def on_update(self):
		"""
			Sets or cancels the event in the scheduler
		"""
		# update control panel
		for f in ('outgoing_mail_server', 'mail_login', 'mail_password', 'auto_email_id', 'mail_port', 'use_ssl'):
			self.set_cp_value(f)

		# setup scheduler for support emails
		if cint(self.doc.sync_support_mails):
			if not (self.doc.support_host and self.doc.support_username and self.doc.support_password):
				webnotes.msgprint("You must give the incoming POP3 settings for support emails to activiate mailbox integration", raise_exception=1)
			
			from webnotes.utils.scheduler import set_event
			set_event('support.doctype.support_ticket.get_support_mails', 60*5, 1)
		else:
			from webnotes.utils.scheduler import cancel_event
			cancel_event('support.doctype.support_ticket.get_support_mails')
