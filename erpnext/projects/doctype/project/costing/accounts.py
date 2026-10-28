# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from functools import cached_property

import frappe
from frappe import qb
from frappe.query_builder.functions import Count, Extract, Sum
from frappe.utils import flt, getdate
from pypika.enums import DatePart

from erpnext.accounts.doctype.budget.budget import get_ordered_amount, get_requested_amount
from erpnext.accounts.utils import get_fiscal_year
from erpnext.projects.doctype.project.costing.project_costing import can_read, month_range
from erpnext.projects.doctype.project.project_overview import check_access

# A budget whose actual plus committed spend reaches this percent of it is near its limit.
NEAR_LIMIT = 90
# Where a Budget starts checking spend, earliest stage first, with the field that turns the check
# on and the field holding what happens when the annual budget is exceeded there.
CONTROL_STAGES = (
	("Material Request", "applicable_on_material_request", "action_if_annual_budget_exceeded_on_mr"),
	("Purchase Order", "applicable_on_purchase_order", "action_if_annual_budget_exceeded_on_po"),
	("Expense", "applicable_on_booking_actual_expenses", "action_if_annual_budget_exceeded"),
)
BUDGET_FIELDS = ["name", "account", "budget_amount", "revision_of"] + [
	field for stage in CONTROL_STAGES for field in stage[1:]
]
LEDGER_FIELDS = [
	"name",
	"posting_date",
	"voucher_type",
	"voucher_no",
	"account",
	"debit",
	"credit",
]


@frappe.whitelist()
def get_project_accounts(project: str) -> dict:
	"""Return the data behind the Costing tab's Accounts view: the project's ledger, commitments and
	Budget records by account, for the company's current fiscal year.

	Reading the ledger needs GL Entry access. Budget records need Budget access (Accounts Manager);
	without it, the accounts come back without them.
	"""
	check_access(project)
	frappe.has_permission("GL Entry", "read", throw=True)
	return ProjectAccounts(project).build()


