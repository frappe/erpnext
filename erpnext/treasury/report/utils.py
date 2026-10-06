# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

"""Building blocks shared by the Treasury reports. All amounts are in company currency."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder import Case, Criterion
from frappe.utils import flt, getdate

import erpnext
from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
	EXIT_TYPES,
	PURCHASE_TYPES,
	UNIT_CLASSES,
)
from erpnext.treasury.ledger import get_investment_gl_query

# investment fields holding the ledger accounts the reports read, in matching priority
ACCOUNT_ROLES = (
	"investment_account",
	"accrued_interest_account",
	"interest_income_account",
	"dividend_income_account",
	"realised_gain_loss_account",
	"charges_account",
)
# company fields holding ledger accounts that investment vouchers also post to
COMPANY_ACCOUNT_ROLES = ("exchange_gain_loss_account",)


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


def get_unrealised_gain_loss(investments, as_on_date):
	"""Unrealised gain or loss of each investment per its latest revaluation up to the date."""
	if not investments:
		return {}

	revaluation = frappe.qb.DocType("Investment Revaluation")
	row = frappe.qb.DocType("Investment Revaluation Detail")
	rows = (
		frappe.qb.from_(row)
		.join(revaluation)
		.on(row.parent == revaluation.name)
		.select(row.investment, row.unrealised_gain_loss)
		.where(row.parenttype == "Investment Revaluation")
		.where(row.investment.isin(investments))
		.where(revaluation.docstatus == 1)
		.where(revaluation.revaluation_date <= as_on_date)
		.orderby(revaluation.revaluation_date)
		.orderby(revaluation.creation)
	).run(as_dict=True)

	# later rows overwrite earlier ones, leaving the latest per investment
	return {r.investment: flt(r.unrealised_gain_loss) for r in rows}


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
	"""Each investment still holding a balance on the date, with book value, accrued interest,
	unrealised gain or loss and market value as they stood that day."""
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


def add_total_row(data, fieldnames, label_field, currency, **values):
	"""Append a bold Total row summing `fieldnames`; `values` adds already computed totals."""
	total = frappe._dict({"bold": 1, label_field: _("Total"), "currency": currency, **values})
	for fieldname in fieldnames:
		total.setdefault(fieldname, sum(flt(row.get(fieldname)) for row in data))

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
