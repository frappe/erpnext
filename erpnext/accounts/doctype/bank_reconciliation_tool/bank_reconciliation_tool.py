# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json

import difflib
import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from six import string_types, iteritems

import frappe
from frappe.core.doctype.data_import.importer import Importer, ImportFile
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt
from frappe.utils.background_jobs import enqueue
from frappe.core.page.background_jobs.background_jobs import get_info
from frappe.utils.scheduler import is_scheduler_inactive
from frappe.utils.xlsxutils import handle_html, ILLEGAL_CHARACTERS_RE

from erpnext import get_company_currency
from erpnext.accounts.utils import get_balance_on
from erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement import get_entries, get_amounts_not_reflected_in_system
from erpnext.accounts.doctype.bank_transaction.bank_transaction import get_paid_amount


class BankReconciliationTool(Document):
	pass

@frappe.whitelist()
def get_bank_transactions(bank_account, from_date = None, to_date = None):
	filters = []
	filters.append(['bank_account', '=', bank_account])
	filters.append(['docstatus', '=', 1])
	filters.append(['unallocated_amount', '>', 0])
	if to_date:
		filters.append(['date', '<=', to_date])
	if from_date:
		filters.append(['date', '>=', from_date])
	transactions = frappe.get_all(
		'Bank Transaction',
		fields = ['date', 'deposit', 'withdrawal', 'currency',
		'description', 'name', 'bank_account', 'company',
		'unallocated_amount', 'reference_number', 'party_type', 'party'],
		filters = filters
	)
	return transactions

@frappe.whitelist()
def get_account_balance(bank_account, till_date):
	account = frappe.db.get_value('Bank Account', bank_account, 'account')
	filters = frappe._dict({
		"account": account,
		"report_date": till_date,
		"include_pos_transactions": 1
	})
	data = get_entries(filters)

	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	amounts_not_reflected_in_system = get_amounts_not_reflected_in_system(filters)

	bank_bal = flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) \
		+ amounts_not_reflected_in_system

	return bank_bal


@frappe.whitelist()
def update_bank_transaction(bank_transaction, reference_number, party_type=None, party=None):
	bank_transaction_name = bank_transaction
	bank_transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	bank_transaction.reference_number = reference_number
	bank_transaction.party_type = party_type
	bank_transaction.party = party
	bank_transaction.save()
	return frappe.db.get_all('Bank Transaction',
		filters={
			'name': bank_transaction_name
		},
		fields=['date', 'deposit', 'withdrawal', 'currency',
			'description', 'name', 'bank_account', 'company',
			'unallocated_amount', 'reference_number',
			 'party_type', 'party'],
	)[0]


@frappe.whitelist()
def create_journal_entry_bts( bank_transaction, reference_number, reference_date, posting_date, entry_type,
	second_account, mode_of_payment=None, party_type=None, party=None):
	bank_transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	company_account = frappe.get_value("Bank Account", bank_transaction.bank_account, "account")
	account_type = frappe.db.get_value("Account", second_account, "account_type")
	if account_type in ["Receivable", "Payable"]:
		if not (party_type and party):
			frappe.throw(_("Party Type and Party is required for Receivable / Payable account {0}").format( second_account))
	accounts = []
	accounts.append({
			"account": second_account,
			"debit_in_account_currency": bank_transaction.deposit
				if  bank_transaction.deposit > 0 
				else 0,
			"credit_in_account_currency":bank_transaction.withdrawal
				if  bank_transaction.withdrawal > 0
				else 0,
			"party_type":party_type,
			"party":party,
		})

	accounts.append({
			"account": company_account,
			"bank_account": bank_transaction.bank_account,
			"debit_in_account_currency": bank_transaction.withdrawal
				if  bank_transaction.withdrawal > 0
				else 0,
			"credit_in_account_currency":bank_transaction.deposit
				if  bank_transaction.deposit > 0
				else 0,
		})

	company = frappe.get_value("Account", company_account, "company")

	journal_entry_dict = {
		"doctype": 'Journal Entry',
		"voucher_type" : entry_type,
		"company" : company,
		"posting_date" : posting_date,
		"cheque_date" : reference_date,
		"cheque_no" : reference_number,
		"mode_of_payment" : mode_of_payment
	}
	journal_entry = frappe.get_doc(journal_entry_dict)
	journal_entry.set("accounts", accounts)
	journal_entry.insert()
	journal_entry.submit()

	if bank_transaction.deposit > 0:
		paid_amount = bank_transaction.deposit
	else:
		paid_amount = bank_transaction.withdrawal

	vouchers = json.dumps([{
		"payment_doctype":"Journal Entry",
		"payment_name":journal_entry.name,
		"amount":paid_amount}])

	return reconcile_vouchers(bank_transaction.name, vouchers)

