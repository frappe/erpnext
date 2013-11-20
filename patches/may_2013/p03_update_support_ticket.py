# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
def execute():
	webnotes.reload_doc("support", "doctype", "support_ticket")
	webnotes.reload_doc("core", "doctype", "communication")
	for d in webnotes.conn.sql("""select name, raised_by from `tabSupport Ticket` 
			where docstatus < 2""", as_dict=True):
		tic = webnotes.get_obj("Support Ticket", d.name)
		tic.set_lead_contact(d.raised_by)
		webnotes.conn.sql("""update `tabSupport Ticket` set lead = %s, contact = %s, company = %s 
			where name = %s""", (tic.doc.lead, tic.doc.contact, tic.doc.company, d.name