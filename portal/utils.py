# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, formatdate
import json

def get_transaction_list(doctype, start, additional_fields=None):
	# find customer id
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, 
		"customer")
	
	if customer:
		if additional_fields:
			additional_fields = ", " + ", ".join(("`%s`" % f for f in additional_fields))
		else:
			additional_fields = ""
			
		transactions = webnotes.conn.sql("""select name, creation, currency, grand_total_export
			%s
			from `tab%s` where customer=%s and docstatus=1
			order by creation desc
			limit %s, 20""" % (additional_fields, doctype, "%s", "%s"), 
			(customer, cint(start)), as_dict=True)
		for doc in transactions:
			items = webnotes.conn.sql_list("""select item_name
				from `tab%s Item` where parent=%s limit 6""" % (doctype, "%s"), doc.name)
			doc.items = ", ".join(items[:5]) + ("..." if (len(items) > 5) else "")
			doc.creation = formatdate(doc.creation)
		return transactions
	else:
		return []
		
def get_currency_context():
	return {
		"global_number_format": webnotes.conn.get_default("number_format") or "#,###.##",
		"currency": webnotes.conn.get_default("currency"),
		"currency_symbols": json.dumps(dict(webnotes.conn.sql("""select name, symbol
			from tabCurrency where ifnull(enabled,0)=1""")))
	}

def get_transaction_context(doctype, name):
	context = {"session_user": webnotes.session.user}
	
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, 
		"customer")
		
	bean = webnotes.bean(doctype, name)
	if bean.doc.customer != customer:
		context.update({"doc": {"name": "Not Allowed"}})
	else:
		context.update({
			"doc": bean.doc,
			"doclist": bean.doclist,
			"webnotes": webnotes,
			"utils": webnotes.utils
		})
	
	return context

@webnotes.whitelist(allow_guest=True)
def send_message(subject="Website Query", message="", sender="", status="Open"):
	from website.doctype.contact_us_settings.templates.pages.contact \
		import send_message as website_send_message
	
	if not website_send_message(subject, message, sender):
		return
		
	if subject=="Support":
		# create support ticket
		from support.doctype.support_ticket.get_support_mails import add_support_communication
		add_support_communication(subject, message, sender, mail=None)
	else:
		# make lead / communication
		from selling.doctype.lead.get_leads import add_sales_communication
		add_sales_communication(subject or "Website Query", message, sender, sender, 
			mail=None, status=status)
	