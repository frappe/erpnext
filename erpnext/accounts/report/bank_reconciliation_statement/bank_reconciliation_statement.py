# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import flt, getdate
from pypika import Order

from erpnext.accounts.utils import get_balance_on


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()

	if not filters.get("account"):
		return columns, []

	account_currency = frappe.get_cached_value("Account", filters.account, "account_currency")

	data = get_entries(filters)

	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0, 0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	amounts_not_reflected_in_system = get_amounts_not_reflected_in_system(filters)

	bank_bal = (
		flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) + amounts_not_reflected_in_system
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
	entries = []

	for method_name in frappe.get_hooks("get_entries_for_bank_reconciliation_statement"):
		entries += frappe.get_attr(method_name)(filters) or []

	return sorted(
		entries,
		key=lambda k: getdate(k["posting_date"]),
	)


def get_entries_for_bank_reconciliation_statement(filters):
	journal_entries = get_journal_entries(filters)

	payment_entries = get_payment_entries(filters)

	purchase_invoices = get_purchase_invoices(filters)

	pos_entries = []
	if filters.include_pos_transactions:
		pos_entries = get_pos_entries(filters)

	return list(journal_entries) + list(payment_entries) + list(pos_entries) + list(purchase_invoices)


def get_journal_entries(filters):
	je = frappe.qb.DocType("Journal Entry")
	jea = frappe.qb.DocType("Journal Entry Account")
	return (
		frappe.qb.from_(jea)
		.join(je)
		.on(jea.parent == je.name)
		.select(
			ConstantColumn("Journal Entry").as_("payment_document"),
			je.name.as_("payment_entry"),
			je.posting_date,
			jea.debit_in_account_currency.as_("debit"),
			jea.credit_in_account_currency.as_("credit"),
			jea.against_account,
			je.cheque_no.as_("reference_no"),
			je.cheque_date.as_("ref_date"),
			je.clearance_date,
			jea.account_currency,
		)
		.where(
			(je.docstatus == 1)
			& (jea.account == filters.account)
			& (je.posting_date <= filters.report_date)
			& (je.clearance_date.isnull() | (je.clearance_date > filters.report_date))
			& (je.company == filters.company)
			& ((je.is_opening.isnull()) | (je.is_opening == "No"))
		)
		.orderby(je.posting_date)
		.orderby(je.name, order=Order.desc)
	).run(as_dict=True)


def get_payment_entries(filters):
	pe = frappe.qb.DocType("Payment Entry")
	return (
		frappe.qb.from_(pe)
		.select(
			ConstantColumn("Payment Entry").as_("payment_document"),
			pe.name.as_("payment_entry"),
			pe.reference_no.as_("reference_no"),
			pe.reference_date.as_("ref_date"),
			Case().when(pe.paid_to == filters.account, pe.received_amount_after_tax).else_(0).as_("debit"),
			Case().when(pe.paid_from == filters.account, pe.paid_amount_after_tax).else_(0).as_("credit"),
			pe.posting_date,
			Coalesce(
				pe.party, Case().when(pe.paid_from == filters.account, pe.paid_to).else_(pe.paid_from)
			).as_("against_account"),
			pe.clearance_date,
			(
				Case()
				.when(pe.paid_to == filters.account, pe.paid_to_account_currency)
				.else_(pe.paid_from_account_currency)
			).as_("account_currency"),
		)
		.where(
			(pe.docstatus == 1)
			& ((pe.paid_from == filters.account) | (pe.paid_to == filters.account))
			& (pe.posting_date <= filters.report_date)
			& (pe.clearance_date.isnull() | (pe.clearance_date > filters.report_date))
			& (pe.company == filters.company)
		)
		.orderby(pe.posting_date)
		.orderby(pe.name, order=Order.desc)
	).run(as_dict=True)


