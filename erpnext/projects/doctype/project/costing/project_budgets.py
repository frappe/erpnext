# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from erpnext.projects.doctype.project.costing.budgets import (
	BUDGET_FIELDS,
	CONTROL_STAGES,
	budget_control,
	rule_label,
)
from erpnext.projects.doctype.project.project_overview import check_access

# The stages a Budget added from the project checks, by the one it checks from. The Budget form
# requires the later stages along with an earlier one.
CHECK_FROM = {
	"Expense": ("Expense",),
	"Purchase Order": ("Purchase Order", "Expense"),
	"Material Request": ("Material Request", "Purchase Order", "Expense"),
}
ACTIONS = ("Stop", "Warn", "Ignore")


@frappe.whitelist(methods=["POST"])
def create_project_budget(
	project: str,
	account: str,
	amount: float,
	action: str,
	check_from: str,
	split: str = "Monthly",
	period_amounts: list | str | None = None,
	from_fiscal_year: str | None = None,
	to_fiscal_year: str | None = None,
) -> str:
	"""Create and submit a Budget for the project on `account`, and return its name.

	It covers `from_fiscal_year` to `to_fiscal_year`, by default the years `get_budget_defaults`
	picks. `split` is how the amount is spread: evenly, or by `period_amounts`, one for each period
	`get_budget_periods` lists. `action` applies when the annual budget is exceeded, at `check_from`
	and each later stage. Monthly rules stay off; the Budget form sets them."""
	check_access(project)
	if action not in ACTIONS or check_from not in CHECK_FROM:
		frappe.throw(_("Choose what happens when spending goes over, and where it is checked"))
	budget = new_project_budget(project, split, from_fiscal_year, to_fiscal_year)
	budget.update({"account": account, "budget_amount": amount, "distribute_equally": 1})
	set_checks(budget, action, CHECK_FROM[check_from])
	budget.insert()
	if period_amounts:
		set_distribution(budget, frappe.parse_json(period_amounts))
		budget.save()
	budget.submit()
	return budget.name


@frappe.whitelist(methods=["GET"])
def get_budget_defaults(project: str) -> dict:
	"""The fiscal years a new budget for the project covers by default, and those it may cover."""
	check_access(project)
	return BudgetYears(project).defaults()


@frappe.whitelist(methods=["GET"])
def get_budget_periods(
	project: str,
	split: str = "Monthly",
	from_fiscal_year: str | None = None,
	to_fiscal_year: str | None = None,
) -> list[dict]:
	"""The periods a Budget for the project is spread over with `split`, each marked by whether the
	project runs in it, so a split can leave out the months before it starts or after it ends."""
	check_access(project)
	budget = new_project_budget(project, split, from_fiscal_year, to_fiscal_year)
	budget.set_fiscal_year_dates()
	runs = BudgetYears(project).runs_between
	return [
		{"start_date": start, "end_date": end, "in_project": runs(start, end)}
		for start, end in budget.get_budget_periods()
	]


@frappe.whitelist(methods=["GET"])
def get_project_budgets(project: str) -> dict:
	"""The Budget records against the project that the user may read, newest first, in every
	status, for the Budgets tab."""
	check_access(project)
	company = frappe.db.get_value("Project", project, "company")
	budgets = frappe.get_list(
		"Budget",
		filters={"budget_against": "Project", "project": project},
		fields=[*BUDGET_FIELDS, "from_fiscal_year", "to_fiscal_year", "distribution_frequency", "docstatus"],
		order_by="creation desc",
	)
	return {
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"budgets": [budget_row(budget) for budget in budgets],
	}


def budget_row(budget: dict) -> dict:
	control = budget_control(budget)
	return {
		"name": budget.name,
		"account": budget.account,
		"account_name": frappe.get_cached_value("Account", budget.account, "account_name"),
		"amount": flt(budget.budget_amount),
		"from_fiscal_year": budget.from_fiscal_year,
		"to_fiscal_year": budget.to_fiscal_year,
		"split": budget.distribution_frequency,
		"control": control,
		"rule": rule_label(control),
		"status": {0: "Draft", 1: "Active", 2: "Cancelled"}[budget.docstatus],
	}


