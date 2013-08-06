# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import extract_email_id

def execute():
	email_lead = {}
	for name, email in webnotes.conn.sql("""select name, email_id from `tabLead`
		where ifnull(email_id, '')!='' order by creation asc"""):
		email = extract_email_id(email)
		if email:
			if email not in email_lead:
				email_lead[email] = name
			else:
				webnotes.rename_doc("Lead", name, email_lead[email], force=True, merge=True)