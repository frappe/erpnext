# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _
from frappe.model.document import Document
from erpnext.accounts.utils import outstanding_voucher_list
import json

class PaymentTool(Document):
	pass

@frappe.whitelist()
def get_outstanding_vouchers(args):
	args = json.loads(args)

	check_mandatory_to_fetch(args.get("company"), args.get("party_type"), args.get("customer"), 
		args.get("supplier"), args.get("received_or_paid"))

	if args.get("party_type") == "Customer" and args.get("received_or_paid") == "Received":
		amount_query = "ifnull(debit, 0) - ifnull(credit, 0)"
		final_order_list = order_list(args.get("customer"), args.get("party_type"))
	
	elif args.get("party_type") == "Supplier" and args.get("received_or_paid") == "Paid":
		amount_query = "ifnull(credit, 0) - ifnull(debit, 0)"
		final_order_list = order_list(args.get("supplier"), args.get("party_type"))
	else:
		frappe.throw(_("Please enter the Against Invoice details manually to create JV"))

	all_outstanding_vouchers = outstanding_voucher_list(amount_query, args.get("account_name"))

	if len(final_order_list):		
		all_outstanding_vouchers.extend(final_order_list)

	return all_outstanding_vouchers

@frappe.whitelist()
def get_account_name(party_type, party_name):
	return frappe.db.get_value("Account", {"account_name": party_name, 
		"master_type": party_type}, fieldname = "name")

def order_list(party_name, party_type):
	final_order_list = []
	order_type = 'Sales Order' if party_type == "Customer" else 'Purchase Order'

	order_list = frappe.db.sql("""
		select
			name as voucher_no, ifnull(grand_total, 0) as invoice_amount,
			ifnull(advance_paid, 0) as advance_paid, transaction_date as posting_date
		from
			`tab%s`
		where
			customer = %s 
			and docstatus = 1
			and ifnull(grand_total, 0) > ifnull(advance_paid, 0)
		group by voucher_no			 
		""" % (order_type, '%s'), party_name, as_dict = True)

	for d in order_list:
		final_order_list.append({
			'voucher_no': d.voucher_no, 
			'voucher_type': order_type,
			'posting_date': d.posting_date, 
			'invoice_amount': flt(d.invoice_amount), 
			'outstanding_amount': flt(d.invoice_amount) - flt(d.advance_paid)
			})

	return final_order_list

def check_mandatory_to_fetch(company, party_type, customer, supplier, received_or_paid):
	check_field = {
	'Company': company,
	'Party Type': party_type,
	'Received Or Paid': received_or_paid,
	'Party Name': customer if party_type == "Customer" else supplier
	}

	for key in check_field:
		if not check_field.get(key):
			frappe.throw(_("Please select {0} field first").format(party_type if key == 'Party Name' else key))