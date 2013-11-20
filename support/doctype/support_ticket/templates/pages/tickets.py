# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, formatdate

no_cache = True

def get_context():
	return {
		"title": "My Tickets",
		"method": "support.doctype.support_ticket.templates.pages.tickets.get_tickets",
		"icon": "icon-ticket",
		"empty_list_message": "No Tickets Raised",
		"page": "ticket"
	}

@webnotes.whitelist()
def get_tickets(start=0):
	tickets = webnotes.conn.sql("""select name, subject, status, creation 
		from `tabSupport Ticket` where raised_by=%s 
		order by modified desc
		limit %s, 20""", (webnotes.session.user, cint(start)), as_dict=True)
	for t in tickets:
		t.creation = formatdate(t.creation)
	
	return tickets
	
@webnotes.whitelist()
def make_new_ticket(subject, message):
	if not (subject and message):
		raise webnotes.throw(_("Please write something in subject and message!"))
		
	from support.doctype.support_ticket.get_support_mails import add_support_communication
	ticket = add_support_communication(subject, message, webnotes.session.user)
	
	return ticket.doc.name