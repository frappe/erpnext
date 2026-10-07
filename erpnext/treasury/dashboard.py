# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import add_months, flt, formatdate, get_last_day, nowdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.treasury.ledger import get_investment_gl_query

HELD_STATUSES = ("Active", "Partially Redeemed")


@frappe.whitelist()
def get_realised_gain_loss(filters: str | dict | None = None) -> dict:
	"""Number card: gain (positive) or loss booked on exits in the current fiscal year."""
	return get_fiscal_year_income(filters, "realised_gain_loss_account")


@frappe.whitelist()
def get_interest_earned(filters: str | dict | None = None) -> dict:
	"""Number card: interest income, including bond amortisation, booked in the current fiscal year."""
	return get_fiscal_year_income(filters, "interest_income_account")


def get_fiscal_year_income(filters, account_field):
	frappe.has_permission("Investment Transaction", throw=True)
	company = get_company(filters)
	fiscal_year = get_fiscal_year(nowdate(), company=company, as_dict=True)
	query = get_income_query(company, account_field, fiscal_year.year_start_date, fiscal_year.year_end_date)

	return {"value": flt(query.run()[0][0]), "fieldtype": "Currency"}


def get_company(filters):
	filters = frappe.parse_json(filters) or {}
	return filters.get("company") or frappe.defaults.get_user_default("Company")


def get_income_query(company, account_field, from_date, to_date):
	"""Income in each investment's own `account_field` account, so others' entries there are left out."""
	ledger = get_investment_gl_query()
	gl_entry = ledger.gl_entry
	investment = frappe.qb.DocType("Investment")

	return (
		ledger.query.join(investment)
		.on(ledger.investment == investment.name)
		.select(Sum(gl_entry.credit) - Sum(gl_entry.debit))
		.where(gl_entry.account == investment[account_field])
		.where(gl_entry.is_cancelled == 0)
		.where(gl_entry.company == company)
		.where(gl_entry.posting_date.between(from_date, to_date))
	)


def get_month_ends(start_date, count):
	"""Last day of `count` consecutive months, starting with the month of `start_date`."""
	return [get_last_day(add_months(start_date, i)) for i in range(count)]


def get_monthly_chart(month_ends, rows, dataset_name, chart_type):
	"""Chart data with one point per month; `rows` are (date, amount) pairs."""
	totals = dict.fromkeys(month_ends, 0)
	for date, amount in rows:
		totals[get_last_day(date)] += flt(amount)

	return {
		"labels": [formatdate(month_end, "MMM YYYY") for month_end in month_ends],
		"datasets": [{"name": dataset_name, "values": list(totals.values())}],
		"type": chart_type,
	}
