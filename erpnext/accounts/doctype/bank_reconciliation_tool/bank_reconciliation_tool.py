# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Sum
from frappe.utils import cint, create_batch, flt

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.bank_transaction.bank_transaction import get_total_allocated_amount
from erpnext.accounts.party import get_party_account
from erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement import (
	get_amounts_not_reflected_in_system,
	get_entries,
)
from erpnext.accounts.utils import get_account_currency, get_balance_on
from erpnext.setup.utils import get_exchange_rate


class BankReconciliationTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_currency: DF.Link | None
		account_opening_balance: DF.Currency
		bank_account: DF.Link | None
		bank_statement_closing_balance: DF.Currency
		bank_statement_from_date: DF.Date | None
		bank_statement_to_date: DF.Date | None
		company: DF.Link | None
		filter_by_reference_date: DF.Check
		from_reference_date: DF.Date | None
		to_reference_date: DF.Date | None
	# end: auto-generated types

	pass


@frappe.whitelist()
def get_bank_transactions(bank_account, from_date=None, to_date=None):
	# returns bank transactions for a bank account
	filters = []
	filters.append(["bank_account", "=", bank_account])
	filters.append(["docstatus", "=", 1])
	filters.append(["unallocated_amount", ">", 0.0])
	if to_date:
		filters.append(["date", "<=", to_date])
	if from_date:
		filters.append(["date", ">=", from_date])
	transactions = frappe.get_all(
		"Bank Transaction",
		fields=[
			"date",
			"deposit",
			"withdrawal",
			"currency",
			"description",
			"name",
			"bank_account",
			"company",
			"unallocated_amount",
			"reference_number",
			"party_type",
			"party",
		],
		filters=filters,
		order_by="date",
	)
	return transactions


@frappe.whitelist()
def get_account_balance(bank_account, till_date, company):
	# returns account balance till the specified date
	account = frappe.db.get_value("Bank Account", bank_account, "account")
	filters = frappe._dict(
		{
			"account": account,
			"report_date": till_date,
			"include_pos_transactions": 1,
			"company": company,
		}
	)
	data = get_entries(filters)

	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0.0, 0.0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	amounts_not_reflected_in_system = get_amounts_not_reflected_in_system(filters)

	return flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) + amounts_not_reflected_in_system


@frappe.whitelist()
def update_bank_transaction(bank_transaction_name, reference_number, party_type=None, party=None):
	# updates bank transaction based on the new parameters provided by the user from Vouchers
	bank_transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	bank_transaction.reference_number = reference_number
	bank_transaction.party_type = party_type
	bank_transaction.party = party
	bank_transaction.save()
	return frappe.db.get_all(
		"Bank Transaction",
		filters={"name": bank_transaction_name},
		fields=[
			"date",
			"deposit",
			"withdrawal",
			"currency",
			"description",
			"name",
			"bank_account",
			"company",
			"unallocated_amount",
			"reference_number",
			"party_type",
			"party",
		],
	)[0]