@frappe.whitelist()
def create_payment_entry_bts( bank_transaction, reference_number, reference_date, party_type, party, posting_date,
	mode_of_payment=None, project=None, cost_center=None):

	bank_transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	paid_amount = bank_transaction.unallocated_amount
	payment_type = "Receive" if bank_transaction.withdrawal > 0 else "Pay"

	company_account = frappe.get_value("Bank Account", bank_transaction.bank_account, "account")
	company = frappe.get_value("Account", company_account, "company")
	payment_entry_dict = {
		"doctype": "Payment Entry",
		"company" : company,
		"payment_type" : payment_type,
		"reference_no" :  reference_number,
		"reference_date" :  reference_date,
		"party_type" :  party_type,
		"party" :  party,
		"posting_date" :  posting_date,
		"paid_amount": paid_amount,
		"received_amount": paid_amount
	}
	payment_entry = frappe.get_doc(payment_entry_dict)

	if mode_of_payment:
		payment_entry.mode_of_payment =  mode_of_payment
	if project:
		payment_entry.project =  project
	if cost_center:
		payment_entry.cost_center =  cost_center
	if payment_type == "Receive":
		payment_entry.paid_to = company_account
	else:
		payment_entry.paid_from = company_account
	payment_entry.insert()
	payment_entry.submit()
	vouchers = json.dumps([{
		"payment_doctype":"Payment Entry",
		"payment_name":payment_entry.name,
		"amount":paid_amount}])
	return reconcile_vouchers(bank_transaction.name, vouchers)

@frappe.whitelist()
def reconcile_vouchers(bank_transaction, vouchers):
	vouchers = json.loads(vouchers)
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	if transaction.unallocated_amount == 0:
		frappe.throw(_("This bank transaction is already fully reconciled"))
	total_amount = 0
	for voucher in vouchers:
		voucher['payment_entry'] = frappe.get_doc(voucher['payment_doctype'], voucher['payment_name'])
		total_amount += get_paid_amount(frappe._dict({
			'payment_document': voucher['payment_doctype'],
			'payment_entry': voucher['payment_name'],
		}), transaction.currency)

	if total_amount > transaction.unallocated_amount:
		frappe.throw(_("The Sum Total of Amounts of All Selected Vouchers Should be Less than the Unallocated Amount of the Bank Transaction"))
	account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")

	for voucher in vouchers:
		gl_entry = frappe.get_doc("GL Entry", dict(account=account, voucher_type=voucher['payment_doctype'], voucher_no=voucher['payment_name']))

		if transaction.withdrawal > 0 and gl_entry.credit > 0:
			frappe.throw(_("The selected payment entry should be linked with a debtor bank transaction"))

		if transaction.deposit > 0 and gl_entry.debit > 0:
			frappe.throw(_("The selected payment entry should be linked with a creditor bank transaction"))

		gl_amount, transaction_amount = (gl_entry.credit, transaction.deposit) if gl_entry.credit > 0 else (gl_entry.debit, transaction.withdrawal)
		allocated_amount = gl_amount if gl_amount <= transaction_amount else transaction_amount

		transaction.append("payment_entries", {
			"payment_document": voucher['payment_entry'].doctype,
			"payment_entry": voucher['payment_entry'].name,
			"allocated_amount": allocated_amount
		})

	transaction.save()
	transaction.update_allocations()
	return frappe.get_doc("Bank Transaction", bank_transaction)

