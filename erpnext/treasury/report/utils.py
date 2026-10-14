# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Building blocks shared by the Treasury reports. All amounts are in company currency."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, getdate

import erpnext
from erpnext.treasury.dashboard import validate_company_permission
from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
	EXIT_TYPES,
	PURCHASE_TYPES,
	UNIT_CLASSES,
)
from erpnext.treasury.ledger import get_investment_gl_query

# accounts the reports read, in priority order: the first match wins when two share an account
ACCOUNT_ROLES = (
	"investment_account",
	"accrued_interest_account",
	"interest_income_account",
	"dividend_income_account",
	"realised_gain_loss_account",
	"charges_account",
)
# company accounts investment vouchers also post to, so exchange gains count in returns
COMPANY_ACCOUNT_ROLES = ("exchange_gain_loss_account",)


def parse_filters(filters):
	"""Report filters, once the user is known to have access to the company asked for."""
	filters = frappe._dict(filters or {})
	validate_company_permission(filters.company)
	return filters


def get_investments(filters):
	"""Submitted investments of the company, narrowed by the common report filters."""
	conditions = {"company": filters.company, "docstatus": 1}
	for fieldname in ("investment_type", "issuer", "investment"):
		if filters.get(fieldname):
			conditions["name" if fieldname == "investment" else fieldname] = filters.get(fieldname)

	return frappe.get_all(
		"Investment",
		filters=conditions,
		fields=[
			"name",
			"investment_type",
			"instrument_class",
			"issuer",
			"currency as investment_currency",
			"purchase_date",
			"maturity_date",
			"rate_of_interest",
			"coupon_rate",
			"face_value",
			"status",
		],
		order_by="name",
	)


def get_ledger_movements(company, to_date, investments):
	"""GL movements (debit minus credit) of each investment's accounts up to `to_date`, tagged by role."""
	if not investments:
		return []

	ledger = get_investment_gl_query()
	gl_entry = ledger.gl_entry
	investment = frappe.qb.DocType("Investment")
	company_doc = frappe.qb.DocType("Company")
	role_accounts = [(investment[fieldname], fieldname) for fieldname in ACCOUNT_ROLES]
	role_accounts += [(company_doc[fieldname], fieldname) for fieldname in COMPANY_ACCOUNT_ROLES]

	role = Case()
	for account, fieldname in role_accounts:
		role = role.when(gl_entry.account == account, fieldname)

	return (
		ledger.query.join(investment)
		.on(ledger.investment == investment.name)
		.join(company_doc)
		.on(gl_entry.company == company_doc.name)
		.select(
			ledger.investment.as_("investment"),
			ledger.transaction_type.as_("transaction_type"),
			role.as_("role"),
			gl_entry.posting_date,
			(gl_entry.debit - gl_entry.credit).as_("amount"),
		)
		.where(gl_entry.is_cancelled == 0)
		.where(gl_entry.company == company)
		.where(gl_entry.posting_date <= to_date)
		.where(ledger.investment.isin(investments))
		.where(Criterion.any([gl_entry.account == account for account, _fieldname in role_accounts]))
	).run(as_dict=True)


def get_balances(movements, role, upto=None):
	"""Balance of one account role per investment, optionally up to (and including) a date."""
	balances = defaultdict(float)
	for row in movements:
		if row.role == role and (not upto or row.posting_date <= getdate(upto)):
			balances[row.investment] += flt(row.amount)

	return balances


def sum_movements(movements, role, transaction_types=None):
	"""Movements of one account role, optionally only those of some transaction types."""
	return sum(
		flt(m.amount)
		for m in movements
		if m.role == role and (not transaction_types or m.transaction_type in transaction_types)
	)


def get_unrealised_gain_loss(investments, as_on_date=None):
	"""Unrealised gain or loss of each investment on the date, in company currency.

	Where revaluations post to the ledger, it is the fair value adjustment still on the books, which
	sales take off. Otherwise it is the latest revaluation's figure for the share of its units still held.
	"""
	if not investments:
		return {}

	revaluation = frappe.qb.DocType("Investment Revaluation")
	row = frappe.qb.DocType("Investment Revaluation Detail")
	query = (
		frappe.qb.from_(row)
		.join(revaluation)
		.on(row.parent == revaluation.name)
		.select(
			row.investment,
			row.unrealised_gain_loss,
			row.units_held,
			row.posts_to_ledger,
			revaluation.revaluation_date,
		)
		.where(row.parenttype == "Investment Revaluation")
		.where(row.investment.isin(investments))
		.where(revaluation.docstatus == 1)
		.orderby(revaluation.revaluation_date)
		.orderby(revaluation.creation)
	)
	if as_on_date:
		query = query.where(revaluation.revaluation_date <= as_on_date)

	# later rows overwrite earlier ones, leaving the latest per investment
	latest_rows = {r.investment: r for r in query.run(as_dict=True)}
	fair_values = get_fair_value_balances(list(latest_rows), as_on_date)

	unrealised = {}
	for investment, latest in latest_rows.items():
		if cint(latest.posts_to_ledger):
			unrealised[investment] = flt(fair_values.get(investment))
		elif flt(latest.units_held):
			# exits take the oldest units first, so they take the valued units before any bought later
			units_exited = get_units_exited(investment, latest.revaluation_date, as_on_date)
			valued_units_left = max(flt(latest.units_held) - units_exited, 0)
			unrealised[investment] = (
				flt(latest.unrealised_gain_loss) * valued_units_left / flt(latest.units_held)
			)

	return unrealised


