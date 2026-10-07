# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.treasury.report.utils import (
	add_total_row,
	get_currency_column,
	get_investment_columns,
	get_positions,
	set_share_of_total,
)

AMOUNT_FIELDS = ("book_value", "accrued_interest", "unrealised_gain_loss", "market_value")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_positions(filters, filters.as_on_date)
	set_share_of_total(data, "market_value")
	chart = get_chart(data)

	if data:
		add_total_row(data, (*AMOUNT_FIELDS, "share"), "investment", data[0].currency)

	return get_columns(), data, None, chart


def get_chart(data):
	"""Market value per investment type."""
	totals = {}
	for row in data:
		totals[row.investment_type] = totals.get(row.investment_type, 0) + row.market_value

	return {
		"data": {
			"labels": list(totals),
			"datasets": [{"name": _("Market Value"), "values": [flt(value, 0) for value in totals.values()]}],
		},
		"type": "donut",
	}


def get_columns():
	return [
		*get_investment_columns(),
		{"label": _("Instrument"), "fieldname": "instrument_class", "fieldtype": "Data", "width": 90},
		{"label": _("Purchase Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 105},
		{"label": _("Maturity Date"), "fieldname": "maturity_date", "fieldtype": "Date", "width": 105},
		{"label": _("Rate %"), "fieldname": "rate", "fieldtype": "Percent", "width": 80},
		{"label": _("Units"), "fieldname": "units", "fieldtype": "Float", "width": 100},
		get_currency_column(_("Book Value"), "book_value"),
		get_currency_column(_("Accrued Interest"), "accrued_interest"),
		get_currency_column(_("Unrealised Gain / Loss"), "unrealised_gain_loss", 150),
		get_currency_column(_("Market Value"), "market_value"),
		{"label": _("% of Portfolio"), "fieldname": "share", "fieldtype": "Percent", "width": 110},
	]
