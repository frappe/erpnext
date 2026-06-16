# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Document builders that map a source document to a Journal Entry or to a
Payment Entry raised against it."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form, nowdate

from erpnext.accounts.doctype.invoice_discounting.invoice_discounting import (
	get_party_account_based_on_invoice_discounting,
)
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_account_currency


@frappe.whitelist()
def get_payment_entry_against_order(
	dt: str,
	dn: str,
	amount: float | None = None,
	debit_in_account_currency: str | float | None = None,
	journal_entry: bool = False,
	bank_account: str | None = None,
) -> dict | Document:
	"""Build an advance-payment Journal Entry against an unbilled Sales/Purchase Order."""
	ref_doc = frappe.get_doc(dt, dn)

	if flt(ref_doc.per_billed, 2) > 0:
		frappe.throw(_("Can only make payment against unbilled {0}").format(dt))

	if dt == "Sales Order":
		party_type = "Customer"
		amount_field_party = "credit_in_account_currency"
		amount_field_bank = "debit_in_account_currency"
	else:
		party_type = "Supplier"
		amount_field_party = "debit_in_account_currency"
		amount_field_bank = "credit_in_account_currency"

	party_account = get_party_account(party_type, ref_doc.get(party_type.lower()), ref_doc.company)
	party_account_currency = get_account_currency(party_account)

	if not amount:
		if party_account_currency == ref_doc.company_currency:
			amount = flt(ref_doc.base_grand_total) - flt(ref_doc.advance_paid)
		else:
			amount = flt(ref_doc.grand_total) - flt(ref_doc.advance_paid)

	return get_payment_entry(
		ref_doc,
		{
			"party_type": party_type,
			"party_account": party_account,
			"party_account_currency": party_account_currency,
			"amount_field_party": amount_field_party,
			"amount_field_bank": amount_field_bank,
			"amount": amount,
			"debit_in_account_currency": debit_in_account_currency,
			"remarks": f"Advance Payment received against {dt} {dn}",
			"is_advance": "Yes",
			"bank_account": bank_account,
			"journal_entry": journal_entry,
		},
	)


@frappe.whitelist()
def get_payment_entry_against_invoice(
	dt: str,
	dn: str,
	amount: float | None = None,
	debit_in_account_currency: str | None = None,
	journal_entry: bool = False,
	bank_account: str | None = None,
) -> dict | Document:
	"""Build a payment Journal Entry against a Sales/Purchase Invoice's outstanding amount."""
	ref_doc = frappe.get_doc(dt, dn)
	if dt == "Sales Invoice":
		party_type = "Customer"
		party_account = get_party_account_based_on_invoice_discounting(dn) or ref_doc.debit_to
	else:
		party_type = "Supplier"
		party_account = ref_doc.credit_to

	if (dt == "Sales Invoice" and ref_doc.outstanding_amount > 0) or (
		dt == "Purchase Invoice" and ref_doc.outstanding_amount < 0
	):
		amount_field_party = "credit_in_account_currency"
		amount_field_bank = "debit_in_account_currency"
	else:
		amount_field_party = "debit_in_account_currency"
		amount_field_bank = "credit_in_account_currency"

	return get_payment_entry(
		ref_doc,
		{
			"party_type": party_type,
			"party_account": party_account,
			"party_account_currency": ref_doc.party_account_currency,
			"amount_field_party": amount_field_party,
			"amount_field_bank": amount_field_bank,
			"amount": amount if amount else abs(ref_doc.outstanding_amount),
			"debit_in_account_currency": debit_in_account_currency,
			"remarks": f"Payment received against {dt} {dn}. {ref_doc.remarks}",
			"is_advance": "No",
			"bank_account": bank_account,
			"journal_entry": journal_entry,
		},
	)


def get_payment_entry(ref_doc, args: dict) -> dict | Document:
	"""Build a Bank Entry Journal Entry paying `ref_doc`, with a party row and a bank row.

	Returns the Journal Entry document when `args["journal_entry"]` is truthy, otherwise its
	dict (for client calls).
	"""
	je = frappe.new_doc("Journal Entry")
	je.update({"voucher_type": "Bank Entry", "company": ref_doc.company, "remark": args.get("remarks")})

	cost_center = ref_doc.get("cost_center") or frappe.get_cached_value(
		"Company", ref_doc.company, "cost_center"
	)
	exchange_rate = _reference_exchange_rate(ref_doc, args)

	party_row = _append_party_row(je, ref_doc, args, cost_center, exchange_rate)
	bank_row = _append_bank_row(je, ref_doc, args, cost_center, exchange_rate)

	if party_row.account_currency != ref_doc.company_currency or (
		bank_row.account_currency and bank_row.account_currency != ref_doc.company_currency
	):
		je.multi_currency = 1

	je.set_amounts_in_company_currency()
	je.set_total_debit_credit()

	return je if args.get("journal_entry") else je.as_dict()


