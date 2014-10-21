# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, json
from frappe import _
from frappe.utils import cint, formatdate

@frappe.whitelist(allow_guest=True)
def send_message(subject="Website Query", message="", sender="", status="Open"):
	from frappe.templates.pages.contact import send_message as website_send_message

	website_send_message(subject, message, sender)

	comm = frappe.get_doc({
		"doctype":"Communication",
		"subject": subject,
		"content": message,
		"sender": sender,
		"sent_or_received": "Received"
	})
	comm.insert(ignore_permissions=True)

def get_transaction_list(doctype, start, additional_fields=None):
	# find customer id
	customer = frappe.db.get_value("Contact", {"email_id": frappe.session.user},
		"customer")

	if customer:
		if additional_fields:
			additional_fields = ", " + ", ".join(("`%s`" % f for f in additional_fields))
		else:
			additional_fields = ""

		transactions = frappe.db.sql("""select name, creation, currency, grand_total_export
			%s
			from `tab%s` where customer=%s and docstatus=1
			order by creation desc
			limit %s, 20""" % (additional_fields, doctype, "%s", "%s"),
			(customer, cint(start)), as_dict=True)
		for doc in transactions:
			items = frappe.db.sql_list("""select item_name
				from `tab%s Item` where parent=%s limit 6""" % (doctype, "%s"), doc.name)
			doc.items = ", ".join(items[:5]) + ("..." if (len(items) > 5) else "")
			doc.creation = formatdate(doc.creation)
		return transactions
	else:
		return []

def get_currency_context():
	return {
		"global_number_format": frappe.db.get_default("number_format") or "#,###.##",
		"currency": frappe.db.get_default("currency"),
		"currency_symbols": json.dumps(dict(frappe.db.sql("""select name, symbol
			from tabCurrency where ifnull(enabled,0)=1""")))
	}

def get_transaction_context(doctype, name):
	customer = frappe.db.get_value("Contact", {"email_id": frappe.session.user},
		"customer")

	doc = frappe.get_doc(doctype, name)
	if doc.customer != customer:
		return { "doc": frappe._dict({"name": _("Not Allowed")}) }
	else:
		return { "doc": doc }
