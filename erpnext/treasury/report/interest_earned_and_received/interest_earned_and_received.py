# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

import erpnext
from erpnext.treasury.doctype.investment_transaction.investment_transaction import PURCHASE_TYPES
from erpnext.treasury.interest import INTEREST_CLASSES
from erpnext.treasury.report.utils import (
	add_total_row,
	get_balances,
	get_currency_column,
	get_investment_columns,
	get_investments,
	get_ledger_movements,
	sum_movements,
)

AMOUNT_FIELDS = (
	"opening_receivable",
	"interest_accrued",
	"interest_bought",
	"interest_received",
	"closing_receivable",
	"amortisation",
	"interest_income",
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	investments = [i for i in get_investments(filters) if i.instrument_class in INTEREST_CLASSES]
	movements = get_ledger_movements(filters.company, filters.to_date, [i.name for i in investments])
	opening = get_balances(movements, "accrued_interest_account", add_days(filters.from_date, -1))
	period_movements = [m for m in movements if m.posting_date >= getdate(filters.from_date)]
	currency = erpnext.get_company_currency(filters.company)

	data = []
	for investment in investments:
		row = get_row(investment, flt(opening.get(investment.name)), period_movements, currency)
		if any(row.get(f) for f in AMOUNT_FIELDS):
			data.append(row)

	chart = get_chart(data)
	if data:
		add_total_row(data, AMOUNT_FIELDS, "investment", currency)

	return get_columns(), data, None, chart


def get_row(investment, opening_receivable, movements, currency):
	"""Interest receivable roll-forward: opening + accrued + bought with purchases - received = closing."""
	movements = [m for m in movements if m.investment == investment.name]
	row = frappe._dict(
		investment=investment.name,
		investment_type=investment.investment_type,
		issuer=investment.issuer,
		rate=flt(investment.rate_of_interest or investment.coupon_rate),
		currency=currency,
		opening_receivable=opening_receivable,
		interest_accrued=sum_movements(movements, "accrued_interest_account", ("Interest Accrual",)),
		interest_bought=sum_movements(movements, "accrued_interest_account", PURCHASE_TYPES),
		interest_received=-sum_movements(movements, "accrued_interest_account", ("Interest Receipt",)),
		amortisation=sum_movements(movements, "investment_account", ("Interest Accrual",)),
		interest_income=-sum_movements(movements, "interest_income_account"),
	)
	row.closing_receivable = opening_receivable + sum_movements(movements, "accrued_interest_account")

	return row


def get_columns():
	return [
		*get_investment_columns(),
		{"label": _("Rate %"), "fieldname": "rate", "fieldtype": "Percent", "width": 80},
		get_currency_column(_("Opening Receivable"), "opening_receivable", 140),
		get_currency_column(_("Interest Accrued"), "interest_accrued"),
		get_currency_column(_("Interest Bought"), "interest_bought"),
		get_currency_column(_("Interest Received"), "interest_received"),
		get_currency_column(_("Closing Receivable"), "closing_receivable", 140),
		get_currency_column(_("Amortisation"), "amortisation"),
		get_currency_column(_("Interest Income"), "interest_income"),
	]


def get_chart(data):
	"""Interest earned next to interest actually received, per investment."""
	return {
		"data": {
			"labels": [row.investment for row in data],
			"datasets": [
				{"name": _("Interest Earned"), "values": [flt(row.interest_income) for row in data]},
				{"name": _("Interest Received"), "values": [flt(row.interest_received) for row in data]},
			],
		},
		"type": "bar",
		"fieldtype": "Currency",
	}
