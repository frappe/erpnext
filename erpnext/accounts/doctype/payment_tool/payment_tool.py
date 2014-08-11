# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import json

class PaymentTool(Document):
	pass

@frappe.whitelist()
def get_party_account(party_type, party_name):
	return frappe.db.get_value("Account", {"master_type": party_type, "master_name": party_name})

@frappe.whitelist()
def get_outstanding_vouchers(args):
	from erpnext.accounts.utils import get_outstanding_invoices

	args = json.loads(args)

	check_mandatory_to_fetch(args)

	if args.get("party_type") == "Customer" and args.get("received_or_paid") == "Received":
		amount_query = "ifnull(debit, 0) - ifnull(credit, 0)"
	elif args.get("party_type") == "Supplier" and args.get("received_or_paid") == "Paid":
		amount_query = "ifnull(credit, 0) - ifnull(debit, 0)"
	else:
		frappe.throw(_("Please enter the Against Vouchers manually"))

	# Get all outstanding sales /purchase invoices
	outstanding_invoices = get_outstanding_invoices(amount_query, args.get("party_account"))

	# Get all SO / PO which are not fully billed or aginst which full advance not paid
	orders_to_be_billed = get_orders_to_be_billed(args.get("party_type"), args.get("party_name"))

	return outstanding_invoices + orders_to_be_billed

def check_mandatory_to_fetch(args):
	check_field = [
		['Company', args.get("company")],
		['Party Type', args.get("party_type")],
		['Received Or Paid', args.get("received_or_paid")],
		['Customer / Supplier', args.get("party_name")]
	]

	for key, val in check_field:
		if not val:
			frappe.throw(_("Please select {0} first").format(key))

def get_orders_to_be_billed(party_type, party_name):
	voucher_type = 'Sales Order' if party_type == "Customer" else 'Purchase Order'
	orders = frappe.db.sql("""
		select
			name as voucher_no,
			ifnull(grand_total, 0) as invoice_amount,
			(ifnull(grand_total, 0) - ifnull(advance_paid, 0)) as outstanding_amount,
			transaction_date as posting_date
		from
			`tab%s`
		where
			%s = %s
			and docstatus = 1
			and ifnull(grand_total, 0) > ifnull(advance_paid, 0)
			and ifnull(per_billed, 0) < 100.0
		""" % (voucher_type, 'customer' if party_type == "Customer" else 'supplier', '%s'),
		party_name, as_dict = True)

	order_list = []
	for d in orders:
		d["voucher_type"] = voucher_type
		order_list.append(d)
	
	return order_list