def get_units_exited(investment, after_date, upto=None):
	"""Units that left the investment after a date, optionally up to another.

	A revaluation values the units held at the end of its date, and units cannot move on that date once
	it is made, so exits after the date are exactly those it did not see.
	"""
	transaction = frappe.qb.DocType("Investment Transaction")
	query = (
		frappe.qb.from_(transaction)
		.select(Sum(transaction.units))
		.where(transaction.investment == investment)
		.where(transaction.docstatus == 1)
		.where(transaction.transaction_type.isin(EXIT_TYPES))
		.where(transaction.posting_date > after_date)
	)
	if upto:
		query = query.where(transaction.posting_date <= upto)

	return flt(query.run()[0][0])


def get_fair_value_balances(investments, as_on_date=None):
	"""Balance of each investment's Fair Value Adjustment Account, up to the date."""
	if not investments:
		return {}

	ledger = get_investment_gl_query(include_revaluations=True)
	gl_entry = ledger.gl_entry
	investment = frappe.qb.DocType("Investment")
	query = (
		ledger.query.join(investment)
		.on(ledger.investment == investment.name)
		.select(ledger.investment, Sum(gl_entry.debit) - Sum(gl_entry.credit))
		.where(gl_entry.account == investment.fair_value_adjustment_account)
		.where(gl_entry.is_cancelled == 0)
		.where(ledger.investment.isin(investments))
		.groupby(ledger.investment)
	)
	if as_on_date:
		query = query.where(gl_entry.posting_date <= as_on_date)

	return dict(query.run())


def get_units_held(investments, as_on_date):
	"""Units bought minus units sold up to the date, for unit-based instruments."""
	if not investments:
		return {}

	units = defaultdict(float)
	for transaction in frappe.get_all(
		"Investment Transaction",
		filters={
			"investment": ("in", investments),
			"instrument_class": ("in", UNIT_CLASSES),
			"docstatus": 1,
			"posting_date": ("<=", as_on_date),
			"transaction_type": ("in", PURCHASE_TYPES + EXIT_TYPES),
		},
		fields=["investment", "transaction_type", "units"],
	):
		sign = -1 if transaction.transaction_type in EXIT_TYPES else 1
		units[transaction.investment] += sign * flt(transaction.units)

	return units


def get_positions(filters, as_on_date):
	"""Positions as they stood on the date, so reports can be run for any past day."""
	investments = get_investments(filters)
	names = [investment.name for investment in investments]
	movements = get_ledger_movements(filters.company, as_on_date, names)
	book_values = get_balances(movements, "investment_account")
	accrued_interest = get_balances(movements, "accrued_interest_account")
	unrealised = get_unrealised_gain_loss(names, as_on_date)
	units = get_units_held(names, as_on_date)

	currency = erpnext.get_company_currency(filters.company)
	positions = []
	for investment in investments:
		position = get_position(investment, book_values, accrued_interest, unrealised, units)
		if position.book_value or position.accrued_interest or position.unrealised_gain_loss:
			positions.append(position.update(currency=currency))

	return positions


def get_position(investment, book_values, accrued_interest, unrealised, units):
	position = frappe._dict(investment, investment=investment.name)
	position.rate = flt(investment.rate_of_interest or investment.coupon_rate)
	position.units = flt(units.get(investment.name))
	position.book_value = flt(book_values.get(investment.name))
	position.accrued_interest = flt(accrued_interest.get(investment.name))
	position.unrealised_gain_loss = flt(unrealised.get(investment.name))
	position.market_value = position.book_value + position.unrealised_gain_loss

	return position


def add_total_row(data, fieldnames, label_field, currency):
	total = frappe._dict({"bold": 1, label_field: _("Total"), "currency": currency})
	for fieldname in fieldnames:
		total[fieldname] = sum(flt(row.get(fieldname)) for row in data)

	data.append(total)


def set_share_of_total(rows, value_field, share_field="share"):
	total = sum(flt(row.get(value_field)) for row in rows)
	for row in rows:
		row[share_field] = flt(row.get(value_field)) * 100 / total if total else 0


def get_investment_columns():
	"""Columns that identify an investment, shared by the per-investment reports."""
	return [
		{
			"label": _("Investment"),
			"fieldname": "investment",
			"fieldtype": "Link",
			"options": "Investment",
			"width": 170,
		},
		{
			"label": _("Investment Type"),
			"fieldname": "investment_type",
			"fieldtype": "Link",
			"options": "Investment Type",
			"width": 130,
		},
		{
			"label": _("Issuer"),
			"fieldname": "issuer",
			"fieldtype": "Link",
			"options": "Financial Institution",
			"width": 140,
		},
	]


def get_currency_column(label, fieldname, width=130):
	"""Amount column in company currency; every row carries the currency in its `currency` field."""
	return {
		"label": label,
		"fieldname": fieldname,
		"fieldtype": "Currency",
		"options": "currency",
		"width": width,
	}
