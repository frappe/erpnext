from __future__ import unicode_literals
import webnotes
def execute():
	webnotes.conn.sql("""\
		DELETE FROM `tabSingles`
		WHERE doctype = 'Control Panel'
		AND field IN ("sync_with_gateway", "mail_password", "auto_email_id",
		"mail_port", "outgoing_mail_server", "mail_login", "use_ssl")""")