@frappe.whitelist()
def create_journal_entry_bts(
	bank_transaction_name,
	reference_number=None,
	reference_date=None,
	posting_date=None,
	entry_type=None,
	second_account=None,
	mode_of_payment=None,
	party_type=None,
	party=None,
	allow_edit=None,
):
	# Create a new journal entry based on the bank transaction
	bank_transaction = frappe.db.get_values(
		"Bank Transaction",
		bank_transaction_name,
		fieldname=["name", "deposit", "withdrawal", "bank_account", "currency"],
		as_dict=True,
	)[0]
	company_account = frappe.get_value("Bank Account", bank_transaction.bank_account, "account")
	account_type = frappe.db.get_value("Account", second_account, "account_type")
	if account_type in ["Receivable", "Payable"]:
		if not (party_type and party):
			frappe.throw(
				_("Party Type and Party is required for Receivable / Payable account {0}").format(
					second_account
				)
			)

	company = frappe.get_value("Account", company_account, "company")
	company_default_currency = frappe.get_cached_value("Company", company, "default_currency")
	company_account_currency = frappe.get_cached_value("Account", company_account, "account_currency")
	second_account_currency = frappe.get_cached_value("Account", second_account, "account_currency")

	# determine if multi-currency Journal or not
	is_multi_currency = (
		True
		if company_default_currency != company_account_currency
		or company_default_currency != second_account_currency
		or company_default_currency != bank_transaction.currency
		else False
	)

	accounts = []
	second_account_dict = {
		"account": second_account,
		"account_currency": second_account_currency,
		"credit_in_account_currency": bank_transaction.deposit,
		"debit_in_account_currency": bank_transaction.withdrawal,
		"party_type": party_type,
		"party": party,
		"cost_center": get_default_cost_center(company),
	}

	company_account_dict = {
		"account": company_account,
		"account_currency": company_account_currency,
		"bank_account": bank_transaction.bank_account,
		"credit_in_account_currency": bank_transaction.withdrawal,
		"debit_in_account_currency": bank_transaction.deposit,
		"cost_center": get_default_cost_center(company),
	}

	# convert transaction amount to company currency
	if is_multi_currency:
		exc_rate = get_exchange_rate(bank_transaction.currency, company_default_currency, posting_date)
		withdrawal_in_company_currency = flt(exc_rate * abs(bank_transaction.withdrawal))
		deposit_in_company_currency = flt(exc_rate * abs(bank_transaction.deposit))
	else:
		withdrawal_in_company_currency = bank_transaction.withdrawal
		deposit_in_company_currency = bank_transaction.deposit

	# if second account is of foreign currency, convert and set debit and credit fields.
	if second_account_currency != company_default_currency:
		exc_rate = get_exchange_rate(second_account_currency, company_default_currency, posting_date)
		second_account_dict.update(
			{
				"exchange_rate": exc_rate,
				"credit": deposit_in_company_currency,
				"debit": withdrawal_in_company_currency,
				"credit_in_account_currency": flt(deposit_in_company_currency / exc_rate) or 0,
				"debit_in_account_currency": flt(withdrawal_in_company_currency / exc_rate) or 0,
			}
		)
	else:
		second_account_dict.update(
			{
				"exchange_rate": 1,
				"credit": deposit_in_company_currency,
				"debit": withdrawal_in_company_currency,
				"credit_in_account_currency": deposit_in_company_currency,
				"debit_in_account_currency": withdrawal_in_company_currency,
			}
		)

	# if company account is of foreign currency, convert and set debit and credit fields.
	if company_account_currency != company_default_currency:
		exc_rate = get_exchange_rate(company_account_currency, company_default_currency, posting_date)
		company_account_dict.update(
			{
				"exchange_rate": exc_rate,
				"credit": withdrawal_in_company_currency,
				"debit": deposit_in_company_currency,
			}
		)
	else:
		company_account_dict.update(
			{
				"exchange_rate": 1,
				"credit": withdrawal_in_company_currency,
				"debit": deposit_in_company_currency,
				"credit_in_account_currency": withdrawal_in_company_currency,
				"debit_in_account_currency": deposit_in_company_currency,
			}
		)

	accounts.append(second_account_dict)
	accounts.append(company_account_dict)

	journal_entry_dict = {
		"voucher_type": entry_type,
		"company": company,
		"posting_date": posting_date,
		"cheque_date": reference_date,
		"cheque_no": reference_number,
		"mode_of_payment": mode_of_payment,
	}
	if is_multi_currency:
		journal_entry_dict.update({"multi_currency": True})

	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.update(journal_entry_dict)
	journal_entry.set("accounts", accounts)

	if allow_edit:
		return journal_entry

	journal_entry.insert()
	journal_entry.submit()

	if bank_transaction.deposit > 0.0:
		paid_amount = bank_transaction.deposit
	else:
		paid_amount = bank_transaction.withdrawal

	vouchers = json.dumps(
		[
			{
				"payment_doctype": "Journal Entry",
				"payment_name": journal_entry.name,
				"amount": paid_amount,
			}
		]
	)

	return reconcile_vouchers(bank_transaction_name, vouchers)


