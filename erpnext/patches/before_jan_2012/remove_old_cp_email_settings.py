def execute():
	"""
		remove control panel email settings if automail.webnotestech.com
	"""
	from webnotes.model.doc import Document
	cp = Document('Control Panel', 'Control Panel')
	if cp:
		if cp.outgoing_mail_server == 'mail.webnotestech.com':
			cp.outgoing_mail_server = None;
			cp.mail_login = None;
			cp.mail_password = None;
			cp.mail_port = None;
			cp.auto_email_id = 'automail@erpnext.com'
			cp.save()

