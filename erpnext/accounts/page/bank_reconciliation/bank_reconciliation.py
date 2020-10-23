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

# The Bank Reconciliation process has clearly gone through a series of developments over
# a significant span of time, occasionally with only a portion of the system being
# updated at one time. These comments are intended to marshal what the components of
# that system are and what the process is, as a sort of central checklist to guide
# future development of this bookkeeping-critical facility.

# As of ERPNext V13, 2020 Oct, it appears that ideally Bank Reconciliation works as
# follows:
# (A) Only accounting documents that directly yield General Ledger entries with Account
#     field equal to the Account of the Bank Account being reconciled are actually used
#     at the database level to reconcile Bank Transactions.
# (B) The reconciliation mechanism is to set a field called "Clearance Date" in those
#     accounting documents to show that they have been reconciled against a bank
#     transaction, and to create a Bank Transaction Payment entry in the Payments table
#     of the Bank Transaction to list the accounting documents against which it has
#     been reconciled.
# (C) The only such accounting document types at the moment are: (1) Payment Entry;
#     (2) Journal Entry Account records (entries in the Accounts field of a
#     Journal Entry); (3) "cash" or "pos" Purchase Invoice documents - ones that have
#     a value for Cash/Bank Account and corresponding value for Paid Amount (note that
#     these denote just a single payment in full); and (4) Sales Invoice Payment
#     records (entries in the Sales Invoice Payment table of a Sales Invoice).
# (D) In the case of Journal Entry Account records, a Reconciled With field is also
#     set to the Bank Transaction entry to allow easy user traversal back to the
#     associated Bank Transaction. In the future, such backreferences could be expanded
#     to the other document types used in direct reconciliation.
# (E) For convenience, the user is also allowed to "reconcile" against a
#     "non-pos" Purchase Invoice, Sales Invoice, Expense Claim, or Journal Entry.
#     In each of these cases, the documents do not directly correspond to GL Entries
#     hitting the bank Account, but they all have associated entries of doctypes from
#     item (C) that do.
#     So "reconciling" against one of these document types is simply a shorthand for
#     (simultaneously) reconciling all of the associated documents of types from (C)
#     that relate to the bank Account being reconciled.

# Here is a list of pieces of the Bank Reconciliation system, all of which have
# been hopefully harmonized with the above view of reconciliation, and which should
# be maintained through future updates.
# (1) The document types listed in item (C) above. They must have the Clearance Date
#     field used to record reconciliations; the other document types do not have to
#     have this field.
# (2) The (single) Bank Clearance doc which implements the "manual" mode of
#     reconciliation, providing a form in which individual documents from (1) can
#     have their Clearance Date fields set without any associated Bank Transaction
#     records to be reconciled against. (In this way, it is possible to perform a
#     bank reconciliation without importing any Bank Transactions.)
# (2) The Bank Transaction doctype, which stores the records from a bank that need to
#     be reconciled; their Bank Transaction Payment records (in the Payments table)
#     must link to the doctypes from (1).
# (4) The Bank Clearance Summary report, which shows all of the documents from (1)
#     associated with a particular Bank Account against which it might reconcile,
#     and whether (and on what date) they have cleared.
# (5) The Bank Reconciliation Statement report, which shows the official bank balance
#     which should correspond to the accounting records in ERPNext based on what
#     documents have been reconciled or not.
# (6) The Bank Reconciliation page, defined in this directory, which provides the main
#     user interface to upload bank transactions and reconcile them with payment
#     documents in ERPNext of all types in both items (C) and (E) above.

