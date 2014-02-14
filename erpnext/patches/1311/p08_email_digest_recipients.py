# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	from webnotes.utils import extract_email_id
	for name, recipients in webnotes.conn.sql("""select name, recipient_list from `tabEmail Digest`"""):
		recipients = "\n".join([extract_email_id(r) for r in recipients.split("\n")])
		webnotes.conn.set_value("Email Digest", name, "recipient_list", recipients)