@frappe.whitelist()
def create_payment_entry_bts(
	bank_transaction_name,
	reference_number=None,
	reference_date=None,
	party_type=None,
	party=None,
	posting_date=None,
	mode_of_payment=None,
	project=None,
	cost_center=None,
	allow_edit=None,
):
	# Create a new payment entry based on the bank transaction
	bank_transaction = frappe.db.get_values(
		"Bank Transaction",
		bank_transaction_name,
		fieldname=["name", "unallocated_amount", "deposit", "bank_account", "currency"],
		as_dict=True,
	)[0]

	payment_type = "Receive" if bank_transaction.deposit > 0.0 else "Pay"

	bank_account = frappe.get_cached_value("Bank Account", bank_transaction.bank_account, "account")
	company = frappe.get_cached_value("Account", bank_account, "company")
	party_account = get_party_account(party_type, party, company)

	bank_currency = bank_transaction.currency
	party_currency = frappe.get_cached_value("Account", party_account, "account_currency")

	exc_rate = get_exchange_rate(bank_currency, party_currency, posting_date)

	amt_in_bank_acc_currency = bank_transaction.unallocated_amount
	amount_in_party_currency = bank_transaction.unallocated_amount * exc_rate

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = payment_type
	pe.company = company
	pe.reference_no = reference_number
	pe.reference_date = reference_date
	pe.party_type = party_type
	pe.party = party
	pe.posting_date = posting_date
	pe.paid_from = party_account if payment_type == "Receive" else bank_account
	pe.paid_to = party_account if payment_type == "Pay" else bank_account
	pe.paid_from_account_currency = party_currency if payment_type == "Receive" else bank_currency
	pe.paid_to_account_currency = party_currency if payment_type == "Pay" else bank_currency
	pe.paid_amount = amount_in_party_currency if payment_type == "Receive" else amt_in_bank_acc_currency
	pe.received_amount = amount_in_party_currency if payment_type == "Pay" else amt_in_bank_acc_currency
	pe.mode_of_payment = mode_of_payment
	pe.project = project
	pe.cost_center = cost_center

	pe.validate()

	if allow_edit:
		return pe

	pe.insert()
	pe.submit()

	vouchers = json.dumps(
		[
			{
				"payment_doctype": "Payment Entry",
				"payment_name": pe.name,
				"amount": amt_in_bank_acc_currency,
			}
		]
	)
	return reconcile_vouchers(bank_transaction_name, vouchers)


@frappe.whitelist()
def auto_reconcile_vouchers(
	bank_account,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
):
	bank_transactions = get_bank_transactions(bank_account)

	if len(bank_transactions) > 10:
		for bank_transaction_batch in create_batch(bank_transactions, 1000):
			frappe.enqueue(
				method="erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.start_auto_reconcile",
				queue="long",
				bank_transactions=bank_transaction_batch,
				from_date=from_date,
				to_date=to_date,
				filter_by_reference_date=filter_by_reference_date,
				from_reference_date=from_reference_date,
				to_reference_date=to_reference_date,
			)
		frappe.msgprint(_("Auto Reconciliation has started in the background"))
	else:
		start_auto_reconcile(
			bank_transactions,
			from_date,
			to_date,
			filter_by_reference_date,
			from_reference_date,
			to_reference_date,
		)