@frappe.whitelist()
def get_ledger_entries(
	project: str,
	account: str | None = None,
	root_type: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> list[dict]:
	"""One page of the project's ledger entries in the current fiscal year, newest first, optionally
	for one account or the accounts of one root type ("Expense" or "Income")."""
	check_access(project)
	company = frappe.db.get_value("Project", project, "company")
	period = current_fiscal_year(company)
	filters = {
		"project": project,
		"company": company,
		"is_cancelled": 0,
		"posting_date": ["between", [period.year_start_date, period.year_end_date]],
	}
	if account:
		filters["account"] = account
	elif root_type:
		filters["account"] = [
			"in",
			frappe.get_all("Account", {"company": company, "root_type": root_type}, pluck="name"),
		]
	return frappe.get_list(
		"GL Entry",
		filters=filters,
		fields=LEDGER_FIELDS,
		order_by="posting_date desc, creation desc",
		start=start,
		page_length=page_length,
	)


def current_fiscal_year(company: str) -> frappe._dict:
	return get_fiscal_year(getdate(), company=company, as_dict=True)


class ProjectAccounts:
	"""One project's Profit and Loss accounts in the current fiscal year: what the ledger booked on
	each, what open purchase orders and material requests commit to it, and its Budget record.

	Amounts are in the company's currency. Expense rows count debit less credit, income rows credit
	less debit. Timesheets do not post to the ledger, so labour shows here only once it is paid or
	billed through accounting documents.
	"""

	def __init__(self, project: str):
		self.project = frappe.db.get_value("Project", project, ["name", "company"], as_dict=True)
		self.fiscal_year = current_fiscal_year(self.project.company)
		self.can_read_budgets = can_read("Budget")

	def build(self) -> dict:
		rows = [self.account_row(account) for account in self.accounts]
		return {
			"project": self.project.name,
			"company": self.project.company,
			"currency": frappe.get_cached_value("Company", self.project.company, "default_currency"),
			"fiscal_year": self.fiscal_year.name,
			"from_date": str(self.fiscal_year.year_start_date),
			"to_date": str(self.fiscal_year.year_end_date),
			"access": {
				"budgets": self.can_read_budgets,
				"manage_budgets": bool(frappe.has_permission("Budget", "create")),
			},
			"rows": rows,
			"monthly": self.monthly(),
		}

	def account_row(self, account: frappe._dict) -> dict:
		sign = -1 if account.root_type == "Income" else 1
		booked = self.ledger_totals.get(account.name, {})
		budget = self.budgets.get(account.name)
		row = {
			"account": account.name,
			"account_name": account.account_name,
			"root_type": account.root_type,
			"actual": sign * flt(booked.get("balance")),
			"entries": booked.get("entries", 0),
			"committed": self.committed(account.name) if account.root_type == "Expense" else 0,
			"budget": budget and budget_summary(budget),
		}
		row["status"] = account_status(row) if account.root_type == "Expense" else None
		return row

	def committed(self, account: str) -> float:
		"""Open purchase orders and material requests on the account, as Budget checks them."""
		params = frappe._dict(
			expense_account=account,
			budget_against_field="project",
			project=self.project.name,
			from_fiscal_year=self.fiscal_year.name,
			to_fiscal_year=self.fiscal_year.name,
		)
		return flt(get_ordered_amount(params)) + flt(get_requested_amount(params))

	def monthly(self) -> list[dict]:
		"""Expense to date and the expense budget accumulated to date, month by month, from the start
		of the fiscal year to this month or its end."""
		last = min(getdate(), getdate(self.fiscal_year.year_end_date))
		months = month_range(str(self.fiscal_year.year_start_date)[:7], str(last)[:7])
		expense = {account.name for account in self.accounts if account.root_type == "Expense"}
		actual, budget, rows = 0.0, 0.0, []
		for month in months:
			actual += sum(self.ledger_by_month.get((account, month), 0) for account in expense)
			budget += sum(
				self.budgets[account]["by_month"].get(month, 0) for account in expense & set(self.budgets)
			)
			rows.append({"month": month, "actual": actual, "budget": budget if self.budgets else None})
		return rows

	@cached_property
	def accounts(self) -> list[frappe._dict]:
		"""Profit and Loss accounts with ledger entries, a budget or a commitment for the project."""
		names = set(self.ledger_totals) | set(self.budgets) | set(self.ordered_accounts())
		return frappe.get_all(
			"Account",
			filters={"name": ["in", list(names)], "report_type": "Profit and Loss"},
			fields=["name", "account_name", "root_type"],
			order_by="root_type desc, account_name",
		)

	@cached_property
	def ledger_totals(self) -> dict[str, dict]:
		"""Debit less credit, and the number of entries, by account."""
		totals = {}
		for row in self.ledger_rows:
			total = totals.setdefault(row.account, {"balance": 0.0, "entries": 0})
			total["balance"] += flt(row.amount)
			total["entries"] += row.entries
		return totals

	@cached_property
	def ledger_by_month(self) -> dict[tuple[str, str], float]:
		"""Debit less credit, keyed by account and "YYYY-MM"."""
		return {
			(row.account, f"{int(row.year)}-{int(row.month):02d}"): flt(row.amount)
			for row in self.ledger_rows
		}

	@cached_property
	def ledger_rows(self) -> list[frappe._dict]:
		gle = qb.DocType("GL Entry")
		year, month = Extract(DatePart.year, gle.posting_date), Extract(DatePart.month, gle.posting_date)
		return (
			self.ledger_query()
			.select(
				gle.account,
				year.as_("year"),
				month.as_("month"),
				Sum(gle.debit - gle.credit).as_("amount"),
				Count("*").as_("entries"),
			)
			.groupby(gle.account, year, month)
			.run(as_dict=True)
		)

	def ledger_query(self):
		gle = qb.DocType("GL Entry")
		return (
			qb.from_(gle)
			.where(gle.project == self.project.name)
			.where(gle.company == self.project.company)
			.where(gle.is_cancelled == 0)
			.where(gle.posting_date[self.fiscal_year.year_start_date : self.fiscal_year.year_end_date])
		)

	def ordered_accounts(self) -> set[str]:
		"""Expense accounts named on the project's submitted purchase orders and material requests."""
		accounts = set()
		for doctype in ("Purchase Order Item", "Material Request Item"):
			accounts.update(
				frappe.get_all(
					doctype,
					filters={"project": self.project.name, "docstatus": 1, "expense_account": ["is", "set"]},
					pluck="expense_account",
					distinct=True,
				)
			)
		return accounts

	@cached_property
	def budgets(self) -> dict[str, dict]:
		"""The submitted Budget on each account that covers the fiscal year, with the part of its
		distribution that falls in it, by month."""
		if not self.can_read_budgets:
			return {}
		budgets = frappe.get_all(
			"Budget",
			filters={
				"budget_against": "Project",
				"project": self.project.name,
				"docstatus": 1,
				"budget_start_date": ["<=", self.fiscal_year.year_end_date],
				"budget_end_date": [">=", self.fiscal_year.year_start_date],
			},
			fields=BUDGET_FIELDS,
		)
		by_month = self.distribution_by_month([budget.name for budget in budgets])
		return {budget.account: {**budget, "by_month": by_month.get(budget.name, {})} for budget in budgets}

	def distribution_by_month(self, budgets: list[str]) -> dict[str, dict[str, float]]:
		rows = frappe.get_all(
			"Budget Distribution",
			filters={
				"parenttype": "Budget",
				"parent": ["in", budgets],
				"start_date": ["between", [self.fiscal_year.year_start_date, self.fiscal_year.year_end_date]],
			},
			fields=["parent", "start_date", "amount"],
		)
		by_month = {}
		for row in rows:
			months = by_month.setdefault(row.parent, {})
			month = str(row.start_date)[:7]
			months[month] = months.get(month, 0) + flt(row.amount)
		return by_month


def budget_summary(budget: dict) -> dict:
	"""A Budget's amount in the fiscal year, the part of it due by this month, and how it is enforced."""
	this_month = str(getdate())[:7]
	precision = frappe.get_precision("Budget Distribution", "amount")
	return {
		"name": budget["name"],
		# monthly shares are rounded, so their sum is too
		"amount": flt(sum(budget["by_month"].values()), precision),
		"to_date": flt(
			sum(amount for month, amount in budget["by_month"].items() if month <= this_month), precision
		),
		"revision_of": budget["revision_of"],
		"control": budget_control(budget),
	}


def budget_control(budget: dict) -> dict | None:
	"""The earliest stage at which the Budget acts on an exceeded annual amount, and how: "Stop" or
	"Warn". None when it only tracks."""
	for stage, applies, action in CONTROL_STAGES:
		if budget[applies] and budget[action] in ("Stop", "Warn"):
			return {"stage": stage, "action": budget[action]}
	return None


def account_status(row: dict) -> str:
	"""none: no budget; over: actual spend is past it; blocked: commitments take it past a budget
	that stops new orders; over_committed: commitments take it past one that does not; near: actual
	plus committed reach NEAR_LIMIT percent of it; ok otherwise."""
	budget = row["budget"]
	if not budget:
		return "none"
	used = row["actual"] + row["committed"]
	if row["actual"] > budget["amount"]:
		return "over"
	if used > budget["amount"]:
		control = budget["control"] or {}
		stops_orders = control.get("action") == "Stop" and control.get("stage") != "Expense"
		return "blocked" if stops_orders else "over_committed"
	if used >= budget["amount"] * NEAR_LIMIT / 100:
		return "near"
	return "ok"
