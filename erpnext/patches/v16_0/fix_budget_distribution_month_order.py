import frappe
from frappe.query_builder.functions import Max
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)


def execute():
	"""Budgets migrated by migrate_budget_records_to_new_structure got the Monthly Distribution
	percentages in row order from the fiscal year start, so the months moved. Put them back on their
	months, for the budgets whose distribution still has exactly what the migration wrote."""
	if not (
		frappe.db.has_column("Budget", "monthly_distribution")
		and frappe.db.has_column("Budget", "fiscal_year")
	):
		return

	budget = frappe.qb.DocType("Budget")
	dimensions = [d for d in get_accounting_dimensions() if frappe.db.has_column("Budget", d)]
	old_budgets = (
		frappe.qb.from_(budget)
		.select(
			budget.name,
			budget.modified,
			budget.company,
			budget.budget_against,
			budget.cost_center,
			budget.project,
			budget.fiscal_year,
			budget.monthly_distribution,
			*[budget[d] for d in dimensions],
		)
		.where((budget.docstatus == 2) & budget.monthly_distribution.isnotnull())
		.where(budget.monthly_distribution != "")
		.run(as_dict=True)
	)

	for old in old_budgets:
		fix_migrated_budgets(old, dimensions)


def fix_migrated_budgets(old, dimensions=None):
	if not frappe.db.exists("Monthly Distribution", old.monthly_distribution):
		return

	year_start_date = frappe.db.get_value("Fiscal Year", old.fiscal_year, "year_start_date")
	if not year_start_date:
		return

	rows = frappe.get_all(
		"Monthly Distribution Percentage",
		filters={"parent": old.monthly_distribution, "parenttype": "Monthly Distribution"},
		fields=["month", "percentage_allocation"],
		order_by="idx asc",
	)
	# what the migration wrote: the percentages in row order, one row per distribution row
	shifted = [flt(row.percentage_allocation) for row in rows]
	by_month = {row.month: flt(row.percentage_allocation) for row in rows}
	correct = [by_month.get(add_months(year_start_date, i).strftime("%B"), 0) for i in range(12)]
	if not shifted or len(shifted) > 12 or same(shifted, correct):
		return

	filters = {
		"docstatus": ("<", 2),
		"company": old.company,
		"budget_against": old.budget_against,
		"from_fiscal_year": old.fiscal_year,
		"to_fiscal_year": old.fiscal_year,
		"distribution_frequency": "Monthly",
		"creation": ("between", get_migration_window(old)),
	}
	if old.budget_against == "Project":
		filters["project"] = old.project
	else:
		filters["cost_center"] = old.cost_center
	for fieldname in dimensions or []:
		if old.get(fieldname):
			filters[fieldname] = old.get(fieldname)

	budgets = frappe.get_all("Budget", filters=filters, fields=["name", "budget_amount"])
	if not budgets:
		return

	distributions = {}
	for row in frappe.get_all(
		"Budget Distribution",
		filters={"parent": ("in", [b.name for b in budgets]), "parenttype": "Budget"},
		fields=["name", "parent", "idx", "start_date", "percent", "amount"],
		order_by="parent asc, idx asc",
	):
		distributions.setdefault(row.parent, []).append(row)

	month_starts = [get_first_day(add_months(year_start_date, i)) for i in range(12)]
	for budget in budgets:
		distribution = distributions.get(budget.name, [])
		if not is_as_migrated(distribution, shifted, budget.budget_amount, month_starts):
			continue

		for i, percent in enumerate(correct):
			values = {"percent": percent, "amount": flt(budget.budget_amount) * percent / 100}
			if i < len(distribution):
				frappe.db.set_value(
					"Budget Distribution", distribution[i].name, values, update_modified=False
				)
			else:
				# the migration made only as many rows as the distribution had
				frappe.get_doc(
					{
						"doctype": "Budget Distribution",
						"parent": budget.name,
						"parenttype": "Budget",
						"parentfield": "budget_distribution",
						"idx": i + 1,
						"start_date": month_starts[i],
						"end_date": get_last_day(month_starts[i]),
						**values,
					}
				).db_insert()

		if len(set(correct)) > 1:
			frappe.db.set_value("Budget", budget.name, "distribute_equally", 0, update_modified=False)


def get_migration_window(old):
	"""The migration made the new budgets of an old budget just before it cancelled it, and after it
	cancelled the old budget before it."""
	budget = frappe.qb.DocType("Budget")
	previous = (
		frappe.qb.from_(budget)
		.select(Max(budget.modified))
		.where((budget.docstatus == 2) & (budget.modified < old.modified) & (budget.name != old.name))
		.run()
	)
	return [previous[0][0] or "1900-01-01", old.modified]


def is_as_migrated(distribution, shifted, budget_amount, month_starts):
	"""The rows, percentages and amounts are still the ones the migration wrote."""
	return (
		len(distribution) == len(shifted)
		and all(getdate(row.start_date) == month_starts[i] for i, row in enumerate(distribution))
		and same([row.percent for row in distribution], shifted)
		and all(
			abs(flt(row.amount) - flt(budget_amount) * flt(row.percent) / 100) < 0.01 for row in distribution
		)
	)


def same(first, second):
	return len(first) == len(second) and all(
		flt(a, 6) == flt(b, 6) for a, b in zip(first, second, strict=True)
	)
