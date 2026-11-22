# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Voucher builders for the cash basis tests. Each builder submits a real document."""

import frappe
from frappe.utils import flt

from erpnext.accounts.cash_basis.tests.fixtures import (
	CUSTOMER,
	SERVICE_ITEMS,
	SUPPLIER,
	US_ABBR,
	US_COMPANY,
	acc,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

MAIN_CC = f"Main - {US_ABBR}"
BANK = acc("Test Bank")


def line(amount, account=None, cost_center=MAIN_CC, item_code=None, qty=1, **extra):
	return frappe._dict(
		amount=amount, account=account, cost_center=cost_center, item_code=item_code, qty=qty, **extra
	)


def make_sales_invoice(posting_date, lines, taxes=(), customer=CUSTOMER, submit=True, **fields):
	doc = frappe.new_doc("Sales Invoice")
	doc.update(
		{
			"company": US_COMPANY,
			"customer": customer,
			"posting_date": posting_date,
			"set_posting_time": 1,
			"due_date": posting_date,
			"currency": "USD",
			"debit_to": acc("Debtors"),
			"cost_center": MAIN_CC,
		}
	)
	doc.update(fields)
	for idx, row in enumerate(lines):
		doc.append(
			"items",
			{
				"item_code": row.item_code or SERVICE_ITEMS[idx],
				"qty": row.qty,
				"rate": flt(row.amount) / row.qty,
				"income_account": row.account or acc("Sales"),
				"cost_center": row.cost_center,
				**{
					k: v
					for k, v in row.items()
					if k not in ("amount", "account", "cost_center", "item_code", "qty")
				},
			},
		)
	append_taxes(doc, taxes)
	return save(doc, submit)


def make_purchase_invoice(posting_date, lines, taxes=(), supplier=SUPPLIER, submit=True, **fields):
	doc = frappe.new_doc("Purchase Invoice")
	doc.update(
		{
			"company": US_COMPANY,
			"supplier": supplier,
			"posting_date": posting_date,
			"set_posting_time": 1,
			"bill_date": posting_date,
			"due_date": posting_date,
			"currency": "USD",
			"credit_to": acc("Creditors"),
			"cost_center": MAIN_CC,
		}
	)
	doc.update(fields)
	for idx, row in enumerate(lines):
		doc.append(
			"items",
			{
				"item_code": row.item_code or SERVICE_ITEMS[idx],
				"qty": row.qty,
				"rate": flt(row.amount) / row.qty,
				"expense_account": row.account or acc("Office Rent"),
				"cost_center": row.cost_center,
				**{
					k: v
					for k, v in row.items()
					if k not in ("amount", "account", "cost_center", "item_code", "qty")
				},
			},
		)
	append_taxes(doc, taxes)
	return save(doc, submit)


def append_taxes(doc, taxes):
	for account, amount, *rest in taxes:
		category = rest[0] if rest else "Total"
		doc.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": account,
				"description": account,
				"tax_amount": amount,
				"cost_center": MAIN_CC,
				"category": category,
				"add_deduct_tax": "Add",
			},
		)


def pay(invoice, posting_date, amount=None, bank=BANK, submit=True, **fields):
	"""A Payment Entry against one invoice, for all or part of its outstanding amount."""
	doc = get_payment_entry(invoice.doctype, invoice.name, party_amount=amount, bank_account=bank)
	doc.posting_date = posting_date
	doc.reference_no = invoice.name
	doc.reference_date = posting_date
	if amount is not None:
		doc.paid_amount = doc.received_amount = amount
		doc.references[0].allocated_amount = amount
	doc.update(fields)
	return save(doc, submit)


def make_advance(
	party_type,
	party,
	posting_date,
	amount,
	bank=BANK,
	party_account=None,
	submit=True,
	references=(),
	**fields,
):
	"""A Payment Entry: a receipt from a customer or a payment to a supplier.

	references: (doctype, name, allocated amount). With none, the payment is unallocated.
	"""
	receive = party_type == "Customer"
	doc = frappe.new_doc("Payment Entry")
	doc.update(
		{
			"company": US_COMPANY,
			"payment_type": "Receive" if receive else "Pay",
			"party_type": party_type,
			"party": party,
			"posting_date": posting_date,
			"paid_from": (party_account or acc("Debtors")) if receive else bank,
			"paid_to": bank if receive else (party_account or acc("Creditors")),
			"paid_amount": amount,
			"received_amount": amount,
			"reference_no": f"ADV-{posting_date}",
			"reference_date": posting_date,
			**fields,
		}
	)
	for reference_doctype, reference_name, allocated in references:
		doc.append(
			"references",
			{
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
				"allocated_amount": allocated,
			},
		)
	doc.setup_party_account_field()
	doc.set_missing_values()
	return save(doc, submit)


def make_journal_entry(posting_date, rows, submit=True, **fields):
	"""rows: dicts with account, debit or credit, and optional party_type, party, reference_type, reference_name."""
	doc = frappe.new_doc("Journal Entry")
	doc.update({"company": US_COMPANY, "posting_date": posting_date, "voucher_type": "Journal Entry"})
	doc.update(fields)
	for row in rows:
		doc.append(
			"accounts",
			{
				"cost_center": frappe.get_cached_value("Company", doc.company, "cost_center"),
				"debit_in_account_currency": row.get("debit", 0),
				"credit_in_account_currency": row.get("credit", 0),
				**{k: v for k, v in row.items() if k not in ("debit", "credit")},
			},
		)
	return save(doc, submit)


def make_return(invoice, posting_date, amount, submit=True):
	"""A credit note or a debit note for a part of the first item of the invoice."""
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	doc = make_return_doc(invoice.doctype, invoice.name)
	doc.posting_date = posting_date
	doc.set_posting_time = 1
	doc.due_date = posting_date
	doc.items = doc.items[:1]
	doc.items[0].qty = -1
	doc.items[0].rate = flt(amount)
	doc.taxes = []
	return save(doc, submit)


def reconcile(party_type, party, receivable_payable_account, advance_account=None):
	"""Reconcile all open payments and invoices of the party, as the Payment Reconciliation tool does."""
	pr = frappe.new_doc("Payment Reconciliation")
	pr.company = US_COMPANY
	pr.party_type = party_type
	pr.party = party
	pr.receivable_payable_account = receivable_payable_account
	pr.default_advance_account = advance_account
	pr.get_unreconciled_entries()
	invoices = [row.as_dict() for row in pr.invoices]
	payments = [row.as_dict() for row in pr.payments]
	pr.allocate_entries(frappe._dict(invoices=invoices, payments=payments))
	pr.reconcile()
	return pr


def save(doc, submit):
	doc.insert()
	if submit:
		doc.submit()
	return doc