def start_auto_reconcile(
	bank_transactions, from_date, to_date, filter_by_reference_date, from_reference_date, to_reference_date
):
	frappe.flags.auto_reconcile_vouchers = True

	reconciled, partially_reconciled = set(), set()
	for transaction in bank_transactions:
		linked_payments = get_linked_payments(
			transaction.name,
			["payment_entry", "journal_entry", "sales_invoice"],
			from_date,
			to_date,
			filter_by_reference_date,
			from_reference_date,
			to_reference_date,
		)

		if not linked_payments:
			continue

		vouchers = list(
			map(
				lambda entry: {
					"payment_doctype": entry.get("doctype"),
					"payment_name": entry.get("name"),
					"amount": entry.get("paid_amount"),
				},
				linked_payments,
			)
		)

		updated_transaction = reconcile_vouchers(transaction.name, json.dumps(vouchers))

		if updated_transaction.status == "Reconciled":
			reconciled.add(updated_transaction.name)
		elif flt(transaction.unallocated_amount) != flt(updated_transaction.unallocated_amount):
			# Partially reconciled (status = Unreconciled & unallocated amount changed)
			partially_reconciled.add(updated_transaction.name)

	alert_message, indicator = get_auto_reconcile_message(partially_reconciled, reconciled)
	frappe.msgprint(title=_("Auto Reconciliation"), msg=alert_message, indicator=indicator)

	frappe.flags.auto_reconcile_vouchers = False


def get_auto_reconcile_message(partially_reconciled, reconciled):
	"""Returns alert message and indicator for auto reconciliation depending on result state."""
	alert_message, indicator = "", "blue"
	if not partially_reconciled and not reconciled:
		alert_message = _("No matches occurred via auto reconciliation")
		return alert_message, indicator

	indicator = "green"
	if reconciled:
		alert_message += _("{0} Transaction(s) Reconciled").format(len(reconciled))
		alert_message += "<br>"

	if partially_reconciled:
		alert_message += _("{0} {1} Partially Reconciled").format(
			len(partially_reconciled),
			_("Transactions") if len(partially_reconciled) > 1 else _("Transaction"),
		)

	return alert_message, indicator


@frappe.whitelist()
def reconcile_vouchers(bank_transaction_name, vouchers):
	# updated clear date of all the vouchers based on the bank transaction
	vouchers = json.loads(vouchers)
	transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	transaction.add_payment_entries(vouchers)
	transaction.validate_duplicate_references()
	transaction.allocate_payment_entries()
	transaction.update_allocated_amount()
	transaction.set_status()
	transaction.save()

	return transaction


@frappe.whitelist()
def get_linked_payments(
	bank_transaction_name,
	document_types=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
):
	# get all matching payments for a bank transaction
	transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	bank_account = frappe.db.get_values(
		"Bank Account", transaction.bank_account, ["account", "company"], as_dict=True
	)[0]
	(gl_account, company) = (bank_account.account, bank_account.company)
	matching = check_matching(
		gl_account,
		company,
		transaction,
		document_types,
		from_date,
		to_date,
		filter_by_reference_date,
		from_reference_date,
		to_reference_date,
	)
	return subtract_allocations(gl_account, matching)


def subtract_allocations(gl_account, vouchers):
	"Look up & subtract any existing Bank Transaction allocations"
	copied = []

	voucher_docs = [(voucher.get("doctype"), voucher.get("name")) for voucher in vouchers]
	voucher_allocated_amounts = get_total_allocated_amount(voucher_docs)

	for voucher in vouchers:
		if amount := get_allocated_amount(voucher_allocated_amounts, voucher, gl_account):
			voucher["paid_amount"] -= amount

		copied.append(voucher)
	return copied


def get_allocated_amount(voucher_allocated_amounts, voucher, gl_account):
	if not (voucher_details := voucher_allocated_amounts.get((voucher.get("doctype"), voucher.get("name")))):
		return

	if not (row := voucher_details.get(gl_account)):
		return

	return row.get("total")


def check_matching(
	bank_account,
	company,
	transaction,
	document_types=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
):
	exact_match = True if "exact_match" in document_types else False

	common_filters = frappe._dict(
		{
			"amount": transaction.unallocated_amount,
			"payment_type": "Receive" if transaction.deposit > 0.0 else "Pay",
			"reference_no": transaction.reference_number,
			"party_type": transaction.party_type,
			"party": transaction.party,
			"bank_account": bank_account,
		}
	)

	queries = get_queries(
		bank_account,
		company,
		transaction,
		document_types,
		from_date,
		to_date,
		filter_by_reference_date,
		from_reference_date,
		to_reference_date,
		exact_match,
		common_filters,
	)

	matching_vouchers = []
	for query in queries:
		matching_vouchers.extend(query.run(as_dict=True))

	return sorted(matching_vouchers, key=lambda x: x["rank"], reverse=True) if matching_vouchers else []