@frappe.whitelist()
def reconcile(bank_transaction, payment_doctype, payment_name):
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	payment_entry = frappe.get_doc(payment_doctype, payment_name)
	if hasattr(payment_entry, 'clearance_date') and payment_entry.clearance_date:
		frappe.throw(_("This payment document is already cleared"))

	# As per the above discussion, certain doctypes are cleared directly:
	if payment_doctype in ["Journal Entry Account", "Payment Entry", "Sales Invoice Payment"]:
		return direct_reconcile(transaction, payment_doctype, payment_entry)

	account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
	if payment_doctype == "Purchase Invoice" and payment_entry.cash_bank_account == account:
		return direct_reconcile(transaction, "Purchase Invoice", payment_entry, account)

	# No other doctypes are cleared directly
	n_recd = 0
	n_tried = 0

	if payment_doctype == "Journal Entry":
		for jea in payment_entry.accounts:
			if jea.account == account and not jea.clearance_date:
				n_tried += 1
				if direct_reconcile(transaction,
						"Journal Entry Account", jea, account):
					n_recd += 1

	elif payment_doctype == "Sales Invoice" and payment_entry.payments:
		for sip in payment_entry.payments:
			if sip.account == account and not sip.clearance_date:
				n_tried += 1
				if direct_reconcile(transaction,
						"Sales Invoice Payment", sip,
						account) == 'reconciled':
					n_recd += 1

	# Everything else is just reconciled in terms of associated Payment Entry
	# documents:
	else:
		pe_list = frappe.db.get_list("Payment Entry",
			filters=dict(reference_name=payment_entry.name))
		for result in pe_list:
			pe = frappe.get_doc("Payment Entry", result["name"])
			if not pe.clearance_date and (pe.paid_to == account or pe.paid_from == account):
				n_tried += 1
				if direct_reconcile(transaction, "Payment Entry",
						pe, account) == 'reconciled':
					n_recd += 1

	return 'reconciled' if n_recd > 0 and n_recd == n_tried else 'failure'