@frappe.whitelist()
def get_linked_payments(bank_transaction, document_types = None):
	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	bank_account = frappe.db.get_values(
		"Bank Account", 
		transaction.bank_account, 
		["account", "company"], 
		as_dict=True)[0]
	(account, company) = (bank_account.account, bank_account.company)
	matching = check_matching(account, company, transaction, document_types)
	return matching

def check_matching(bank_account, company, transaction, document_types):

	subquery = get_subquery(bank_account, company, transaction, document_types)
	query = get_query(subquery)

	if transaction.deposit > 0:
		currency_field = "paid_to_account_currency as currency"  
	else:
		currency_field = "paid_from_account_currency as currency"

	matching_vouchers = frappe.db.sql(query,
		{
			"amount": transaction.unallocated_amount,
			"payment_type" : "Receive" if transaction.deposit > 0 else "Pay",
			"currency_field" : currency_field,
			"reference_no": transaction.reference_number,
			"party_type": transaction.party_type,
			"party": transaction.party,
			"bank_account":  bank_account
		},
		as_dict=True,
		debug=True
	)
	return matching_vouchers

def get_subquery(bank_account, company, transaction, document_types):
	amount_condition = "=" if "exact_match" in document_types else "<="
	account_from_to = "paid_to" if transaction.deposit > 0 else "paid_from"
	subqueries = []

	if "payment_entry" in document_types:
		pe_amount_matching = get_pe_amount_matching_query(amount_condition, account_from_to)
		pe_reference_no_matching = get_pe_reference_no_matching_query(amount_condition, account_from_to)
		pe_party_matching = get_pe_party_matching_query(amount_condition, account_from_to)
		subqueries.extend([pe_amount_matching, pe_party_matching, pe_reference_no_matching])

	if "journal_entry" in document_types:
		je_amount_matching = get_je_amount_matching_query(amount_condition, transaction)
		je_reference_no_matching = get_je_reference_no_matching_query(amount_condition, transaction)
		subqueries.extend([je_amount_matching, je_reference_no_matching])

	if transaction.deposit > 0 and "sales_invoice" in document_types:
		si_amount_matching =  get_si_amount_matching_query(amount_condition)
		si_party_matching =  get_si_party_matching_query(amount_condition)
		subqueries.extend([si_amount_matching, si_party_matching])

	if transaction.withdrawal > 0:
		if "purchase_invoice" in document_types:
			pi_amount_matching = get_pi_amount_matching_query(amount_condition)
			pi_party_matching = get_pi_party_matching_query(amount_condition)
			subqueries.extend([pi_amount_matching, pi_party_matching])

		if "expense_claim" in document_types:
			ec_amount_matching = get_ec_amount_matching_query(bank_account, company, amount_condition)
			ec_party_matching = get_ec_party_matching_query(bank_account, company, amount_condition)
			subqueries.extend([ec_amount_matching, ec_party_matching])

	return " UNION ALL ".join(subqueries)

def get_query(subquery):
	return """SELECT
				COUNT(name) as rank, doctype, name, paid_amount, reference_no, reference_date,
				party, party_type, posting_date, %(currency_field)s  
			FROM (""" + subquery + " ) AS unranked " +  "GROUP BY name " + " ORDER BY rank DESC " 


def get_pe_amount_matching_query(amount_condition, account_from_to):
	return  f"""
	SELECT
		'Payment Entry' as doctype, name, paid_amount, reference_no, reference_date,
		party, party_type, posting_date, %(currency_field)s
	FROM
		`tabPayment Entry`
	WHERE
		paid_amount {amount_condition} %(amount)s
		AND docstatus = 1
		AND payment_type IN (%(payment_type)s, 'Internal Transfer')
		AND ifnull(clearance_date, '') = "" 
		AND {account_from_to} = %(bank_account)s
	"""
	# amount_condition
	# amount
	# payment_type
	# currency_field