def get_queries(
	bank_account,
	company,
	transaction,
	document_types=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
	exact_match=None,
	common_filters=None,
):
	# get queries to get matching vouchers
	account_from_to = "paid_to" if transaction.deposit > 0.0 else "paid_from"
	queries = []

	# get matching queries from all the apps
	for method_name in frappe.get_hooks("get_matching_queries"):
		queries.extend(
			frappe.get_attr(method_name)(
				bank_account,
				company,
				transaction,
				document_types,
				exact_match,
				account_from_to,
				from_date,
				to_date,
				filter_by_reference_date,
				from_reference_date,
				to_reference_date,
				common_filters,
			)
			or []
		)

	return queries


def get_matching_queries(
	bank_account,
	company,
	transaction,
	document_types=None,
	exact_match=None,
	account_from_to=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
	common_filters=None,
):
	queries = []
	currency = get_account_currency(bank_account)

	if "payment_entry" in document_types:
		query = get_pe_matching_query(
			exact_match,
			account_from_to,
			transaction,
			from_date,
			to_date,
			filter_by_reference_date,
			from_reference_date,
			to_reference_date,
			common_filters,
		)
		queries.append(query)

	if "journal_entry" in document_types:
		query = get_je_matching_query(
			exact_match,
			transaction,
			from_date,
			to_date,
			filter_by_reference_date,
			from_reference_date,
			to_reference_date,
			common_filters,
		)
		queries.append(query)

	if transaction.deposit > 0.0 and "sales_invoice" in document_types:
		query = get_si_matching_query(exact_match, currency, common_filters, transaction)
		queries.append(query)

	if transaction.withdrawal > 0.0:
		if "purchase_invoice" in document_types:
			query = get_pi_matching_query(exact_match, currency, common_filters)
			queries.append(query)

	if "bank_transaction" in document_types:
		query = get_bt_matching_query(exact_match, transaction)
		queries.append(query)

	return queries


def get_bt_matching_query(exact_match, transaction):
	# get matching bank transaction query
	# find bank transactions in the same bank account with opposite sign
	# same bank account must have same company and currency
	bt = frappe.qb.DocType("Bank Transaction")

	field = "deposit" if transaction.withdrawal > 0.0 else "withdrawal"
	amount_equality = getattr(bt, field) == transaction.unallocated_amount
	amount_rank = frappe.qb.terms.Case().when(amount_equality, 1).else_(0)
	amount_condition = amount_equality if exact_match else getattr(bt, field) > 0.0

	ref_rank = frappe.qb.terms.Case().when(bt.reference_number == transaction.reference_number, 1).else_(0)
	unallocated_rank = (
		frappe.qb.terms.Case().when(bt.unallocated_amount == transaction.unallocated_amount, 1).else_(0)
	)

	party_condition = (
		(bt.party_type == transaction.party_type) & (bt.party == transaction.party) & bt.party.isnotnull()
	)
	party_rank = frappe.qb.terms.Case().when(party_condition, 1).else_(0)

	query = (
		frappe.qb.from_(bt)
		.select(
			(ref_rank + amount_rank + party_rank + unallocated_rank + 1).as_("rank"),
			ConstantColumn("Bank Transaction").as_("doctype"),
			bt.name,
			bt.unallocated_amount.as_("paid_amount"),
			bt.reference_number.as_("reference_no"),
			bt.date.as_("reference_date"),
			bt.party,
			bt.party_type,
			bt.date.as_("posting_date"),
			bt.currency,
		)
		.where(bt.status != "Reconciled")
		.where(bt.name != transaction.name)
		.where(bt.bank_account == transaction.bank_account)
		.where(amount_condition)
		.where(bt.docstatus == 1)
	)
	return query


