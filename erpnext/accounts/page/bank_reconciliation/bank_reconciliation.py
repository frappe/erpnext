# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import difflib
from operator import itemgetter
from frappe.utils import flt

@frappe.whitelist()
def reconcile(bank_transaction, payment_entry):
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	payment_entry = frappe.get_doc("Payment Entry", payment_entry)

	if transaction.payment_entry:
		frappe.throw(_("This bank transaction is already linked to a payment entry"))
	
	if transaction.credit > 0 and payment_entry.payment_type == "Pay":
		frappe.throw(_("The selected payment entry should be linked with a debitor bank transaction"))

	if transaction.debit > 0 and payment_entry.payment_type == "Receive":
		frappe.throw(_("The selected payment entry should be linked with a creditor bank transaction"))

	add_payment_to_transaction(transaction, payment_entry)
	clear_payment_entry(transaction, payment_entry)

	return 'reconciled'

def add_payment_to_transaction(transaction, payment_entry):
	transaction.append("payment_entries", {"payment_entry": payment_entry.name})
	transaction.save()

def clear_payment_entry(transaction, payment_entry):
	linked_bank_transactions = frappe.get_all("Bank Transaction", filters={"payment_entry": payment_entry, "docstatus": 1},
		fields=["sum(debit) as debit", "sum(credit) as credit"])

	cleared_amount = (flt(linked_bank_transactions[0].credit) - flt(linked_bank_transactions[0].debit))

	if cleared_amount == payment_entry.paid_amount:
		frappe.db.set_value("Payment Entry", payment_entry.name, "clearance_date", transaction.date)

@frappe.whitelist()
def get_linked_payments(bank_transaction):

	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	
	# Get all payment entries with a matching amount
	amount_matching = check_matching_amount(transaction)
	print(amount_matching)

	# Get some data from payment entries linked to a corresponding bank transaction
	description_matching = check_matching_descriptions(transaction)
	print(description_matching)

	"""
	if amount_matching:
		match = check_amount_vs_description(amount_matching, description_matching)
		if match:
			return match
		else:
			return merge_matching_lists(amount_matching, description_matching)

	else:
		linked_payments = get_matching_transactions_payments(description_matching)
		return linked_payments
	"""

def check_matching_amount(transaction):
	amount = transaction.credit if transaction.credit > 0 else transaction.debit
	payment_type = "Receive" if transaction.credit > 0 else "Pay"

	payments = frappe.get_all("Payment Entry", fields=["name", "paid_amount", "payment_type", "reference_no", "reference_date", 
		"party", "party_type", "posting_date", "paid_to_account_currency"], filters=[["paid_amount", "like", "{0}%".format(amount)],
		["docstatus", "=", "1"], ["payment_type", "=", payment_type], ["ifnull(clearance_date, '')", "=", ""]])

	return payments

def check_matching_descriptions(transaction):
	bank_transactions = frappe.db.sql(""" 
		SELECT
			bt.name, bt.description, bt.date, btp.payment_document, btp.payment_entry
		FROM
			`tabBank Transaction` as bt
		LEFT JOIN
			`tabBank Transaction Payments` as btp
		ON
			bt.name = btp.parent
		WHERE
			bt.allocated_amount > 0
		AND
			bt.docstatus = 1
		""", as_dict=True)

	selection = []
	for bank_transaction in bank_transactions:
		if bank_transaction.description:
			seq=difflib.SequenceMatcher(lambda x: x == " ", transaction.description, bank_transaction.description)

			if seq.ratio() > 0.5:
				bank_transaction["ratio"] = seq.ratio()
				selection.append(bank_transaction)

	document_types = set([x["payment_document"] for x in selection])

	for document_type in document_types:
		print(document_type)


	return selection

def check_amount_vs_description(amount_matching, description_matching):
	result = []
	print(description_matching)
	print(amount_matching)
	for match in amount_matching:
		m = [match for x in description_matching.payment_entries if match["name"]==x["payment_entry"]]
		result.append(m)
	print(result)
	return result

def merge_matching_lists(amount_matching, description_matching):
	
	for match in amount_matching:
		if match["name"] in map(itemgetter('payment_entry'), description_matching):
			index = map(itemgetter('payment_entry'), description_matching).index(match["name"])
			del description_matching[index]

	linked_payments = get_matching_transactions_payments(description_matching)

	result = amount_matching.append(linked_payments)
	return sorted(result, key = lambda x: x["posting_date"], reverse=True)

def get_matching_transactions_payments(description_matching):
	payments = [x["payment_entry"] for x in description_matching]

	payment_by_ratio = {x["payment_entry"]: x["ratio"] for x in description_matching}

	if payments:
		reference_payment_list = frappe.get_all("Payment Entry", fields=["name", "paid_amount", "payment_type", "reference_no", "reference_date", 
			"party", "party_type", "posting_date", "paid_to_account_currency"], filters=[["name", "in", payments]])

		return sorted(reference_payment_list, key=lambda x: payment_by_ratio[x["name"]])

	else:
		return []