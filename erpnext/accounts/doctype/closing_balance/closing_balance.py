# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)


class ClosingBalance(Document):
	pass


def make_closing_entries(closing_entries, voucher_name):
	accounting_dimensions = get_accounting_dimensions()
	company = closing_entries[0].get("company")
	closing_date = closing_entries[0].get("closing_date")

	previous_closing_entries = get_previous_closing_entries(
		company, closing_date, accounting_dimensions
	)
	combined_entries = closing_entries + previous_closing_entries

	merged_entries = aggregate_with_last_closing_balance(combined_entries, accounting_dimensions)

	for key, value in merged_entries.items():
		cle = frappe.new_doc("Closing Balance")
		cle.update(value)
		cle.update(value["dimensions"])
		cle.update(
			{
				"period_closing_voucher": voucher_name,
				"closing_date": closing_date,
			}
		)
		cle.submit()


def aggregate_with_last_closing_balance(entries, accounting_dimensions):
	merged_entries = {}
	for entry in entries:
		key, key_values = generate_key(entry, accounting_dimensions)
		merged_entries.setdefault(
			key,
			{
				"debit": 0,
				"credit": 0,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": 0,
			},
		)

		merged_entries[key]["dimensions"] = key_values
		merged_entries[key]["debit"] += entry.get("debit")
		merged_entries[key]["credit"] += entry.get("credit")
		merged_entries[key]["debit_in_account_currency"] += entry.get("debit_in_account_currency")
		merged_entries[key]["credit_in_account_currency"] += entry.get("credit_in_account_currency")

	return merged_entries


def generate_key(entry, accounting_dimensions):
	key = [
		entry.get("account"),
		entry.get("account_currency"),
		entry.get("cost_center"),
		entry.get("project"),
		entry.get("finance_book"),
		entry.get("is_period_closing_voucher_entry"),
	]

	key_values = {
		"account": entry.get("account"),
		"account_currency": entry.get("account_currency"),
		"cost_center": entry.get("cost_center"),
		"project": entry.get("project"),
		"finance_book": entry.get("finance_book"),
		"is_period_closing_voucher_entry": entry.get("is_period_closing_voucher_entry"),
	}
	for dimension in accounting_dimensions:
		key.append(entry.get(dimension))
		key_values[dimension] = entry.get(dimension)

	return tuple(key), key_values


def get_previous_closing_entries(company, closing_date, accounting_dimensions):
	entries = []
	last_period_closing_voucher = frappe.db.get_all(
		"Period Closing Voucher",
		filters={"docstatus": 1, "company": company, "posting_date": ("<", closing_date)},
		fields=["name"],
		order_by="posting_date desc",
		limit=1,
	)

	if last_period_closing_voucher:
		closing_balance = frappe.qb.DocType("Closing Balance")
		query = frappe.qb.from_(closing_balance).select(
			closing_balance.account,
			closing_balance.account_currency,
			closing_balance.debit,
			closing_balance.credit,
			closing_balance.debit_in_account_currency,
			closing_balance.credit_in_account_currency,
			closing_balance.cost_center,
			closing_balance.project,
			closing_balance.finance_book,
			closing_balance.is_period_closing_voucher_entry,
		)

		for dimension in accounting_dimensions:
			query = query.select(closing_balance[dimension])

		query = query.where(
			closing_balance.period_closing_voucher == last_period_closing_voucher[0].name
		)
		entries = query.run(as_dict=1)

	return entries
