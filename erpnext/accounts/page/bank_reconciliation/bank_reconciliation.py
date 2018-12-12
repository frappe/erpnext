# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import difflib
from operator import itemgetter
from frappe.utils import flt
from six import iteritems

@frappe.whitelist()
def reconcile(bank_transaction, payment_doctype, payment_name):
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	payment_entry = frappe.get_doc(payment_doctype, payment_name)

	account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
	gl_entry = frappe.get_doc("GL Entry", dict(account=account, voucher_type=payment_doctype, voucher_no=payment_name))

	if transaction.unallocated_amount == 0:
		frappe.throw(_("This bank transaction is already fully reconciled"))

	if transaction.credit > 0 and gl_entry.credit > 0:
		frappe.throw(_("The selected payment entry should be linked with a debitor bank transaction"))

	if transaction.debit > 0 and gl_entry.debit > 0:
		frappe.throw(_("The selected payment entry should be linked with a creditor bank transaction"))

	add_payment_to_transaction(transaction, payment_entry, gl_entry)
	clear_payment_entry(transaction, payment_entry, gl_entry)

	return 'reconciled'

def add_payment_to_transaction(transaction, payment_entry, gl_entry):
	transaction.append("payment_entries", {
		"payment_document": payment_entry.doctype, 
		"payment_entry": payment_entry.name,
		"allocated_amount": gl_entry.credit if gl_entry.credit > 0 else gl_entry.debit
	})
	transaction.save()

def clear_payment_entry(transaction, payment_entry, gl_entry):
	linked_bank_transactions = frappe.db.sql("""
		SELECT
			bt.credit, bt.debit
		FROM
			`tabBank Transaction Payments` as btp
		LEFT JOIN
			`tabBank Transaction` as bt on btp.parent=bt.name
		WHERE
			btp.payment_document = '%s'
		AND
			btp.payment_entry = '%s'
		AND
			bt.docstatus = 1
	""" % (payment_entry.doctype, payment_entry.name), as_dict=True)

	amount_cleared = (flt(linked_bank_transactions[0].credit) - flt(linked_bank_transactions[0].debit))
	amount_to_be_cleared = (flt(gl_entry.debit) - flt(gl_entry.credit))

	if payment_entry.doctype == "Payment Entry":
		clear_simple_entry(amount_cleared, amount_to_be_cleared, payment_entry, transaction)

	elif payment_entry.doctype == "Journal Entry":
		clear_simple_entry(amount_cleared, amount_to_be_cleared, payment_entry, transaction)

	elif payment_entry.doctype == "Sales Invoice":
		clear_sales_invoice(amount_cleared, amount_to_be_cleared, payment_entry, transaction)

	elif payment_entry.doctype == "Purchase Invoice":
		clear_simple_entry(amount_cleared, amount_to_be_cleared, payment_entry, transaction)

	elif payment_entry.doctype == "Expense Claim":
		clear_simple_entry(amount_cleared, amount_to_be_cleared, payment_entry, transaction)

def clear_simple_entry(amount_cleared, amount_to_be_cleared, payment_entry, transaction):
	if amount_cleared == amount_to_be_cleared:
		frappe.db.set_value(payment_entry.doctype, payment_entry.name, "clearance_date", transaction.date)

def clear_sales_invoice(amount_cleared, amount_to_be_cleared, payment_entry, transaction):
	if amount_cleared == amount_to_be_cleared:
		frappe.db.set_value("Sales Invoice Payment", dict(parenttype=payment_entry.doctype,
			parent=payment_entry.name), "clearance_date", transaction.date)

@frappe.whitelist()
def get_linked_payments(bank_transaction):
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	bank_account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
	
	# Get all payment entries with a matching amount
	amount_matching = check_matching_amount(bank_account, transaction)

	# Get some data from payment entries linked to a corresponding bank transaction
	description_matching = get_matching_descriptions_data(bank_account, transaction)

	if amount_matching:
		return check_amount_vs_description(amount_matching, description_matching)

	elif description_matching:
		return sorted(description_matching, key = lambda x: x["posting_date"], reverse=True)

	else:
		return []

def check_matching_amount(bank_account, transaction):
	payments = []
	amount = transaction.credit if transaction.credit > 0 else transaction.debit

	payment_type = "Receive" if transaction.credit > 0 else "Pay"
	account_from_to = "paid_to" if transaction.credit > 0 else "paid_from"
	currency_field = "paid_to_account_currency as currency" if transaction.credit > 0 else "paid_from_account_currency as currency"
	payment_entries = frappe.get_all("Payment Entry", fields=["'Payment Entry' as doctype", "name", "paid_amount", "payment_type", "reference_no", "reference_date", 
		"party", "party_type", "posting_date", "{0}".format(currency_field)], filters=[["paid_amount", "like", "{0}%".format(amount)],
		["docstatus", "=", "1"], ["payment_type", "=", payment_type], ["ifnull(clearance_date, '')", "=", ""], ["{0}".format(account_from_to), "=", "{0}".format(bank_account)]])

	payment_field = "jea.debit_in_account_currency" if transaction.credit > 0 else "jea.credit_in_account_currency"
	journal_entries = frappe.db.sql("""
		SELECT
			'Journal Entry' as doctype, je.name, je.posting_date, je.cheque_no as reference_no,
			je.pay_to_recd_from as party, je.cheque_date as reference_date, %s as paid_amount
		FROM
			`tabJournal Entry Account` as jea
		JOIN
			`tabJournal Entry` as je
		ON
			jea.parent = je.name
		WHERE
			(je.clearance_date is null or je.clearance_date='0000-00-00')
		AND
			jea.account = '%s'
		AND
			%s like '%s'
		AND
			je.docstatus = 1
	""" % (payment_field, bank_account, payment_field, amount), as_dict=True)

	sales_invoices = frappe.db.sql("""
		SELECT
			'Sales Invoice' as doctype, si.name, si.customer as party,
			si.posting_date, sip.amount as paid_amount
		FROM
			`tabSales Invoice Payment` as sip
		JOIN
			`tabSales Invoice` as si
		ON
			sip.parent = si.name
		WHERE
			(sip.clearance_date is null or sip.clearance_date='0000-00-00')
		AND
			sip.account = '%s'
		AND
			sip.amount like '%s'
		AND
			si.docstatus = 1
	""" % (bank_account, amount), as_dict=True)

	for data in [payment_entries, journal_entries, sales_invoices]:
		if data:
			payments.extend(data)

	return payments

