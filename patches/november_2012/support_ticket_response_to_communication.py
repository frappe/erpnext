# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
import email.utils

def execute():
	webnotes.reload_doc("core", "doctype", "communication")
	webnotes.conn.commit()
	for d in webnotes.conn.sql("""select owner, creation, modified, modified_by, parent, 
		from_email, mail from `tabSupport Ticket Response`""", as_dict=1):
		c = webnotes.doc("Communication")
		c.creation = d.creation
		c.owner = d.owner
		c.modified = d.modified
		c.modified_by = d.modified_by
		c.naming_series = "COMM-"
		c.subject = "response to Support Ticket: " + d.parent
		c.content = d.mail
		c.email_address = d.from_email
		c.support_ticket = d.parent
		email_addr = email.utils.parseaddr(c.email_address)[1]
		c.contact = webnotes.conn.get_value("Contact", {"email_id": email_addr}, "name") or None
		c.lead = webnotes.conn.get_value("Lead", {"email_id": email_addr}, "name") or None
		c.communication_medium = "Email"
		webnotes.conn.begin()
		c.save(1, keep_timestamps=True)
		webnotes.conn.commit()
		
	webnotes.delete_doc("DocType", "Support Ticket Response")
