# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import difflib
from frappe.utils import flt
from six import iteritems
from erpnext import get_company_currency

@frappe.whitelist()
def reconcile(bank_transaction, payment_doctype, payment_name):
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	payment_entry = frappe.get_doc(payment_doctype, payment_name)

	account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
	gl_entry = frappe.get_doc("GL Entry", dict(account=account, voucher_type=payment_doctype, voucher_no=payment_name))

	if transaction.unallocated_amount == 0:
		frappe.throw(_("This bank transaction is already fully reconciled"))

	if transaction.credit > 0 and gl_entry.credit > 0:
		frappe.throw(_("The selected payment entry should be linked with a debtor bank transaction"))

	if transaction.debit > 0 and gl_entry.debit > 0:
		frappe.throw(_("The selected payment entry should be linked with a creditor bank transaction"))

	add_payment_to_transaction(transaction, payment_entry, gl_entry)

	return 'reconciled'

def add_payment_to_transaction(transaction, payment_entry, gl_entry):
	gl_amount, transaction_amount = (gl_entry.credit, transaction.debit) if gl_entry.credit > 0 else (gl_entry.debit, transaction.credit)
	allocated_amount = gl_amount if gl_amount <= transaction_amount else transaction_amount
	transaction.append("payment_entries", {
		"payment_document": payment_entry.doctype,
		"payment_entry": payment_entry.name,
		"allocated_amount": allocated_amount
	})

	transaction.save()
	transaction.update_allocations()

@frappe.whitelist()
def get_linked_payments(bank_transaction):
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	bank_account = frappe.db.get_values("Bank Account", transaction.bank_account, ["account", "company"], as_dict=True)

	# Get all payment entries with a matching amount
	amount_matching = check_matching_amount(bank_account[0].account, bank_account[0].company, transaction)

	# Get some data from payment entries linked to a corresponding bank transaction
	description_matching = get_matching_descriptions_data(bank_account[0].company, transaction)

	if amount_matching:
		return check_amount_vs_description(amount_matching, description_matching)

	elif description_matching:
		description_matching = filter(lambda x: not x.get('clearance_date'), description_matching)
		if not description_matching:
			return []

		return sorted(list(description_matching), key = lambda x: x["posting_date"], reverse=True)

	else:
		return []