def get_matching_descriptions_data(bank_account, transaction):
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

			if seq.ratio() > 0.6:
				bank_transaction["ratio"] = seq.ratio()
				selection.append(bank_transaction)

	document_types = set([x["payment_document"] for x in selection])

	links = {}
	for document_type in document_types:
		links[document_type] = [x["payment_entry"] for x in selection if x["payment_document"]==document_type]


	data = []
	for key, value in iteritems(links):
		if key == "Payment Entry":
			data.extend(frappe.get_all("Payment Entry", filters=[["name", "in", value]], fields=["'Payment Entry' as doctype", "posting_date", "party", "reference_no", "reference_date", "paid_amount"]))
		if key == "Journal Entry":
			data.extend(frappe.get_all("Journal Entry", filters=[["name", "in", value]], fields=["'Journal Entry' as doctype", "posting_date", "paid_to_recd_from as party", "cheque_no as reference_no", "cheque_date as reference_date"]))
		if key == "Sales Invoice":
			data.extend(frappe.get_all("Sales Invoice", filters=[["name", "in", value]], fields=["'Sales Invoice' as doctype", "posting_date", "customer_name as party"]))
		if key == "Purchase Invoice":
			data.append(frappe.get_all("Purchase Invoice", filters=[["name", "in", value]], fields=["'Purchase Invoice' as doctype", "posting_date", "supplier_name as party"]))
		if key == "Purchase Invoice":
			data.append(frappe.get_all("Expense Claim", filters=[["name", "in", value]], fields=["'Expense Claim' as doctype", "posting_date", "employee_name as party"]))

	return data

def check_amount_vs_description(amount_matching, description_matching):
	result = []

	if description_matching:
		for am_match in amount_matching:
			for des_match in description_matching:
				if am_match["party"] == des_match["party"]:
					if am_match not in result:
						result.append(am_match)
						continue

				if hasattr(am_match, "reference_no") and hasattr(des_match, "reference_no"):
					if difflib.SequenceMatcher(lambda x: x == " ", am_match["reference_no"], des_match["reference_no"]) > 70:
						if am_match not in result:
							result.append(am_match)
		if result:
			return sorted(result, key = lambda x: x["posting_date"], reverse=True)
		else:
			return sorted(amount_matching, key = lambda x: x["posting_date"], reverse=True)

	else:
		return sorted(amount_matching, key = lambda x: x["posting_date"], reverse=True)

def get_matching_transactions_payments(description_matching):
	payments = [x["payment_entry"] for x in description_matching]

	payment_by_ratio = {x["payment_entry"]: x["ratio"] for x in description_matching}

	if payments:
		reference_payment_list = frappe.get_all("Payment Entry", fields=["name", "paid_amount", "payment_type", "reference_no", "reference_date", 
			"party", "party_type", "posting_date", "paid_to_account_currency"], filters=[["name", "in", payments]])

		return sorted(reference_payment_list, key=lambda x: payment_by_ratio[x["name"]])

	else:
		return []

def journal_entry_query(doctype, txt, searchfield, start, page_len, filters):
	account = frappe.db.get_value("Bank Account", filters.get("bank_account"), "account")

	return frappe.db.sql("""
		SELECT
			jea.parent, je.pay_to_recd_from, 
			if(jea.debit_in_account_currency > 0, jea.debit_in_account_currency, jea.credit_in_account_currency)
		FROM
			`tabJournal Entry Account` as jea
		LEFT JOIN
			`tabJournal Entry` as je
		ON
			jea.parent = je.name
		WHERE
			(je.clearance_date is null or je.clearance_date='0000-00-00')
		AND
			jea.account = %(account)s
		AND
			(jea.parent like %(txt)s or je.pay_to_recd_from like %(txt)s)
		AND
			je.docstatus = 1
		ORDER BY
			if(locate(%(_txt)s, jea.parent), locate(%(_txt)s, jea.parent), 99999),
			jea.parent
		LIMIT
			%(start)s, %(page_len)s""".format(**{
				'key': searchfield,
			}), {
				'txt': "%%%s%%" % txt,
				'_txt': txt.replace("%", ""),
				'start': start,
				'page_len': page_len,
				'account': account
			}
		)

def sales_invoices_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT
			sip.parent, si.customer, sip.amount, sip.mode_of_payment
		FROM
			`tabSales Invoice Payment` as sip
		LEFT JOIN
			`tabSales Invoice` as si
		ON
			sip.parent = si.name
		WHERE
			(sip.clearance_date is null or sip.clearance_date='0000-00-00')
		AND
			(sip.parent like %(txt)s or si.customer like %(txt)s)
		ORDER BY
			if(locate(%(_txt)s, sip.parent), locate(%(_txt)s, sip.parent), 99999),
			sip.parent
		LIMIT
			%(start)s, %(page_len)s""".format(**{
				'key': searchfield,
			}), {
				'txt': "%%%s%%" % txt,
				'_txt': txt.replace("%", ""),
				'start': start,
				'page_len': page_len
			}
		)