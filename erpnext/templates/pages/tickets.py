# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, formatdate

no_cache = 1
no_sitemap = 1

def get_context(context):
	return {
		"title": "My Tickets",
		"method": "erpnext.templates.pages.tickets.get_tickets",
		"icon": "icon-ticket",
		"empty_list_message": "No Tickets Raised",
		"page": "ticket"
	}

@frappe.whitelist()
def get_tickets(start=0):
	tickets = frappe.db.sql("""select name, subject, status, creation
		from `tabIssue` where raised_by=%s
		order by modified desc
		limit %s, 20""", (frappe.session.user, cint(start)), as_dict=True)
	for t in tickets:
		t.creation = formatdate(t.creation)

	return tickets

@frappe.whitelist()
def make_new_ticket(subject, message):
	if not (subject and message):
		raise frappe.throw(_("Please write something in subject and message!"))

	ticket = frappe.get_doc({
		"doctype":"Issue",
		"subject": subject,
		"raised_by": frappe.session.user,
	})
	ticket.insert(ignore_permissions=True)

	comm = frappe.get_doc({
		"doctype":"Communication",
		"subject": subject,
		"content": message,
		"sender": frappe.session.user,
		"sent_or_received": "Received",
		"reference_doctype": "Issue",
		"reference_name": ticket.name
	})
	comm.insert(ignore_permissions=True)

	return ticket.name