def get_pe_reference_no_matching_query(amount_condition, account_from_to): 
	return f"""
	SELECT
		'Payment Entry' as doctype, name, paid_amount, reference_no, reference_date,
		party, party_type, posting_date, %(currency_field)s
	FROM
		`tabPayment Entry`
	WHERE
		paid_amount {amount_condition} %(amount)s 
		AND reference_no = %(reference_no)s 
		AND docstatus = 1 
		AND payment_type IN (%(payment_type)s, 'Internal Transfer') 
		AND ifnull(clearance_date, '') = "" 
		AND {account_from_to} = %(bank_account)s
	"""

	# transaction.reference_number
	# payment_type
	# currency_field

def get_pe_party_matching_query(amount_condition, account_from_to):
	return  f"""
		SELECT
			'Payment Entry' as doctype, name, paid_amount, reference_no, reference_date,
			party, party_type, posting_date, %(currency_field)s
		FROM
			`tabPayment Entry`
		WHERE
			paid_amount {amount_condition} %(amount)s 
			AND party_type = %(party_type)s 
			AND party = %(party)s 
			AND docstatus = 1 
			AND payment_type IN (%(payment_type)s, 'Internal Transfer') 
			AND ifnull(clearance_date, '') = "" 
			AND {account_from_to} = %(bank_account)s
	"""
	# party_type
	# party
	# bank_account

def get_je_amount_matching_query(amount_condition, transaction):
	cr_or_dr = "credit" if transaction.withdrawal > 0 else "debit"
	return f"""

		SELECT
			'Journal Entry' as doctype, je.name, je.posting_date, je.cheque_no as reference_no,
			jea.account_currency as currency, je.pay_to_recd_from as party, je.cheque_date as reference_date,
			jea.{cr_or_dr}_in_account_currency as paid_amount, jea.party_type
		FROM
			`tabJournal Entry Account` as jea
		JOIN
			`tabJournal Entry` as je
		ON
			jea.parent = je.name
		WHERE
			(je.clearance_date is null or je.clearance_date='0000-00-00')
			AND jea.account = %(bank_account)s
			AND jea.{cr_or_dr}_in_account_currency {amount_condition} %(amount)s
			AND je.docstatus = 1
	"""
	# bank_account
	# amount

def get_je_reference_no_matching_query(amount_condition, transaction):
	cr_or_dr = "credit" if transaction.withdrawal > 0 else "debit"
	return f"""

		SELECT
			'Journal Entry' as doctype, je.name, je.posting_date, je.cheque_no as reference_no,
			jea.account_currency as currency, je.pay_to_recd_from as party, je.cheque_date as reference_date,
			jea.{cr_or_dr}_in_account_currency as paid_amount, jea.party_type
		FROM
			`tabJournal Entry Account` as jea
		JOIN
			`tabJournal Entry` as je
		ON
			jea.parent = je.name
		WHERE
			(je.clearance_date is null or je.clearance_date='0000-00-00')
			AND jea.account = %(bank_account)s
			AND jea.{cr_or_dr}_in_account_currency {amount_condition} %(amount)s
			AND je.cheque_no = %(reference_no)s 
			AND je.docstatus = 1
	"""
	# bank_account
	# amount
	# reference_no

def get_si_amount_matching_query(amount_condition):
	return f"""
		SELECT
			'Sales Invoice' as doctype, si.name, si.customer as party,
			si.posting_date, sip.amount as paid_amount, si.currency,
			'' as reference_date, '' as reference_no, 'Customer' as party_type
		FROM
			`tabSales Invoice Payment` as sip
		JOIN
			`tabSales Invoice` as si
		ON
			sip.parent = si.name
		WHERE (sip.clearance_date is null or sip.clearance_date='0000-00-00')
			AND sip.account = %(bank_account)s
			AND sip.amount {amount_condition} %(amount)s
			AND si.docstatus = 1
	"""

	# bank_account
	# amount

