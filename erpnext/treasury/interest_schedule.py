# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

"""Estimated vs actual interest per period, so the user sees where the bank paid a different amount."""

import frappe
from frappe.utils import add_days, date_diff, flt, getdate

from erpnext.treasury.interest import InterestCalculator


# Rebuild an investment's Interest Schedule; called when principal changes or an accrual is posted.
def update_interest_schedule(investment_name):
	investment = frappe.get_doc("Investment", investment_name)
	calculator = InterestCalculator(investment)
	accruals = get_submitted_accruals(investment_name)
	accrued_upto = max((getdate(accrual.to_date) for accrual in accruals), default=None)

	rows = get_schedule_rows(calculator, accruals, accrued_upto)
	investment.set_interest_schedule(rows, accrued_upto)


def get_schedule_rows(calculator, accruals, accrued_upto):
	precision = get_amount_precision()
	rows = [
		frappe._dict(period_from=start, period_to=add_days(end, -1), actual_interest=0)
		for start, end in calculator.get_schedule_periods()
	]
	allocate_accruals(rows, accruals, precision)

	for row in rows:
		row.status = get_period_status(row, accrued_upto)

	set_estimated_interest(calculator, rows, precision)
	set_amortisation(calculator, rows)

	return [row for row in rows if row.estimated_interest or row.actual_interest or row.amortisation_amount]


def allocate_accruals(rows, accruals, precision):
	"""Spread each accrual over the periods it covers by days, since an accrual can span any range."""
	for accrual in accruals:
		total_days = date_diff(accrual.to_date, accrual.from_date) + 1
		covered_days, allocated = 0, 0
		for row in rows:
			days = get_overlap_days(row.period_from, row.period_to, accrual.from_date, accrual.to_date)
			if not days:
				continue

			covered_days += days
			share = flt(flt(accrual.interest_amount) * covered_days / total_days, precision) - allocated
			allocated += share
			row.actual_interest = flt(row.actual_interest + share, precision)
			row.interest_accrual = accrual.name


def get_overlap_days(from_date, to_date, other_from_date, other_to_date):
	"""Days (both ends included) that two date ranges have in common."""
	start = max(getdate(from_date), getdate(other_from_date))
	end = min(getdate(to_date), getdate(other_to_date))

	return max(date_diff(end, start) + 1, 0)


def get_period_status(row, accrued_upto):
	if not accrued_upto or accrued_upto < getdate(row.period_from):
		return "Pending"

	if accrued_upto < getdate(row.period_to):
		return "Partially Accrued"

	return "Accrued"


def set_estimated_interest(calculator, rows, precision):
	"""Compound on actual interest where known, so later estimates follow what the bank credited."""
	compounded_interest = 0
	for row in rows:
		end = add_days(row.period_to, 1)
		row.estimated_interest = flt(
			calculator.get_interest(row.period_from, end, compounded_interest), precision
		)
		is_accrued = row.status == "Accrued"
		row.variance = flt(row.actual_interest - row.estimated_interest, precision) if is_accrued else 0

		if calculator.compounds:
			compounded_interest += row.actual_interest if is_accrued else row.estimated_interest


def set_amortisation(calculator, rows):
	"""Rounded as a running total, so the rows add up to exactly the whole premium / discount."""
	precision, running, previous = get_amount_precision(), 0, 0
	for row in rows:
		running += calculator.get_amortisation(row.period_from, add_days(row.period_to, 1))
		rounded = flt(running, precision)
		row.amortisation_amount, previous = rounded - previous, rounded


def get_rounded_amortisation(calculator, start, end):
	"""Rounded as a running total, so the pieces add up to exactly the whole premium / discount."""
	first_date, precision = calculator.get_start_date(), get_amount_precision()
	return flt(calculator.get_amortisation(first_date, end), precision) - flt(
		calculator.get_amortisation(first_date, start), precision
	)


def get_estimated_interest(investment_name, from_date, to_date):
	"""Estimated interest of a date range, taken from the schedule periods it overlaps by days."""
	estimate = 0
	for row in get_schedule(investment_name):
		days = get_overlap_days(row.period_from, row.period_to, from_date, to_date)
		if days:
			period_days = date_diff(row.period_to, row.period_from) + 1
			estimate += flt(row.estimated_interest) * days / period_days

	return flt(estimate, get_amount_precision())


def get_schedule(investment_name):
	return frappe.get_all(
		"Investment Interest Schedule",
		filters={"parent": investment_name, "parenttype": "Investment", "parentfield": "interest_schedule"},
		fields=["period_from", "period_to", "estimated_interest", "actual_interest", "status"],
		order_by="idx asc",
	)


def get_submitted_accruals(investment_name):
	return frappe.get_all(
		"Investment Interest Accrual",
		filters={"investment": investment_name, "docstatus": 1},
		fields=["name", "from_date", "to_date", "interest_amount"],
		order_by="from_date asc",
	)


def get_amount_precision():
	return frappe.get_precision("Investment Interest Accrual", "interest_amount")
