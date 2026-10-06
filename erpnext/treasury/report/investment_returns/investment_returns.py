# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate

import erpnext
from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
	EXIT_TYPES,
	PURCHASE_TYPES,
)
from erpnext.treasury.report.utils import (
	add_total_row,
	get_balances,
	get_currency_column,
	get_investment_columns,
	get_investments,
	get_ledger_movements,
	get_unrealised_gain_loss,
	sum_movements,
)

AMOUNT_FIELDS = (
	"opening_book_value",
	"purchases",
	"exits",
	"closing_book_value",
	"average_invested",
	"interest_income",
	"dividend_income",
	"realised_gain_loss",
	"exchange_gain_loss",
	"unrealised_change",
	"charges",
	"total_return",
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	investments = get_investments(filters)
	names = [investment.name for investment in investments]
	movements = get_ledger_movements(filters.company, filters.to_date, names)
	context = get_context(filters, names, movements)

	data = [get_row(investment, filters, context) for investment in investments]
	data = [row for row in data if any(row.get(f) for f in AMOUNT_FIELDS)]
	chart = get_chart(data)
	if data:
		add_total_row(data, AMOUNT_FIELDS, "investment", data[0].currency)
		set_returns(data[-1], filters)

	return get_columns(), data, None, chart


def get_context(filters, names, movements):
	day_before = add_days(filters.from_date, -1)
	return frappe._dict(
		currency=erpnext.get_company_currency(filters.company),
		opening=get_balances(movements, "investment_account", day_before),
		closing=get_balances(movements, "investment_account"),
		unrealised_opening=get_unrealised_gain_loss(names, day_before),
		unrealised_closing=get_unrealised_gain_loss(names, filters.to_date),
		period_movements=[m for m in movements if m.posting_date >= getdate(filters.from_date)],
	)


def get_row(investment, filters, context):
	movements = [m for m in context.period_movements if m.investment == investment.name]
	row = frappe._dict(
		investment=investment.name,
		investment_type=investment.investment_type,
		issuer=investment.issuer,
		currency=context.currency,
		opening_book_value=flt(context.opening.get(investment.name)),
		closing_book_value=flt(context.closing.get(investment.name)),
		purchases=sum_movements(movements, "investment_account", PURCHASE_TYPES),
		exits=-sum_movements(movements, "investment_account", EXIT_TYPES),
		# income and gains are credits, so their sign is flipped
		interest_income=-sum_movements(movements, "interest_income_account"),
		dividend_income=-sum_movements(movements, "dividend_income_account"),
		realised_gain_loss=-sum_movements(movements, "realised_gain_loss_account"),
		exchange_gain_loss=-sum_movements(movements, "exchange_gain_loss_account"),
		charges=sum_movements(movements, "charges_account"),
		unrealised_change=flt(context.unrealised_closing.get(investment.name))
		- flt(context.unrealised_opening.get(investment.name)),
	)
	row.average_invested = get_average_invested(row.opening_book_value, movements, filters)
	row.total_return = (
		row.interest_income
		+ row.dividend_income
		+ row.realised_gain_loss
		+ row.exchange_gain_loss
		+ row.unrealised_change
		- row.charges
	)
	set_returns(row, filters)

	return row


def get_average_invested(opening_book_value, movements, filters):
	"""Book value averaged over the days of the period: each movement counts for the days it was held."""
	days = date_diff(filters.to_date, filters.from_date) + 1
	weighted = sum(
		flt(m.amount) * (date_diff(filters.to_date, m.posting_date) + 1)
		for m in movements
		if m.role == "investment_account"
	)

	return opening_book_value + weighted / days


def set_returns(row, filters):
	"""Return on the average amount invested, and the same rate scaled to a full year."""
	days = date_diff(filters.to_date, filters.from_date) + 1
	row.return_percent = flt(row.total_return) * 100 / row.average_invested if row.average_invested > 0 else 0
	row.annualised_return = row.return_percent * 365 / days


def get_columns():
	return [
		*get_investment_columns(),
		get_currency_column(_("Opening Book Value"), "opening_book_value", 140),
		get_currency_column(_("Purchases"), "purchases"),
		get_currency_column(_("Exits (at Cost)"), "exits"),
		get_currency_column(_("Closing Book Value"), "closing_book_value", 140),
		get_currency_column(_("Average Invested"), "average_invested", 140),
		get_currency_column(_("Interest Income"), "interest_income"),
		get_currency_column(_("Dividend Income"), "dividend_income"),
		get_currency_column(_("Realised Gain / Loss"), "realised_gain_loss", 140),
		get_currency_column(_("Exchange Gain / Loss"), "exchange_gain_loss", 140),
		get_currency_column(_("Unrealised Gain / Loss Change"), "unrealised_change", 170),
		get_currency_column(_("Charges"), "charges", 110),
		get_currency_column(_("Total Return"), "total_return"),
		{"label": _("Return %"), "fieldname": "return_percent", "fieldtype": "Percent", "width": 100},
		{
			"label": _("Annualised Return %"),
			"fieldname": "annualised_return",
			"fieldtype": "Percent",
			"width": 140,
		},
	]


def get_chart(data):
	"""Where each investment's return came from, stacked; charges show below zero."""
	sources = (
		(_("Interest Income"), "interest_income", 1),
		(_("Dividend Income"), "dividend_income", 1),
		(_("Realised Gain / Loss"), "realised_gain_loss", 1),
		(_("Exchange Gain / Loss"), "exchange_gain_loss", 1),
		(_("Unrealised Gain / Loss Change"), "unrealised_change", 1),
		(_("Charges"), "charges", -1),
	)
	datasets = [
		{"name": label, "values": [sign * flt(row.get(fieldname)) or 0 for row in data]}
		for label, fieldname, sign in sources
		if any(row.get(fieldname) for row in data)
	]

	return {
		"data": {"labels": [row.investment for row in data], "datasets": datasets},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"fieldtype": "Currency",
	}
