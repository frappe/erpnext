import frappe
from frappe.utils import add_months, flt


def execute():
	"""Budgets migrated by migrate_budget_records_to_new_structure got the Monthly Distribution
	percentages in row order from the fiscal year start, so for a fiscal year that does not start in
	January every month moved. Put them back on their months, for the budgets whose distribution
	still has exactly that order."""
	if not (
		frappe.db.has_column("Budget", "monthly_distribution")
		and frappe.db.has_column("Budget", "fiscal_year")
	):
		return

	budget = frappe.qb.DocType("Budget")
	old_budgets = (
		frappe.qb.from_(budget)
		.select(
			budget.company,
			budget.budget_against,
			budget.cost_center,
			budget.project,
			budget.fiscal_year,
			budget.monthly_distribution,
		)
		.where((budget.docstatus == 2) & budget.monthly_distribution.isnotnull())
		.where(budget.monthly_distribution != "")
		.distinct()
		.run(as_dict=True)
	)

	for old in old_budgets:
		fix_migrated_budgets(old)


def fix_migrated_budgets(old):
	if not frappe.db.exists("Monthly Distribution", old.monthly_distribution):
		return

	year_start_date = frappe.db.get_value("Fiscal Year", old.fiscal_year, "year_start_date")
	if not year_start_date or year_start_date.month == 1:
		return

	rows = frappe.get_all(
		"Monthly Distribution Percentage",
		filters={"parent": old.monthly_distribution, "parenttype": "Monthly Distribution"},
		fields=["month", "percentage_allocation"],
		order_by="idx asc",
	)
	shifted = [flt(row.percentage_allocation) for row in rows]
	by_month = {row.month: flt(row.percentage_allocation) for row in rows}
	correct = [by_month.get(add_months(year_start_date, i).strftime("%B"), 0) for i in range(12)]
	if len(shifted) != 12 or same(shifted, correct):
		return

	filters = {
		"docstatus": ("<", 2),
		"company": old.company,
		"budget_against": old.budget_against,
		"from_fiscal_year": old.fiscal_year,
		"to_fiscal_year": old.fiscal_year,
		"distribution_frequency": "Monthly",
	}
	if old.budget_against == "Project":
		filters["project"] = old.project
	else:
		filters["cost_center"] = old.cost_center

	for name, budget_amount in frappe.get_all(
		"Budget", filters=filters, fields=["name", "budget_amount"], as_list=True
	):
		distribution = frappe.get_all(
			"Budget Distribution",
			filters={"parent": name, "parenttype": "Budget"},
			fields=["name", "percent"],
			order_by="idx asc",
		)
		if not same([flt(row.percent) for row in distribution], shifted):
			continue

		for row, percent in zip(distribution, correct, strict=True):
			frappe.db.set_value(
				"Budget Distribution",
				row.name,
				{"percent": percent, "amount": flt(budget_amount) * percent / 100},
				update_modified=False,
			)


def same(first, second):
	return len(first) == len(second) and all(
		flt(a, 6) == flt(b, 6) for a, b in zip(first, second, strict=True)
	)