def get_pe_matching_query(
	exact_match,
	account_from_to,
	transaction,
	from_date,
	to_date,
	filter_by_reference_date,
	from_reference_date,
	to_reference_date,
	common_filters,
):
	# get matching payment entries query
	to_from = "to" if transaction.deposit > 0.0 else "from"
	currency_field = f"paid_{to_from}_account_currency"
	payment_type = "Receive" if transaction.deposit > 0.0 else "Pay"
	pe = frappe.qb.DocType("Payment Entry")

	ref_condition = pe.reference_no == transaction.reference_number
	ref_rank = frappe.qb.terms.Case().when(ref_condition, 1).else_(0)

	amount_equality = pe.paid_amount == transaction.unallocated_amount
	amount_rank = frappe.qb.terms.Case().when(amount_equality, 1).else_(0)
	amount_condition = amount_equality if exact_match else pe.paid_amount > 0.0

	party_condition = (
		(pe.party_type == transaction.party_type) & (pe.party == transaction.party) & pe.party.isnotnull()
	)
	party_rank = frappe.qb.terms.Case().when(party_condition, 1).else_(0)

	filter_by_date = pe.posting_date.between(from_date, to_date)
	if cint(filter_by_reference_date):
		filter_by_date = pe.reference_date.between(from_reference_date, to_reference_date)

	query = (
		frappe.qb.from_(pe)
		.select(
			(ref_rank + amount_rank + party_rank + 1).as_("rank"),
			ConstantColumn("Payment Entry").as_("doctype"),
			pe.name,
			pe.base_paid_amount_after_tax.as_("paid_amount"),
			pe.reference_no,
			pe.reference_date,
			pe.party,
			pe.party_type,
			pe.posting_date,
			getattr(pe, currency_field).as_("currency"),
		)
		.where(pe.docstatus == 1)
		.where(pe.payment_type.isin([payment_type, "Internal Transfer"]))
		.where(pe.clearance_date.isnull())
		.where(getattr(pe, account_from_to) == common_filters.bank_account)
		.where(amount_condition)
		.where(filter_by_date)
		.orderby(pe.reference_date if cint(filter_by_reference_date) else pe.posting_date)
	)

	if frappe.flags.auto_reconcile_vouchers is True:
		query = query.where(ref_condition)

	return query


def get_je_matching_query(
	exact_match,
	transaction,
	from_date,
	to_date,
	filter_by_reference_date,
	from_reference_date,
	to_reference_date,
	common_filters,
):
	# get matching journal entry query
	# We have mapping at the bank level
	# So one bank could have both types of bank accounts like asset and liability
	# So cr_or_dr should be judged only on basis of withdrawal and deposit and not account type
	cr_or_dr = "credit" if transaction.withdrawal > 0.0 else "debit"
	je = frappe.qb.DocType("Journal Entry")
	jea = frappe.qb.DocType("Journal Entry Account")

	amount_field = f"{cr_or_dr}_in_account_currency"

	filter_by_date = je.posting_date.between(from_date, to_date)
	if cint(filter_by_reference_date):
		filter_by_date = je.cheque_date.between(from_reference_date, to_reference_date)

	subquery = (
		frappe.qb.from_(jea)
		.join(je)
		.on(jea.parent == je.name)
		.select(
			Sum(getattr(jea, amount_field)).as_("paid_amount"),
			ConstantColumn("Journal Entry").as_("doctype"),
			je.name,
			je.cheque_no.as_("reference_no"),
			je.cheque_date.as_("reference_date"),
			je.pay_to_recd_from.as_("party"),
			jea.party_type,
			je.posting_date,
			jea.account_currency.as_("currency"),
		)
		.where(je.docstatus == 1)
		.where(je.voucher_type != "Opening Entry")
		.where(je.clearance_date.isnull())
		.where(jea.account == common_filters.bank_account)
		.where(filter_by_date)
		.groupby(je.name)
		.orderby(je.cheque_date if cint(filter_by_reference_date) else je.posting_date)
	)

	if frappe.flags.auto_reconcile_vouchers is True:
		subquery = subquery.where(je.cheque_no == transaction.reference_number)

	ref_rank = frappe.qb.terms.Case().when(subquery.reference_no == transaction.reference_number, 1).else_(0)
	amount_equality = subquery.paid_amount == transaction.unallocated_amount
	amount_rank = frappe.qb.terms.Case().when(amount_equality, 1).else_(0)

	query = (
		frappe.qb.from_(subquery)
		.select(
			"*",
			(ref_rank + amount_rank + 1).as_("rank"),
		)
		.where(amount_equality if exact_match else subquery.paid_amount > 0.0)
	)

	return query


