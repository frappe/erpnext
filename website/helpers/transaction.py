# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, formatdate
import json

def get_transaction_list(doctype, start):
	# find customer id
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, 
		"customer")
		
	if customer:
		transactions = webnotes.conn.sql("""select name, creation, currency, grand_total_export 
			from `tab%s` where customer=%s and docstatus=1
			order by creation desc
			limit %s, 20""" % (doctype, "%s", "%s"), (customer, cint(start)), as_dict=True)
		for doc in transactions:
			doc.items = ", ".join(webnotes.conn.sql_list("""select item_name
				from `tab%s Item` where parent=%s limit 5""" % (doctype, "%s"), doc.name))
			doc.creation = formatdate(doc.creation)
		return transactions
	else:
		return []
		
def get_common_args():
	return {
		"global_number_format": webnotes.conn.get_default("number_format") or "#,###.##",
		"currency": webnotes.conn.get_default("currency"),
		"currency_symbols": json.dumps(dict(webnotes.conn.sql("""select name, symbol
			from tabCurrency where ifnull(enabled,0)=1""")))
	}

@webnotes.whitelist()
def get_orders(start=0):
	return get_transaction_list("Sales Order", start)
		
def order_list_args():
	args = get_common_args()
	args.update({
		"title": "My Orders",
		"method": "website.helpers.transaction.get_orders",
		"icon": "icon-list",
		"empty_list_message": "No Orders Yet",
		"page": "order",
	})
	return args

@webnotes.whitelist()
def get_invoices(start=0):
	return get_transaction_list("Sales Invoice", start)

def invoice_list_args():
	args = get_common_args()
	args.update({
		"title": "Invoices",
		"method": "website.helpers.transaction.get_invoices",
		"icon": "icon-file-text",
		"empty_list_message": "No Invoices Found",
		"page": "invoice"
	})
	return args

@webnotes.whitelist()
def get_shipments(start=0):
	return get_transaction_list("Delivery Note", start)

def shipment_list_args():
	args = get_common_args()
	args.update({
		"title": "Shipments",
		"method": "website.helpers.transaction.get_shipments",
		"icon": "icon-truck",
		"empty_list_message": "No Shipments Found",
		"page": "shipment"
	})
	return args
	
@webnotes.whitelist()
def get_tickets(start=0):
	tickets = webnotes.conn.sql("""select name, subject, status, creation 
		from `tabSupport Ticket` where raised_by=%s 
		order by modified desc
		limit %s, 20""", (webnotes.session.user, cint(start)), as_dict=True)
	for t in tickets:
		t.creation = formatdate(t.creation)
	
	return tickets
	
def ticket_list_args():
	return {
		"title": "My Tickets",
		"method": "website.helpers.transaction.get_tickets",
		"icon": "icon-ticket",
		"empty_list_message": "No Tickets Raised",
		"page": "ticket"
	}
	
def get_transaction_args(doctype, name):
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, 
		"customer")
		
	bean = webnotes.bean(doctype, name)
	if bean.doc.customer != customer:
		return {
			"doc": {"name": "Not Allowed"}
		}
	else:
		return {
			"doc": bean.doc,
			"doclist": bean.doclist,
			"webnotes": webnotes,
			"utils": webnotes.utils
		}

def get_order_args():	
	args = get_transaction_args("Sales Order", webnotes.form_dict.name)
	args.update({
		"parent_link": "orders",
		"parent_title": "My Orders"
	})
	return args
	
def get_invoice_args():
	args = get_transaction_args("Sales Invoice", webnotes.form_dict.name)
	args.update({
		"parent_link": "invoices",
		"parent_title": "Invoices"
	})
	return args

def get_shipment_args():
	args = get_transaction_args("Delivery Note", webnotes.form_dict.name)
	args.update({
		"parent_link": "shipments",
		"parent_title": "Shipments"
	})
	return args