def get_purchase_invoices(filters):
	pi = frappe.qb.DocType("Purchase Invoice")
	acc = frappe.qb.DocType("Account")
	return (
		frappe.qb.from_(pi)
		.inner_join(acc)
		.on(pi.cash_bank_account == acc.name)
		.select(
			ConstantColumn("Purchase Invoice").as_("payment_document"),
			pi.name.as_("payment_entry"),
			pi.bill_no.as_("reference_no"),
			pi.posting_date.as_("ref_date"),
			Case().when(pi.paid_amount < 0, pi.paid_amount * -1).else_(0).as_("debit"),
			Case().when(pi.paid_amount > 0, pi.paid_amount).else_(0).as_("credit"),
			pi.posting_date,
			pi.supplier.as_("against_account"),
			pi.clearance_date,
			acc.account_currency,
		)
		.where(
			(pi.docstatus == 1)
			& (pi.is_paid == 1)
			& (pi.cash_bank_account == filters.account)
			& (pi.posting_date <= filters.report_date)
			& (pi.clearance_date.isnull() | (pi.clearance_date > filters.report_date))
			& (pi.company == filters.company)
		)
		.orderby(pi.posting_date)
		.orderby(pi.name, order=Order.desc)
	).run(as_dict=True)


def get_pos_entries(filters):
	si = frappe.qb.DocType("Sales Invoice")
	si_payment = frappe.qb.DocType("Sales Invoice Payment")
	acc = frappe.qb.DocType("Account")
	return (
		frappe.qb.from_(si_payment)
		.join(si)
		.on(si_payment.parent == si.name)
		.join(acc)
		.on(si_payment.account == acc.name)
		.select(
			ConstantColumn("Sales Invoice").as_("payment_document"),
			si.name.as_("payment_entry"),
			si_payment.amount.as_("debit"),
			si.posting_date,
			si.debit_to.as_("against_account"),
			si_payment.clearance_date,
			acc.account_currency,
			ConstantColumn(0).as_("credit"),
		)
		.where(
			(si_payment.account == filters.account)
			& (si.docstatus == 1)
			& (si.posting_date <= filters.report_date)
			& (si_payment.clearance_date.isnull() | (si_payment.clearance_date > filters.report_date))
			& (si.company == filters.company)
		)
		.orderby(si.posting_date)
		.orderby(si_payment.name, order=Order.desc)
	).run(as_dict=True)


def get_amounts_not_reflected_in_system(filters):
	amount = 0.0

	# get amounts from all the apps
	for method_name in frappe.get_hooks(
		"get_amounts_not_reflected_in_system_for_bank_reconciliation_statement"
	):
		amount += frappe.get_attr(method_name)(filters) or 0.0

	return amount


def get_amounts_not_reflected_in_system_for_bank_reconciliation_statement(filters):
	je = frappe.qb.DocType("Journal Entry")
	jea = frappe.qb.DocType("Journal Entry Account")

	je_amount = (
		frappe.qb.from_(jea)
		.inner_join(je)
		.on(jea.parent == je.name)
		.select(
			Sum(jea.debit_in_account_currency - jea.credit_in_account_currency).as_("amount"),
		)
		.where(
			(je.docstatus == 1)
			& (jea.account == filters.account)
			& (je.posting_date > filters.report_date)
			& (je.clearance_date <= filters.report_date)
			& (je.company == filters.company)
			& ((je.is_opening.isnull()) | (je.is_opening == "No"))
		)
		.run(as_dict=True)
	)
	je_amount = flt(je_amount[0].amount) if je_amount else 0.0

	pe = frappe.qb.DocType("Payment Entry")
	pe_amount = (
		frappe.qb.from_(pe)
		.select(
			Sum(Case().when(pe.paid_from == filters.account, pe.paid_amount).else_(pe.received_amount)).as_(
				"amount"
			),
		)
		.where(
			((pe.paid_from == filters.account) | (pe.paid_to == filters.account))
			& (pe.docstatus == 1)
			& (pe.posting_date > filters.report_date)
			& (pe.clearance_date <= filters.report_date)
			& (pe.company == filters.company)
		)
		.run(as_dict=True)
	)
	pe_amount = flt(pe_amount[0].amount) if pe_amount else 0.0

	pi = frappe.qb.DocType("Purchase Invoice")
	pi_amount = (
		frappe.qb.from_(pi)
		.select(
			Sum(pi.paid_amount).as_("amount"),
		)
		.where(
			(pi.docstatus == 1)
			& (pi.is_paid == 1)
			& (pi.cash_bank_account == filters.account)
			& (pi.posting_date > filters.report_date)
			& (pi.clearance_date <= filters.report_date)
			& (pi.company == filters.company)
		)
	).run(as_dict=True)

	pi_amount = flt(pi_amount[0].amount) if pi_amount else 0.0

	return je_amount + pe_amount + pi_amount


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