def get_si_matching_query(exact_match, currency, common_filters, transaction):
	# get matching sales invoice query
	si = frappe.qb.DocType("Sales Invoice")
	sip = frappe.qb.DocType("Sales Invoice Payment")

	ref_condition = sip.reference_no == transaction.reference_number
	ref_rank = frappe.qb.terms.Case().when(ref_condition, 1).else_(0)

	amount_equality = sip.amount == common_filters.amount
	amount_rank = frappe.qb.terms.Case().when(amount_equality, 1).else_(0)
	amount_condition = amount_equality if exact_match else sip.amount > 0.0

	party_condition = si.customer == common_filters.party
	party_rank = frappe.qb.terms.Case().when(party_condition, 1).else_(0)

	query = (
		frappe.qb.from_(sip)
		.join(si)
		.on(sip.parent == si.name)
		.select(
			(ref_rank + party_rank + amount_rank + 1).as_("rank"),
			ConstantColumn("Sales Invoice").as_("doctype"),
			si.name,
			sip.amount.as_("paid_amount"),
			sip.reference_no,
			ConstantColumn("").as_("reference_date"),
			si.customer.as_("party"),
			ConstantColumn("Customer").as_("party_type"),
			si.posting_date,
			si.currency,
		)
		.where(si.docstatus == 1)
		.where(sip.clearance_date.isnull())
		.where(sip.account == common_filters.bank_account)
		.where(amount_condition)
		.where(si.currency == currency)
	)

	if frappe.flags.auto_reconcile_vouchers is True:
		query = query.where(ref_condition)

	return query


def get_pi_matching_query(exact_match, currency, common_filters):
	# get matching purchase invoice query when they are also used as payment entries (is_paid)
	purchase_invoice = frappe.qb.DocType("Purchase Invoice")

	amount_equality = purchase_invoice.paid_amount == common_filters.amount
	amount_rank = frappe.qb.terms.Case().when(amount_equality, 1).else_(0)
	amount_condition = amount_equality if exact_match else purchase_invoice.paid_amount > 0.0

	party_condition = purchase_invoice.supplier == common_filters.party
	party_rank = frappe.qb.terms.Case().when(party_condition, 1).else_(0)

	query = (
		frappe.qb.from_(purchase_invoice)
		.select(
			(party_rank + amount_rank + 1).as_("rank"),
			ConstantColumn("Purchase Invoice").as_("doctype"),
			purchase_invoice.name,
			purchase_invoice.paid_amount,
			ConstantColumn("").as_("reference_no"),
			ConstantColumn("").as_("reference_date"),
			purchase_invoice.supplier.as_("party"),
			ConstantColumn("Supplier").as_("party_type"),
			purchase_invoice.posting_date,
			purchase_invoice.currency,
		)
		.where(purchase_invoice.docstatus == 1)
		.where(purchase_invoice.is_paid == 1)
		.where(purchase_invoice.clearance_date.isnull())
		.where(purchase_invoice.cash_bank_account == common_filters.bank_account)
		.where(amount_condition)
		.where(purchase_invoice.currency == currency)
	)

	return query
