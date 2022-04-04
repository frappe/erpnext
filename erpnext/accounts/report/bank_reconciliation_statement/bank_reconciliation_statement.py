# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate
from pypika import CustomFunction

from erpnext.accounts.utils import get_balance_on


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()

	if not filters.get("account"):
		return columns, []

	account_currency = frappe.db.get_value("Account", filters.account, "account_currency")

	data = get_entries(filters)

	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0, 0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	amounts_not_reflected_in_system = get_amounts_not_reflected_in_system(filters)

	bank_bal = (
		flt(balance_as_per_system)
		- flt(total_debit)
		+ flt(total_credit)
		+ amounts_not_reflected_in_system
	)

	data += [
		get_balance_row(
			_("Bank Statement balance as per General Ledger"), balance_as_per_system, account_currency
		),
		{},
		{
			"payment_entry": _("Outstanding Cheques and Deposits to clear"),
			"debit": total_debit,
			"credit": total_credit,
			"account_currency": account_currency,
		},
		get_balance_row(
			_("Cheques and Deposits incorrectly cleared"), amounts_not_reflected_in_system, account_currency
		),
		{},
		get_balance_row(_("Calculated Bank Statement balance"), bank_bal, account_currency),
	]

	return columns, data


def get_columns():
	return [
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 90},
		{
			"fieldname": "payment_document",
			"label": _("Payment Document Type"),
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"fieldname": "payment_entry",
			"label": _("Payment Document"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 220,
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120,
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120,
		},
		{
			"fieldname": "against_account",
			"label": _("Against Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 200,
		},
		{"fieldname": "reference_no", "label": _("Reference"), "fieldtype": "Data", "width": 100},
		{"fieldname": "ref_date", "label": _("Ref Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "clearance_date", "label": _("Clearance Date"), "fieldtype": "Date", "width": 110},
		{
			"fieldname": "account_currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100,
		},
	]


def get_entries(filters):
	journal_entries = get_journal_entries(filters)

	payment_entries = get_payment_entries(filters)

	loan_entries = get_loan_entries(filters)

	pos_entries = []
	if filters.include_pos_transactions:
		pos_entries = get_pos_entries(filters)

	return sorted(
		list(payment_entries) + list(journal_entries + list(pos_entries) + list(loan_entries)),
		key=lambda k: getdate(k["posting_date"]),
	)


def get_journal_entries(filters):
	return frappe.db.sql(
		"""
		select "Journal Entry" as payment_document, jv.posting_date,
			jv.name as payment_entry, jvd.debit_in_account_currency as debit,
			jvd.credit_in_account_currency as credit, jvd.against_account,
			jv.cheque_no as reference_no, jv.cheque_date as ref_date, jv.clearance_date, jvd.account_currency
		from
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1
			and jvd.account = %(account)s and jv.posting_date <= %(report_date)s
			and ifnull(jv.clearance_date, '4000-01-01') > %(report_date)s
			and ifnull(jv.is_opening, 'No') = 'No'""",
		filters,
		as_dict=1,
	)


def get_payment_entries(filters):
	return frappe.db.sql(
		"""
		select
			"Payment Entry" as payment_document, name as payment_entry,
			reference_no, reference_date as ref_date,
			if(paid_to=%(account)s, received_amount, 0) as debit,
			if(paid_from=%(account)s, paid_amount, 0) as credit,
			posting_date, ifnull(party,if(paid_from=%(account)s,paid_to,paid_from)) as against_account, clearance_date,
			if(paid_to=%(account)s, paid_to_account_currency, paid_from_account_currency) as account_currency
		from `tabPayment Entry`
		where
			(paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
			and posting_date <= %(report_date)s
			and ifnull(clearance_date, '4000-01-01') > %(report_date)s
	""",
		filters,
		as_dict=1,
	)


def get_pos_entries(filters):
	return frappe.db.sql(
		"""
			select
				"Sales Invoice Payment" as payment_document, sip.name as payment_entry, sip.amount as debit,
				si.posting_date, si.debit_to as against_account, sip.clearance_date,
				account.account_currency, 0 as credit
			from `tabSales Invoice Payment` sip, `tabSales Invoice` si, `tabAccount` account
			where
				sip.account=%(account)s and si.docstatus=1 and sip.parent = si.name
				and account.name = sip.account and si.posting_date <= %(report_date)s and
				ifnull(sip.clearance_date, '4000-01-01') > %(report_date)s
			order by
				si.posting_date ASC, si.name DESC
		""",
		filters,
		as_dict=1,
	)


def get_loan_entries(filters):
	loan_docs = []
	for doctype in ["Loan Disbursement", "Loan Repayment"]:
		loan_doc = frappe.qb.DocType(doctype)
		ifnull = CustomFunction("IFNULL", ["value", "default"])

		if doctype == "Loan Disbursement":
			amount_field = (loan_doc.disbursed_amount).as_("credit")
			posting_date = (loan_doc.disbursement_date).as_("posting_date")
			account = loan_doc.disbursement_account
		else:
			amount_field = (loan_doc.amount_paid).as_("debit")
			posting_date = (loan_doc.posting_date).as_("posting_date")
			account = loan_doc.payment_account

		entries = (
			frappe.qb.from_(loan_doc)
			.select(
				ConstantColumn(doctype).as_("payment_document"),
				(loan_doc.name).as_("payment_entry"),
				(loan_doc.reference_number).as_("reference_no"),
				(loan_doc.reference_date).as_("ref_date"),
				amount_field,
				posting_date,
			)
			.where(loan_doc.docstatus == 1)
			.where(account == filters.get("account"))
			.where(posting_date <= getdate(filters.get("report_date")))
			.where(ifnull(loan_doc.clearance_date, "4000-01-01") > getdate(filters.get("report_date")))
			.run(as_dict=1)
		)

		loan_docs.extend(entries)

	return loan_docs


def get_amounts_not_reflected_in_system(filters):
	je_amount = frappe.db.sql(
		"""
		select sum(jvd.debit_in_account_currency - jvd.credit_in_account_currency)
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 and jvd.account=%(account)s
		and jv.posting_date > %(report_date)s and jv.clearance_date <= %(report_date)s
		and ifnull(jv.is_opening, 'No') = 'No' """,
		filters,
	)

	je_amount = flt(je_amount[0][0]) if je_amount else 0.0

	pe_amount = frappe.db.sql(
		"""
		select sum(if(paid_from=%(account)s, paid_amount, received_amount))
		from `tabPayment Entry`
		where (paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
		and posting_date > %(report_date)s and clearance_date <= %(report_date)s""",
		filters,
	)

	pe_amount = flt(pe_amount[0][0]) if pe_amount else 0.0

	loan_amount = get_loan_amount(filters)

	return je_amount + pe_amount + loan_amount


def get_loan_amount(filters):
	total_amount = 0
	for doctype in ["Loan Disbursement", "Loan Repayment"]:
		loan_doc = frappe.qb.DocType(doctype)
		ifnull = CustomFunction("IFNULL", ["value", "default"])

		if doctype == "Loan Disbursement":
			amount_field = Sum(loan_doc.disbursed_amount)
			posting_date = (loan_doc.disbursement_date).as_("posting_date")
			account = loan_doc.disbursement_account
		else:
			amount_field = Sum(loan_doc.amount_paid)
			posting_date = (loan_doc.posting_date).as_("posting_date")
			account = loan_doc.payment_account

		amount = (
			frappe.qb.from_(loan_doc)
			.select(amount_field)
			.where(loan_doc.docstatus == 1)
			.where(account == filters.get("account"))
			.where(posting_date > getdate(filters.get("report_date")))
			.where(ifnull(loan_doc.clearance_date, "4000-01-01") <= getdate(filters.get("report_date")))
			.run()[0][0]
		)

		total_amount += flt(amount)

	return total_amount


def get_balance_row(label, amount, account_currency):
	if amount > 0:
		return {
			"payment_entry": label,
			"debit": amount,
			"credit": 0,
			"account_currency": account_currency,
		}
	else:
		return {
			"payment_entry": label,
			"debit": 0,
			"credit": abs(amount),
			"account_currency": account_currency,
		}