def new_project_budget(project: str, split: str, from_fiscal_year: str | None, to_fiscal_year: str | None):
	"""An unsaved Budget against the project, spread by `split`, over the given fiscal years or the
	default ones."""
	if not (from_fiscal_year and to_fiscal_year):
		defaults = BudgetYears(project).defaults()
		from_fiscal_year = from_fiscal_year or defaults["from_fiscal_year"]
		to_fiscal_year = to_fiscal_year or defaults["to_fiscal_year"]
	return frappe.get_doc(
		{
			"doctype": "Budget",
			"budget_against": "Project",
			"project": project,
			"company": frappe.db.get_value("Project", project, "company"),
			"from_fiscal_year": from_fiscal_year,
			"to_fiscal_year": to_fiscal_year,
			"distribution_frequency": split,
		}
	)


class BudgetYears:
	"""The fiscal years a project's budget covers: from the one its expected start falls in to the
	one its expected end falls in. Without an expected start, the year starts today; without an
	expected end, the budget ends in the year it starts. An end past the company's last fiscal year
	stops at that year."""

	def __init__(self, project: str):
		self.project = frappe.db.get_value(
			"Project", project, ["company", "expected_start_date", "expected_end_date"], as_dict=True
		)
		self.start = getdate(self.project.expected_start_date or getdate())
		self.end = getdate(self.project.expected_end_date) if self.project.expected_end_date else None

	def defaults(self) -> dict:
		years = company_fiscal_years(self.project.company)
		if not years:
			frappe.throw(_("Set up a Fiscal Year for {0} first").format(self.project.company))
		first = year_containing(years, self.start)
		last = year_containing(years, self.end) if self.end else first
		if years.index(last) < years.index(first):
			last = first
		return {
			# a budget for a year before the project starts has nothing to hold
			"fiscal_years": [year.name for year in years[years.index(first) :]],
			"from_fiscal_year": first.name,
			"to_fiscal_year": last.name,
			"capped": bool(self.end and self.end > getdate(years[-1].year_end_date)),
		}

	def runs_between(self, start, end) -> bool:
		"""Whether the project runs at any time from `start` to `end`. Without expected dates, it
		runs in every period."""
		if not (self.project.expected_start_date and self.end):
			return True
		return getdate(start) <= self.end and getdate(end) >= self.start


def company_fiscal_years(company: str) -> list[frappe._dict]:
	"""The company's enabled fiscal years, earliest first: those that name it, and those that name
	no company at all."""
	years = frappe.get_all(
		"Fiscal Year",
		filters={"disabled": 0},
		fields=["name", "year_start_date", "year_end_date"],
		order_by="year_start_date",
	)
	named = {}
	for row in frappe.get_all("Fiscal Year Company", fields=["parent", "company"]):
		named.setdefault(row.parent, set()).add(row.company)
	return [year for year in years if not named.get(year.name) or company in named[year.name]]


def year_containing(years: list[frappe._dict], date) -> frappe._dict:
	"""The year `date` falls in; before the first, the first; after the last, the last."""
	for year in years:
		if getdate(year.year_start_date) <= date <= getdate(year.year_end_date):
			return year
	return years[0] if date < getdate(years[0].year_start_date) else years[-1]


def set_distribution(budget, amounts: list) -> None:
	"""Spread the budget over its periods by `amounts`, in order. ERPNext spreads a new Budget evenly,
	so a custom split is set once the Budget exists; ERPNext then checks that it adds up."""
	if len(amounts) != len(budget.budget_distribution):
		frappe.throw(_("Enter an amount for each of the {0} periods").format(len(budget.budget_distribution)))
	budget.distribute_equally = 0
	for row, amount in zip(budget.budget_distribution, amounts, strict=True):
		row.amount = flt(amount)
		row.percent = flt(amount) * 100 / flt(budget.budget_amount)


def set_checks(budget, action: str, stages: tuple[str, ...]) -> None:
	"""Check `stages` with `action` on the annual budget and no monthly rule; leave the rest off."""
	for stage, applies, annual, monthly in CONTROL_STAGES:
		checked = stage in stages
		budget.set(applies, int(checked))
		if checked:
			budget.set(annual, action)
			budget.set(monthly, "Ignore")
