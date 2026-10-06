# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, flt

from erpnext.treasury.report.utils import (
	add_total_row,
	get_currency_column,
	get_investment_columns,
	get_positions,
)

# upper limit in days to maturity of each bucket; a negative count means the maturity date has passed
BUCKET_LIMITS = (-1, 30, 90, 180, 365)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = [row for row in get_positions(filters, filters.as_on_date) if row.maturity_date]
	labels = get_bucket_labels()
	for row in data:
		row.days_to_maturity = date_diff(row.maturity_date, filters.as_on_date)
		row.bucket = get_bucket(row.days_to_maturity, labels)
		row.total = flt(row.book_value) + flt(row.accrued_interest)

	data.sort(key=lambda row: row.maturity_date)
	chart = get_chart(data, labels)
	if data:
		add_total_row(data, ("book_value", "accrued_interest", "total"), "investment", data[0].currency)

	return get_columns(), data, None, chart


def get_bucket_labels():
	"""One label per bucket limit, then one for anything later."""
	return [
		_("Overdue"),
		_("0-30 Days"),
		_("31-90 Days"),
		_("91-180 Days"),
		_("181-365 Days"),
		_("Over 1 Year"),
	]


def get_bucket(days_to_maturity, labels):
	index = next(
		(i for i, limit in enumerate(BUCKET_LIMITS) if days_to_maturity <= limit), len(BUCKET_LIMITS)
	)
	return labels[index]


def get_chart(data, labels):
	"""Book value maturing in each bucket, in bucket order."""
	totals = dict.fromkeys(labels, 0)
	for row in data:
		totals[row.bucket] += flt(row.book_value)

	return {
		"data": {"labels": labels, "datasets": [{"name": _("Book Value"), "values": list(totals.values())}]},
		"type": "bar",
		"fieldtype": "Currency",
	}


def get_columns():
	return [
		*get_investment_columns(),
		{"label": _("Maturity Date"), "fieldname": "maturity_date", "fieldtype": "Date", "width": 105},
		{"label": _("Days to Maturity"), "fieldname": "days_to_maturity", "fieldtype": "Int", "width": 120},
		{"label": _("Maturity Bucket"), "fieldname": "bucket", "fieldtype": "Data", "width": 120},
		{"label": _("Rate %"), "fieldname": "rate", "fieldtype": "Percent", "width": 80},
		get_currency_column(_("Book Value"), "book_value"),
		get_currency_column(_("Accrued Interest"), "accrued_interest"),
		get_currency_column(_("Total"), "total"),
	]