def get_si_party_matching_query(amount_condition):
	return f"""
		SELECT
			'Sales Invoice' as doctype, si.name, si.customer as party,
			si.posting_date, sip.amount as paid_amount, si.currency,
			'' as reference_date, '' as reference_no, 'Customer' as party_type
		FROM
			`tabSales Invoice Payment` as sip
		JOIN
			`tabSales Invoice` as si
		ON
			sip.parent = si.name
		WHERE
			(sip.clearance_date is null or sip.clearance_date='0000-00-00')
			AND sip.account = %(bank_account)s
			AND sip.amount {amount_condition} %(amount)s
			AND si.customer = %(party)s 
			AND si.docstatus = 1
	"""

	# bank_account
	# amount
	# party

def get_pi_party_matching_query(amount_condition):
	return f"""
		SELECT 
			'Purchase Invoice' as doctype, name, paid_amount, supplier as party, posting_date, currency ,
			'' as reference_date, '' as reference_no, 'Supplier' as party_type
		FROM 
			`tabPurchase Invoice`
		WHERE
			paid_amount {amount_condition} %(amount)s 
			AND docstatus = 1 
			AND is_paid = 1 
			AND ifnull(clearance_date, '') = "" 
			AND supplier = %(party)s 
			AND cash_bank_account  = %(bank_account)s
	"""
	# amount
	# bank_account

def get_pi_amount_matching_query(amount_condition):
	return f"""
		SELECT 
			'Purchase Invoice' as doctype, name, paid_amount, supplier as party, posting_date, currency ,
			'' as reference_date, '' as reference_no, 'Supplier' as party_type
		FROM 
			`tabPurchase Invoice`
		WHERE
			paid_amount {amount_condition} %(amount)s
			AND docstatus = 1 
			AND is_paid = 1 
			AND ifnull(clearance_date, '') = "" 
			AND cash_bank_account  = %(bank_account)s
	"""
	# amount
	# bank_account
	# party

def get_ec_amount_matching_query(bank_account, company, amount_condition): 
	mode_of_payments = [x["parent"] for x in frappe.db.get_list("Mode of Payment Account",
			filters={"default_account": bank_account}, fields=["parent"])]
	mode_of_payments = '(\'' + '\', \''.join(mode_of_payments) + '\' )'
	company_currency = get_company_currency(company)
	return f"""
		SELECT 'Expense Claim' as doctype, name, total_sanctioned_amount as paid_amount,
				employee as party, posting_date, '{company_currency}' as currency,
				'' as reference_date, '' as reference_no, 'Employee' as party_type
		FROM
			`tabExpense Claim`
		WHERE	
			total_sanctioned_amount {amount_condition} %(amount)s
			AND docstatus = 1 
			AND is_paid = 1 
			AND ifnull(clearance_date, '') = "" 
			AND mode_of_payment in {mode_of_payments}
	"""
	# amount

def get_ec_party_matching_query(bank_account, company, amount_condition): 
	mode_of_payments = [x["parent"] for x in frappe.db.get_list("Mode of Payment Account",
			filters={"default_account": bank_account}, fields=["parent"])]
	mode_of_payments = '(\'' + '\', \''.join(mode_of_payments) + '\' )'
	company_currency = get_company_currency(company)
	return f"""
		SELECT 'Expense Claim' as doctype, name, total_sanctioned_amount as paid_amount,
				employee as party, posting_date, '{company_currency}' as currency,
				'' as reference_date, '' as reference_no, 'Employee' as party_type
		FROM
			`tabExpense Claim`
		WHERE	
			total_sanctioned_amount {amount_condition} %(amount)s 
			AND docstatus = 1 
			AND is_paid = 1 
			AND ifnull(clearance_date, '') = "" 
			AND mode_of_payment in {mode_of_payments} 
			AND employee = %(party)s

	"""	
	# amount
	# party
