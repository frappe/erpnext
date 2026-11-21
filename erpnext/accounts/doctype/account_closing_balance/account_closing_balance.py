# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.docstatus import DocStatus
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, now

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.exceptions import ReportingCurrencyExchangeNotFoundError
from erpnext.setup.utils import get_exchange_rate


class AccountClosingBalance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		account_currency: DF.Link | None
		closing_date: DF.Date | None
		company: DF.Link | None
		cost_center: DF.Link | None
		credit: DF.Currency
		credit_in_account_currency: DF.Currency
		credit_in_reporting_currency: DF.Currency
		debit: DF.Currency
		debit_in_account_currency: DF.Currency
		debit_in_reporting_currency: DF.Currency
		finance_book: DF.Link | None
		is_period_closing_voucher_entry: DF.Check
		period_closing_voucher: DF.Link | None
		project: DF.Link | None
		reporting_currency_exchange_rate: DF.Float
	# end: auto-generated types

	pass


def make_closing_entries(closing_entries, voucher_name, company, closing_date):
	accounting_dimensions = get_accounting_dimensions()

	previous_closing_entries = get_previous_closing_entries(company, closing_date, accounting_dimensions)
	combined_entries = closing_entries + previous_closing_entries

	merged_entries = aggregate_with_last_account_closing_balance(combined_entries, accounting_dimensions)
	if not merged_entries:
		return

	# one row per dimension combination can run into lakhs; inserting them one
	# by one exceeds the write limit of a single transaction
	exchange_rate = get_reporting_currency_exchange_rate(company, closing_date)
	timestamp = now()
	rows = [
		get_closing_balance_row(value, voucher_name, closing_date, exchange_rate, timestamp)
		for value in merged_entries.values()
	]
	frappe.db.bulk_insert(
		"Account Closing Balance",
		fields=list(rows[0]),
		values=[tuple(row.values()) for row in rows],
		chunk_size=10_000,
	)


def get_closing_balance_row(value, voucher_name, closing_date, exchange_rate, timestamp):
	"""Return the row that `Document.submit` would have written.

	The validate hooks still run, so app hooks and Server Scripts see each row; only the write is batched.
	"""
	cle = frappe.new_doc("Account Closing Balance")
	cle.update(value)
	cle.update(value["dimensions"])
	cle.update(
		{
			"period_closing_voucher": voucher_name,
			"closing_date": closing_date,
			"docstatus": DocStatus.SUBMITTED,
			"owner": frappe.session.user,
			"modified_by": frappe.session.user,
			"creation": timestamp,
			"modified": timestamp,
		}
	)
	if exchange_rate:
		set_amount_with_exchange_rate(cle, exchange_rate)
	cle.run_method("validate")
	cle.set_new_name()
	return cle.get_valid_dict(convert_dates_to_str=True, ignore_virtual=True)


def aggregate_with_last_account_closing_balance(entries, accounting_dimensions):
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
		cstr(entry.get("account")),
		cstr(entry.get("account_currency")),
		cstr(entry.get("cost_center")),
		cstr(entry.get("project")),
		cstr(entry.get("finance_book")),
		cint(entry.get("is_period_closing_voucher_entry")),
	]

	key_values = {
		"company": cstr(entry.get("company")),
		"account": cstr(entry.get("account")),
		"account_currency": cstr(entry.get("account_currency")),
		"cost_center": cstr(entry.get("cost_center")),
		"project": cstr(entry.get("project")),
		"finance_book": cstr(entry.get("finance_book")),
		"is_period_closing_voucher_entry": cint(entry.get("is_period_closing_voucher_entry")),
	}
	for dimension in accounting_dimensions:
		key.append(cstr(entry.get(dimension)))
		key_values[dimension] = cstr(entry.get(dimension))

	return tuple(key), key_values


def get_previous_closing_entries(company, closing_date, accounting_dimensions):
	entries = []
	last_period_closing_voucher = frappe.db.get_all(
		"Period Closing Voucher",
		filters={"docstatus": 1, "company": company, "period_end_date": ("<", closing_date)},
		fields=["name"],
		order_by="period_end_date desc",
		limit=1,
	)

	if last_period_closing_voucher:
		account_closing_balance = frappe.qb.DocType("Account Closing Balance")
		query = frappe.qb.from_(account_closing_balance).select(
			account_closing_balance.company,
			account_closing_balance.account,
			account_closing_balance.account_currency,
			account_closing_balance.debit,
			account_closing_balance.credit,
			account_closing_balance.debit_in_account_currency,
			account_closing_balance.credit_in_account_currency,
			account_closing_balance.cost_center,
			account_closing_balance.project,
			account_closing_balance.finance_book,
			account_closing_balance.is_period_closing_voucher_entry,
		)

		for dimension in accounting_dimensions:
			query = query.select(account_closing_balance[dimension])

		query = query.where(
			account_closing_balance.period_closing_voucher == last_period_closing_voucher[0].name
		)
		entries = query.run(as_dict=1)

	return entries


def set_amount_in_reporting_currency(cle, company, closing_date):
	if exchange_rate := get_reporting_currency_exchange_rate(company, closing_date):
		set_amount_with_exchange_rate(cle, exchange_rate)


def get_reporting_currency_exchange_rate(company, closing_date):
	default_currency, reporting_currency = frappe.get_cached_value(
		"Company", company, ["default_currency", "reporting_currency"]
	)

	if not reporting_currency:
		return

	reporting_currency_exchange_rate = get_exchange_rate(default_currency, reporting_currency, closing_date)
	if not reporting_currency_exchange_rate:
		frappe.throw(
			title=_("Reporting Currency Exchange Not Found"),
			msg=_(
				"Unable to find exchange rate for {0} to {1} for key date {2}. Please create a Currency Exchange record manually."
			).format(default_currency, reporting_currency, closing_date),
			exc=ReportingCurrencyExchangeNotFoundError,
		)

	return reporting_currency_exchange_rate


def set_amount_with_exchange_rate(cle, reporting_currency_exchange_rate):
	debit_in_reporting_currency = flt(cle.get("debit", 0) * reporting_currency_exchange_rate)
	credit_in_reporting_currency = flt(cle.get("credit", 0) * reporting_currency_exchange_rate)

	cle.update(
		{
			"reporting_currency_exchange_rate": reporting_currency_exchange_rate,
			"debit_in_reporting_currency": debit_in_reporting_currency,
			"credit_in_reporting_currency": credit_in_reporting_currency,
		}
	)