def _reference_exchange_rate(ref_doc, args: dict) -> float:
	"""Exchange rate of the party account on the reference document's posting date."""
	if not args.get("party_account"):
		return 1

	from erpnext.accounts.doctype.journal_entry.journal_entry import get_exchange_rate

	return get_exchange_rate(
		ref_doc.get("posting_date") or ref_doc.get("transaction_date"),
		args.get("party_account"),
		args.get("party_account_currency"),
		ref_doc.company,
		ref_doc.doctype,
		ref_doc.name,
	)


def _append_party_row(je, ref_doc, args: dict, cost_center, exchange_rate: float):
	"""Append the party (debtor/creditor) row that records the advance/payment."""
	return je.append(
		"accounts",
		{
			"account": args.get("party_account"),
			"party_type": args.get("party_type"),
			"party": ref_doc.get(args.get("party_type").lower()),
			"cost_center": cost_center,
			"account_type": frappe.get_cached_value("Account", args.get("party_account"), "account_type"),
			"account_currency": args.get("party_account_currency")
			or get_account_currency(args.get("party_account")),
			"exchange_rate": exchange_rate,
			args.get("amount_field_party"): args.get("amount"),
			"is_advance": args.get("is_advance"),
			"reference_type": ref_doc.doctype,
			"reference_name": ref_doc.name,
		},
	)


def _append_bank_row(je, ref_doc, args: dict, cost_center, exchange_rate: float):
	"""Append the bank/cash row, defaulting the account and converting the amount to it."""
	from erpnext.accounts.doctype.journal_entry.journal_entry import (
		get_default_bank_cash_account,
		get_exchange_rate,
	)

	bank_row = je.append("accounts")
	bank_account = get_default_bank_cash_account(ref_doc.company, "Bank", account=args.get("bank_account"))
	if bank_account:
		bank_row.update(bank_account)
		# posting date assumed to be the reference document's posting/transaction date
		bank_row.exchange_rate = get_exchange_rate(
			ref_doc.get("posting_date") or ref_doc.get("transaction_date"),
			bank_account["account"],
			bank_account["account_currency"],
			ref_doc.company,
		)

	bank_row.cost_center = cost_center

	amount = args.get("debit_in_account_currency") or args.get("amount")
	if bank_row.account_currency == args.get("party_account_currency"):
		bank_row.set(args.get("amount_field_bank"), amount)
	else:
		bank_row.set(args.get("amount_field_bank"), amount * exchange_rate)

	return bank_row


@frappe.whitelist()
def make_inter_company_journal_entry(name: str, voucher_type: str, company: str) -> dict:
	"""Build the counterpart Journal Entry in another company, linked back to `name`."""
	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.voucher_type = voucher_type
	journal_entry.company = company
	journal_entry.posting_date = nowdate()
	journal_entry.inter_company_journal_entry_reference = name
	return journal_entry.as_dict()


@frappe.whitelist()
def make_reverse_journal_entry(source_name: str, target_doc: str | Document | None = None) -> Document:
	"""Map a submitted Journal Entry to a reversing one (debits and credits swapped)."""
	existing_reverse = frappe.db.exists("Journal Entry", {"reversal_of": source_name, "docstatus": 1})
	if existing_reverse:
		frappe.throw(
			_("A Reverse Journal Entry {0} already exists for this Journal Entry.").format(
				get_link_to_form("Journal Entry", existing_reverse)
			)
		)

	from frappe.model.mapper import get_mapped_doc

	def post_process(source, target) -> None:
		target.reversal_of = source.name

	doclist = get_mapped_doc(
		"Journal Entry",
		source_name,
		{
			"Journal Entry": {"doctype": "Journal Entry", "validation": {"docstatus": ["=", 1]}},
			"Journal Entry Account": {
				"doctype": "Journal Entry Account",
				"field_map": {
					"account_currency": "account_currency",
					"exchange_rate": "exchange_rate",
					"debit_in_account_currency": "credit_in_account_currency",
					"debit": "credit",
					"credit_in_account_currency": "debit_in_account_currency",
					"credit": "debit",
					"reference_type": "reference_type",
					"reference_name": "reference_name",
				},
			},
		},
		target_doc,
		post_process,
	)

	return doclist