def check_matching_amount(bank_account, company, transaction):
	payments = []
	amount = transaction.credit if transaction.credit > 0 else transaction.debit

	payment_type = "Receive" if transaction.credit > 0 else "Pay"
	account_from_to = "paid_to" if transaction.credit > 0 else "paid_from"
	currency_field = "paid_to_account_currency as currency" if transaction.credit > 0 else "paid_from_account_currency as currency"

	payment_entries = frappe.get_all("Payment Entry", fields=["'Payment Entry' as doctype", "name", "paid_amount", "payment_type", "reference_no", "reference_date",
		"party", "party_type", "posting_date", "{0}".format(currency_field)], filters=[["paid_amount", "like", "{0}%".format(amount)],
		["docstatus", "=", "1"], ["payment_type", "=", [payment_type, "Internal Transfer"]], ["ifnull(clearance_date, '')", "=", ""], ["{0}".format(account_from_to), "=", "{0}".format(bank_account)]])

	if transaction.credit > 0:
		journal_entries = frappe.db.sql("""
			SELECT
				'Journal Entry' as doctype, je.name, je.posting_date, je.cheque_no as reference_no,
				je.pay_to_recd_from as party, je.cheque_date as reference_date, jea.debit_in_account_currency as paid_amount
			FROM
				`tabJournal Entry Account` as jea
			JOIN
				`tabJournal Entry` as je
			ON
				jea.parent = je.name
			WHERE
				(je.clearance_date is null or je.clearance_date='0000-00-00')
			AND
				jea.account = %s
			AND
				jea.debit_in_account_currency like %s
			AND
				je.docstatus = 1
		""", (bank_account, amount), as_dict=True)
	else:
		journal_entries = frappe.db.sql("""
			SELECT
				'Journal Entry' as doctype, je.name, je.posting_date, je.cheque_no as reference_no,
				jea.account_currency as currency, je.pay_to_recd_from as party, je.cheque_date as reference_date,
				jea.credit_in_account_currency as paid_amount
			FROM
				`tabJournal Entry Account` as jea
			JOIN
				`tabJournal Entry` as je
			ON
				jea.parent = je.name
			WHERE
				(je.clearance_date is null or je.clearance_date='0000-00-00')
			AND
				jea.account = %(bank_account)s
			AND
				jea.credit_in_account_currency like %(txt)s
			AND
				je.docstatus = 1
		""", {
			'bank_account': bank_account,
			'txt': '%%%s%%' % amount
		}, as_dict=True)

	if transaction.credit > 0:
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
				sip.account = %s
			AND
				sip.amount like %s
			AND
				si.docstatus = 1
		""", (bank_account, amount), as_dict=True)
	else:
		sales_invoices = []

	if transaction.debit > 0:
		purchase_invoices = frappe.get_all("Purchase Invoice",
			fields = ["'Purchase Invoice' as doctype", "name", "paid_amount", "supplier as party", "posting_date", "currency"],
			filters=[
				["paid_amount", "like", "{0}%".format(amount)],
				["docstatus", "=", "1"],
				["is_paid", "=", "1"],
				["ifnull(clearance_date, '')", "=", ""],
				["cash_bank_account", "=", "{0}".format(bank_account)]
			]
		)

		mode_of_payments = [x["parent"] for x in frappe.db.get_list("Mode of Payment Account",
			filters={"default_account": bank_account}, fields=["parent"])]

		company_currency = get_company_currency(company)

		expense_claims = frappe.get_all("Expense Claim",
			fields=["'Expense Claim' as doctype", "name", "total_sanctioned_amount as paid_amount",
				"employee as party", "posting_date", "'{0}' as currency".format(company_currency)],
			filters=[
				["total_sanctioned_amount", "like", "{0}%".format(amount)],
				["docstatus", "=", "1"],
				["is_paid", "=", "1"],
				["ifnull(clearance_date, '')", "=", ""],
				["mode_of_payment", "in", "{0}".format(tuple(mode_of_payments))]
			]
		)
	else:
		purchase_invoices = expense_claims = []

	for data in [payment_entries, journal_entries, sales_invoices, purchase_invoices, expense_claims]:
		if data:
			payments.extend(data)

	return payments

def get_matching_descriptions_data(company, transaction):
	if not transaction.description :
		return []

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
	company_currency = get_company_currency(company)
	for key, value in iteritems(links):
		if key == "Payment Entry":
			data.extend(frappe.get_all("Payment Entry", filters=[["name", "in", value]],
				fields=["'Payment Entry' as doctype", "posting_date", "party", "reference_no",
					"reference_date", "paid_amount", "paid_to_account_currency as currency", "clearance_date"]))
		if key == "Journal Entry":
			journal_entries = frappe.get_all("Journal Entry", filters=[["name", "in", value]],
				fields=["name", "'Journal Entry' as doctype", "posting_date",
					"pay_to_recd_from as party", "cheque_no as reference_no", "cheque_date as reference_date",
					"total_credit as paid_amount", "clearance_date"])
			for journal_entry in journal_entries:
				journal_entry_accounts = frappe.get_all("Journal Entry Account", filters={"parenttype": journal_entry["doctype"], "parent": journal_entry["name"]}, fields=["account_currency"])
				journal_entry["currency"] = journal_entry_accounts[0]["account_currency"] if journal_entry_accounts else company_currency
			data.extend(journal_entries)
		if key == "Sales Invoice":
			data.extend(frappe.get_all("Sales Invoice", filters=[["name", "in", value]], fields=["'Sales Invoice' as doctype", "posting_date", "customer_name as party", "paid_amount", "currency"]))
		if key == "Purchase Invoice":
			data.extend(frappe.get_all("Purchase Invoice", filters=[["name", "in", value]], fields=["'Purchase Invoice' as doctype", "posting_date", "supplier_name as party", "paid_amount", "currency"]))
		if key == "Expense Claim":
			expense_claims = frappe.get_all("Expense Claim", filters=[["name", "in", value]], fields=["'Expense Claim' as doctype", "posting_date", "employee_name as party", "total_amount_reimbursed as paid_amount"])
			data.extend([dict(x,**{"currency": company_currency}) for x in expense_claims])

	return data

def check_amount_vs_description(amount_matching, description_matching):
	result = []

	if description_matching:
		for am_match in amount_matching:
			for des_match in description_matching:
				if des_match.get("clearance_date"):
					continue

				if am_match["party"] == des_match["party"]:
					if am_match not in result:
						result.append(am_match)
						continue

				if "reference_no" in am_match and "reference_no" in des_match:
					if difflib.SequenceMatcher(lambda x: x == " ", am_match["reference_no"], des_match["reference_no"]).ratio() > 70:
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

def payment_entry_query(doctype, txt, searchfield, start, page_len, filters):
	account = frappe.db.get_value("Bank Account", filters.get("bank_account"), "account")
	if not account:
		return

	return frappe.db.sql("""
		SELECT
			name, party, paid_amount, received_amount, reference_no
		FROM
			`tabPayment Entry`
		WHERE
			(clearance_date is null or clearance_date='0000-00-00')
			AND (paid_from = %(account)s or paid_to = %(account)s)
			AND (name like %(txt)s or party like %(txt)s)
			AND docstatus = 1
		ORDER BY
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999), name
		LIMIT
			%(start)s, %(page_len)s""",
		{
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'account': account
		}
	)

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
			%(start)s, %(page_len)s""",
		{
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
			%(start)s, %(page_len)s""",
		{
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		}
	)