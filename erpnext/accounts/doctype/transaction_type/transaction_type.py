# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
import copy
import json
from six import string_types

class TransactionType(Document):
	def validate(self):
		if not self.buying and not self.selling:
			frappe.throw(_("Transaction Type must be at least one of Selling or Buying type"))


@frappe.whitelist()
def get_transaction_type_defaults(transaction_type, company):
	if transaction_type:
		tranction_type_doc = frappe.get_cached_doc("Transaction Type", transaction_type)
		if tranction_type_doc:
			for d in tranction_type_doc.item_defaults or []:
				if d.company == company:
					row = copy.deepcopy(d.as_dict())
					row.pop("name")
					return row

	return frappe._dict()


@frappe.whitelist()
def get_transaction_type_details(args, items):
	from erpnext.accounts.party import get_party_account_details
	from erpnext.stock.get_item_details import get_item_defaults_info

	args = json.loads(args) if isinstance(args, string_types) else args
	args = frappe._dict(args)
	items = json.loads(items) if isinstance(items, string_types) else items

	party_type = party = account_field = None

	if frappe.get_meta(args.doctype).has_field('debit_to'):
		account_field = 'debit_to'
	elif frappe.get_meta(args.doctype).has_field('credit_to'):
		account_field = 'credit_to'

	if args.letter_of_credit:
		party_type = "Letter of Credit"
		party = args.letter_of_credit
	elif args.supplier:
		party_type = "Supplier"
		party = args.supplier
	elif args.customer:
		party_type = "Customer"
		party = args.customer

	out = frappe._dict({
		"items": get_item_defaults_info(args, items),
		"doc": frappe._dict()
	})

	if args.transaction_type_name:
		transaction_type_doc = frappe.get_cached_doc("Transaction Type", args.transaction_type_name)
		if transaction_type_doc.allocate_advances_automatically:
			out.doc.allocate_advances_automatically = cint(transaction_type_doc.allocate_advances_automatically == "Yes")
		if transaction_type_doc.disable_rounded_total:
			out.doc.disable_rounded_total = cint(transaction_type_doc.disable_rounded_total == "Yes")
		if transaction_type_doc.calculate_tax_on_company_currency:
			out.doc.calculate_tax_on_company_currency = cint(transaction_type_doc.calculate_tax_on_company_currency == "Yes")

		if args.company:
			transaction_type_defaults = get_transaction_type_defaults(args.transaction_type_name, args.company)
			if transaction_type_defaults.get('default_warehouse'):
				out.doc.set_warehouse = transaction_type_defaults.get('default_warehouse')

	if account_field and party_type and party:
		party_account_details = get_party_account_details(party_type, party, args.company,
			transaction_type=args.transaction_type_name)

		out.doc[account_field] = party_account_details.account
		if party_account_details.cost_center:
			out.doc.cost_center = party_account_details.cost_center

	return out
