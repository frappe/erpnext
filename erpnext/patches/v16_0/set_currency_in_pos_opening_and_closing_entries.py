from collections import defaultdict

import frappe
from frappe.utils import now_datetime

from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import build_invoice_query


def execute():
	invoice_currency = get_invoice_currency_by_closing_entry()
	closing_currency = {
		name: invoice_currency.get(name) or profile_currency
		for name, profile_currency in get_entries_without_currency("POS Closing Entry")
	}
	update_currency("POS Closing Entry", closing_currency)

	opening_entries = get_entries_without_currency(
		"POS Opening Entry", "pos_closing_entry", "status", "pos_profile", "user", "period_start_date"
	)
	stored_closing_currency = get_closing_entry_currency({d[2] for d in opening_entries if d[2]})
	opening_currency = {
		name: stored_closing_currency.get(closing_entry)
		or (status == "Open" and get_open_session_currency(pos_profile, user, start))
		or profile_currency
		for name, profile_currency, closing_entry, status, pos_profile, user, start in opening_entries
	}
	update_currency("POS Opening Entry", opening_currency)


def get_entries_without_currency(doctype, *fields):
	entry = frappe.qb.DocType(doctype)
	profile = frappe.qb.DocType("POS Profile")

	return (
		frappe.qb.from_(entry)
		.left_join(profile)
		.on(profile.name == entry.pos_profile)
		.select(entry.name, profile.currency, *(entry[field] for field in fields))
		.where(entry.currency.isnull() | (entry.currency == ""))
		.run()
	)


def get_invoice_currency_by_closing_entry():
	currency_by_closing_entry = {}
	for reference_doctype, invoice_doctype, invoice_field in (
		("POS Invoice Reference", "POS Invoice", "pos_invoice"),
		("Sales Invoice Reference", "Sales Invoice", "sales_invoice"),
	):
		reference = frappe.qb.DocType(reference_doctype)
		invoice = frappe.qb.DocType(invoice_doctype)
		rows = (
			frappe.qb.from_(reference)
			.join(invoice)
			.on(invoice.name == reference[invoice_field])
			.select(reference.parent, invoice.currency)
			.where(reference.parenttype == "POS Closing Entry")
			.distinct()
			.run()
		)
		for closing_entry, currency in rows:
			currency_by_closing_entry.setdefault(closing_entry, currency)

	return currency_by_closing_entry


def get_open_session_currency(pos_profile, user, start):
	"""Currency of the invoices an open session has made so far, as its closing entry would collect them."""
	for invoice_doctype in ("POS Invoice", "Sales Invoice"):
		invoice = frappe.qb.DocType(invoice_doctype)
		query = build_invoice_query(invoice_doctype, user, pos_profile, start, now_datetime())
		rows = query.select(invoice.currency.as_("session_currency")).limit(1).run(as_dict=True)
		if rows:
			return rows[0].session_currency


def get_closing_entry_currency(closing_entries):
	if not closing_entries:
		return {}

	return dict(
		frappe.get_all(
			"POS Closing Entry",
			filters={"name": ("in", list(closing_entries))},
			fields=["name", "currency"],
			as_list=True,
		)
	)


def update_currency(doctype, currency_by_name):
	names_by_currency = defaultdict(list)
	for name, currency in currency_by_name.items():
		if currency:
			names_by_currency[currency].append(name)

	entry = frappe.qb.DocType(doctype)
	for currency, names in names_by_currency.items():
		frappe.qb.update(entry).set(entry.currency, currency).where(entry.name.isin(names)).run()