def direct_reconcile(transaction, payment_doctype, payment_entry, account = None):
	if transaction.unallocated_amount == 0:
		frappe.throw(_("This bank transaction is already fully reconciled"))

	account = account or frappe.db.get_value("Bank Account", transaction.bank_account, "account")

	gl_entry = None
	gl_count = 0
	if payment_doctype == "Journal Entry Account":
		gl_entry = frappe.get_doc("GL Entry", dict(account=account,
			voucher_type="Journal Entry",
			voucher_no=payment_entry.parent,
			credit_in_account_currency=payment_entry.credit_in_account_currency,
			debit_in_account_currency=payment_entry.debit_in_account_currency
		))
		# There could still be multiple matches (maybe equal payments
		# to two different cost centers) but since we only use the
		# credit and debit amounts from the GL Entry and we don't
		# modify the GL Entry in any way, it won't matter if it is the
		# "wrong" one.
	else:
		# On the other hand, if there are multiple GL matches in other
		# circumstances, we had best be cautious:
		selector = dict(account=account, voucher_type=payment_doctype,
				voucher_no=payment_entry.name)
		gl_count = frappe.db.count("GL Entry", selector)
		if gl_count == 1:
			gl_entry = frappe.get_doc("GL Entry", selector)
		elif gl_count == 0 and payment_doctype == "Sales Invoice Payment":
			selector['voucher_type'] = "Sales Invoice"
			selector['voucher_no'] = payment_entry.parent
			gl_count = frappe.db.count("GL Entry", selector)
			if gl_count == 1:
				gl_entry = frappe.get_doc("GL Entry", selector)
	if not gl_entry:
		frappe.throw(_("There are {0} General Ledger entries associated with {1}: {2}").format(gl_count, payment_doctype, payment_entry.name))

	payment_amount = gl_entry.credit_in_account_currency + gl_entry.debit_in_account_currency
	if payment_amount > transaction.unallocated_amount:
		frappe.throw(_("The paid amount of {0} {1} is greater than the Bank Transaction's unallocated amount").format(payment_doctype, payment_entry.name))

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
	amount = transaction.unallocated_amount
	company_currency = get_company_currency(company)

	payment_type = "Receive" if transaction.credit > 0 else "Pay"
	account_from_to = "paid_to" if transaction.credit > 0 else "paid_from"
	currency_field = "paid_to_account_currency" if transaction.credit > 0 else "paid_from_account_currency"
	pymt_amount_field = "received_amount as pymt_amount" if transaction.credit > 0 else "paid_amount as pymt_amount"
	compare_amount = "received_amount" if transaction.credit > 0 else "paid_amount"
	currency_filter = []
	if transaction.currency == company_currency:
		compare_amount = "base_received_amount" if transaction.credit > 0 else "base_paid_amount"
	else:
		currency_filter = [[currency_field, "=",
			'"' + transaction.currency + '"'
		]]

	payment_entries = frappe.get_all("Payment Entry",
		fields=["'Payment Entry' as doctype", "name", "name as display_name",
			pymt_amount_field, "payment_type", "reference_no",
			"reference_date", "party", "party_type", "posting_date",
			currency_field + " as currency"
		], filters=currency_filter + [
			[compare_amount, "like", "{0}%".format(amount)],
			["docstatus", "=", "1"],
			["payment_type", "=", [payment_type, "Internal Transfer"]],
			["ifnull(clearance_date, '')", "=", ""],
			[account_from_to, "=", bank_account]
		])

	jea_side = "debit" if transaction.credit > 0 else "credit"
	compare_amount = "jea." + jea_side;
	currency_condition = ""
	if company_currency != transaction.currency:
		compare_amount += "_in_account_currency"
		currency_condition = 'AND jea.account_currency = "' + transaction.currency + '"'
	# This query produces individual Journal Entry Account lines that match the
	# desired total.
	journal_entry_accounts = frappe.db.sql(f"""
		SELECT
			'Journal Entry Account' as doctype, jea.name, je.name as display_name, je.posting_date, je.cheque_no as reference_no,
			jea.account_currency as currency, je.pay_to_recd_from as party, je.cheque_date as reference_date,
			jea.{jea_side}_in_account_currency as pymt_amount
		FROM
			`tabJournal Entry Account` as jea
		JOIN
			`tabJournal Entry` as je
		ON
			jea.parent = je.name
		WHERE
			(jea.clearance_date is null or jea.clearance_date='0000-00-00')
		AND
			jea.account = %(bank_account)s
		AND
			{compare_amount} like %(txt)s {currency_condition}
		AND
			je.docstatus = 1
	""", {
		'bank_account': bank_account,
		'txt': '%%%s%%' % amount
	}, as_dict=True)

	# However, if the transaction happens to be in company currency, we can also
	# look for Journal Entry documents where the total of all of the relevant
	# account lines equals the desired amount:
	journal_entries = []
	if transaction.currency == company_currency:
		signed_amount = amount if transaction.credit > 0 else -amount
		journal_entries = frappe.db.sql("""
			SELECT
				"Journal Entry" as doctype, je.name,
				je.name as display_name, je.posting_date,
				je.cheque_no as reference_no,
				je.pay_to_recd_from as party, je.cheque_date,
				%(amount)s as pymt_amount
			FROM
				`tabJournal Entry Account` as jea
			JOIN
				`tabJournal Entry` as je
			ON
				jea.parent = je.name
			WHERE
				(jea.clearance_date is null or jea.clearance_date='0000-00-00')
			AND
				jea.account = %(bank_account)s
			AND
				je.docstatus = 1
			GROUP BY
				je.name
			HAVING
				count(*) > 1
			AND
				sum(jea.debit)-sum(jea.credit) = %(signed_amount)s
			""", dict(amount=amount, signed_amount=signed_amount,
			bank_account=bank_account, company_currency=company_currency),
			as_dict=True)
		for je in journal_entries:
			je.currency = company_currency
			doc = frappe.get_doc("Journal Entry", je.name)
			je.subentries = []
			for jea in doc.accounts:
				if jea.clearance_date or jea.account != bank_account:
					continue
				sub = jea.as_dict();
				sub.update(dict(display_name=jea.name,
					posting_date=doc.posting_date,
					reference_no=doc.cheque_no,
					currency=company_currency,
					reference_date=doc.cheque_date,
					party=doc.pay_to_recd_from,
					pymt_amount=jea.debit-jea.credit
				))
				if transaction.debit > 0:
					sub['pymt_amount'] = jea.credit - jea.debit
				je.subentries.append(sub)

	if transaction.credit > 0:
		compare_amount = "sip.base_amount"
		currency_condition = ""
		if (company_currency != transaction.currency):
			compare_amount = "sip.amount"
			currency_condition = 'AND si.currency = "' + transaction.currency + '"'
		query = f"""SELECT
				'Sales Invoice Payment' as doctype, sip.name,
				si.name as display_name, si.customer as party,
				si.posting_date, sip.amount as pymt_amount,
				si.currency
			FROM
				`tabSales Invoice Payment` as sip
			JOIN
				`tabSales Invoice` as si
			ON
				sip.parent = si.name
			WHERE
				(sip.clearance_date is null or sip.clearance_date='0000-00-00')
			AND
				sip.account = '{bank_account}'
			AND
				{compare_amount} like {amount} {currency_condition}
			AND
				si.docstatus = 1
		"""
		sales_invoices = frappe.db.sql(query, dict(), as_dict=True)
	else:
		sales_invoices = []

	if transaction.debit > 0:
		compare_amount = "base_paid_amount"
		currency_condition = []
		if (company_currency != transaction.currency):
			compare_amount = "paid_amount"
			currency_condition = [["currency", "=", '"' + transaction.currency + '"']]

		purchase_invoices = frappe.get_all("Purchase Invoice",
			fields = ["'Purchase Invoice' as doctype", "name",
				"name as display_name", "paid_amount as pymt_amount",
				"supplier as party", "posting_date", "currency"],
			filters=currency_condition + [
				[compare_amount, "like", "{0}%".format(amount)],
				["docstatus", "=", "1"],
				["is_paid", "=", "1"],
				["ifnull(clearance_date, '')", "=", ""],
				["cash_bank_account", "=", "{0}".format(bank_account)]
			]
		)

		expense_claims = []
		if transaction.currency == company_currency:
			mode_of_payments = [x["parent"] for x in frappe.db.get_list("Mode of Payment Account",
				filters={"default_account": bank_account}, fields=["parent"])]

			expense_claims = frappe.get_all("Expense Claim",
				fields=["'Expense Claim' as doctype", "name", "name as display_name", "total_sanctioned_amount as pymt_amount",
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

	for data in [payment_entries, journal_entry_accounts, journal_entries, sales_invoices, purchase_invoices, expense_claims]:
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
					"reference_date", "paid_amount as pymt_amount", "paid_to_account_currency as currency", "clearance_date"]))
		if key == "Journal Entry Account":
			journal_entry_accounts = frappe.get_all("Journal Entry Account", filters=[["name", "in", value]],
				fields=["name", "'Journal Entry Account' as doctype", "parent", "debit", "credit", "account_currency as currency", "clearance_date"])
			for jea in journal_entry_accounts:
				jea["pymt_amount"] = jea["debit"] + jea["credit"]
				journal_entry = frappe.get_doc("Journal Entry", jea["parent"])
				jea["posting_date"] = journal_entry.posting_date;
				jea["party"] = journal_entry.pay_to_recd_from;
				jea["reference_no"] = journal_entry.cheque_no;
				jea["reference_date"] = journal_entry.cheque_date;
			data.extend(journal_entry_accounts)
		if key == "Sales Invoice":
			data.extend(frappe.get_all("Sales Invoice",
				filters=[["name", "in", value]],
				fields=[
					"'Sales Invoice' as doctype",
					"posting_date",
					"customer_name as party",
					"paid_amount as pymt_amount",
					"currency"
				]
			))
		if key == "Purchase Invoice":
			data.extend(frappe.get_all("Purchase Invoice",
				filters=[["name", "in", value]],
				fields=[
					"'Purchase Invoice' as doctype",
					"posting_date",
					"supplier_name as party",
					"paid_amount as pymt_amount",
					"currency"
				]
			))
		if key == "Expense Claim":
			expense_claims = frappe.get_all("Expense Claim",
				filters=[["name", "in", value]],
				fields=["'Expense Claim' as doctype",
					"posting_date",
					"employee_name as party",
					"total_amount_reimbursed as pymt_amount"
				]
			)
			data.extend([dict(x,currency=company_currency) for x in expense_claims])

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
					# Sequence Matcher does not handle None as input
					am_reference = am_match["reference_no"] or ""
					des_reference = des_match["reference_no"] or ""

					if difflib.SequenceMatcher(lambda x: x == " ", am_reference, des_reference).ratio() > 70:
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
		reference_payment_list = frappe.get_all("Payment Entry", fields=["name", "paid_amount as pymt_amount", "payment_type", "reference_no", "reference_date",
			"party", "party_type", "posting_date", "paid_to_account_currency"], filters=[["name", "in", payments]])

		return sorted(reference_payment_list, key=lambda x: payment_by_ratio[x["name"]])

	else:
		return []

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
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

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
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
			(jea.clearance_date is null or jea.clearance_date='0000-00-00')
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

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def sales_invoices_query(doctype, txt, searchfield, start, page_len, filters):
	account = frappe.db.get_value("Bank Account", filters.get("bank_account"), "account")
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
		AND
			sip.account = %(account)s
		ORDER BY
			if(locate(%(_txt)s, sip.parent), locate(%(_txt)s, sip.parent), 99999),
			sip.parent
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
