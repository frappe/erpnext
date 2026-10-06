# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.treasury.report.utils import (
	add_total_row,
	get_currency_column,
	get_positions,
	set_share_of_total,
)

AMOUNT_FIELDS = ("book_value", "accrued_interest", "exposure", "market_value")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_exposures(get_positions(filters, filters.as_on_date))
	set_share_of_total(data, "exposure")
	chart = get_chart(data)

	if data:
		add_total_row(data, (*AMOUNT_FIELDS, "investments", "share"), "issuer", data[0].currency)

	return get_columns(), data, None, chart


def get_exposures(positions):
	"""Positions summed per issuer; exposure is what the issuer owes: book value plus accrued interest."""
	exposures = {}
	for position in positions:
		exposure = exposures.setdefault(
			position.issuer,
			frappe._dict(
				issuer=position.issuer,
				currency=position.currency,
				investments=0,
				**dict.fromkeys(AMOUNT_FIELDS, 0),
			),
		)
		exposure.investments += 1
		exposure.book_value += flt(position.book_value)
		exposure.accrued_interest += flt(position.accrued_interest)
		exposure.exposure += flt(position.book_value) + flt(position.accrued_interest)
		exposure.market_value += flt(position.market_value)

	set_institution_details(exposures)
	return sorted(exposures.values(), key=lambda row: row.exposure, reverse=True)


def set_institution_details(exposures):
	institutions = frappe.get_all(
		"Financial Institution",
		filters={"name": ("in", list(exposures))},
		fields=["name", "institution_type", "country"],
	)
	for institution in institutions:
		exposures[institution.name].update(
			institution_type=institution.institution_type, country=institution.country
		)


def get_chart(data):
	return {
		"data": {
			"labels": [row.issuer for row in data],
			"datasets": [{"name": _("Exposure"), "values": [flt(row.exposure, 0) for row in data]}],
		},
		"type": "pie",
	}


def get_columns():
	return [
		{
			"label": _("Issuer"),
			"fieldname": "issuer",
			"fieldtype": "Link",
			"options": "Financial Institution",
			"width": 180,
		},
		{"label": _("Institution Type"), "fieldname": "institution_type", "fieldtype": "Data", "width": 120},
		{
			"label": _("Country"),
			"fieldname": "country",
			"fieldtype": "Link",
			"options": "Country",
			"width": 100,
		},
		{"label": _("Investments"), "fieldname": "investments", "fieldtype": "Int", "width": 100},
		get_currency_column(_("Book Value"), "book_value"),
		get_currency_column(_("Accrued Interest"), "accrued_interest"),
		get_currency_column(_("Total Exposure"), "exposure"),
		get_currency_column(_("Market Value"), "market_value"),
		{"label": _("% of Total Exposure"), "fieldname": "share", "fieldtype": "Percent", "width": 140},
	]
