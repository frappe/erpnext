# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from functools import cached_property

import frappe
from frappe import qb
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import Coalesce, Count, Extract, Sum
from frappe.utils import flt, get_last_day, getdate
from pypika.enums import DatePart

from erpnext.accounts.utils import get_fiscal_year
from erpnext.projects.doctype.project.costing.budgets import BUDGET_FIELDS, account_status, budget_summary
from erpnext.projects.doctype.project.costing.project_costing import (
	can_create,
	can_read,
	can_submit,
	month_range,
	permitted_reports,
)
from erpnext.projects.doctype.project.project_overview import check_access

# The Accounts reports; each opens on the project's fiscal year.
ACCOUNTS_REPORTS = ("Budget Variance Report", "General Ledger", "Profit and Loss Statement")
LEDGER_FIELDS = [
	"name",
	"posting_date",
	"voucher_type",
	"voucher_no",
	"account",
	"debit",
	"credit",
]


@frappe.whitelist(methods=["GET"])
def get_project_accounts(project: str) -> dict:
	"""Return the data behind the Costing tab's Accounts view: the project's ledger, commitments and
	Budget records by account, for the company's current fiscal year.

	Reading the ledger needs GL Entry access. Budget records need Budget access (Accounts Manager);
	without it, the accounts come back without them.
	"""
	check_access(project)
	frappe.has_permission("GL Entry", "read", throw=True)
	return ProjectAccounts(project).build()


@frappe.whitelist(methods=["GET"])
def get_ledger_entries(
	project: str,
	root_type: str | None = None,
	start: int = 0,
	page_length: int = 20,
) -> list[dict]:
	"""One page of the project's ledger entries on Profit and Loss accounts in the current fiscal
	year, newest first, optionally for the accounts of one root type ("Expense" or "Income").

	The balance sheet side of each voucher (debtors, creditors, stock) is left out, so an amount
	shows once, on the account it was spent or earned on."""
	check_access(project)
	company = frappe.db.get_value("Project", project, "company")
	period = current_fiscal_year(company)
	filters = {
		"project": project,
		"company": company,
		"is_cancelled": 0,
		"posting_date": ["between", [period.year_start_date, period.year_end_date]],
	}
	filters["account"] = ["in", profit_and_loss_accounts(company, root_type)]
	return frappe.get_list(
		"GL Entry",
		filters=filters,
		fields=LEDGER_FIELDS,
		order_by="posting_date desc, creation desc",
		offset=max(start, 0),
		limit=page_length,
	)


def profit_and_loss_accounts(company: str, root_type: str | None = None) -> list[str]:
	filters = {"company": company, "report_type": "Profit and Loss"}
	if root_type:
		filters["root_type"] = root_type
	return frappe.get_all("Account", filters=filters, pluck="name")


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
				# a budget added from the tab is submitted as well as created
				"manage_budgets": can_create("Budget") and can_submit("Budget"),
			},
			"reports": permitted_reports(ACCOUNTS_REPORTS),
			"rows": rows,
			"monthly": self.monthly(),
		}

	def account_row(self, account: frappe._dict) -> dict:
		sign = -1 if account.root_type == "Income" else 1
		booked = self.ledger_totals.get(account.name, {})
		budget = self.budgets.get(account.name)
		expense = account.root_type == "Expense"
		spend = {
			"actual": sign * flt(booked.get("balance")),
			"ordered": self.ordered.get(account.name, 0) if expense else 0,
			"requested": self.requested.get(account.name, 0) if expense else 0,
			**self.budget_spend.get(account.name, {"spent": 0.0, "spent_to_date": 0.0}),
		}
		return {
			"account": account.name,
			"account_name": account.account_name,
			"root_type": account.root_type,
			"actual": spend["actual"],
			"entries": booked.get("entries", 0),
			"committed": spend["ordered"] + spend["requested"],
			"budget": budget and budget_summary(budget, spend),
			"status": account_status(budget, spend) if expense else None,
		}

	@cached_property
	def ordered(self) -> dict[str, float]:
		"""Open purchase orders and material requests on each expense account, counted as ERPNext's
		budget controller counts them (`BudgetValidation.get_ordered_amount` and
		`get_requested_amount`), for every account at once."""
		return {account: flt(amount) for account, amount in self.ordered_by_account()}

	@cached_property
	def requested(self) -> dict[str, float]:
		return {account: flt(amount) for account, amount in self.requested_by_account()}

	def ordered_by_account(self) -> list[tuple[str, float]]:
		"""What submitted, open purchase orders dated in the fiscal year have not billed yet."""
		item, order = qb.DocType("Purchase Order Item"), qb.DocType("Purchase Order")
		unbilled = (item.amount - item.billed_amt) * Coalesce(order.conversion_rate, 1)
		query = (
			qb.from_(item)
			.join(order)
			.on(order.name == item.parent)
			.where(order.docstatus == 1)
			.where(order.status != "Closed")
			.where(item.closed == 0)
			.where(item.amount > item.billed_amt)
			.where(order.transaction_date[self.fiscal_year.year_start_date : self.fiscal_year.year_end_date])
		)
		return self.by_expense_account(query, item, unbilled, "Purchase Order")

	def requested_by_account(self) -> list[tuple[str, float]]:
		"""What submitted purchase material requests dated in the fiscal year have not ordered yet."""
		item, request = qb.DocType("Material Request Item"), qb.DocType("Material Request")
		unordered = (item.stock_qty - item.ordered_qty) * item.rate / item.conversion_factor
		query = (
			qb.from_(item)
			.join(request)
			.on(request.name == item.parent)
			.where(request.docstatus == 1)
			.where(request.material_request_type == "Purchase")
			.where(request.status != "Stopped")
			.where(item.stock_qty > item.ordered_qty)
			.where(
				request.transaction_date[self.fiscal_year.year_start_date : self.fiscal_year.year_end_date]
			)
		)
		return self.by_expense_account(query, item, unordered, "Material Request")

	def by_expense_account(self, query, item, amount, doctype: str) -> list[tuple[str, float]]:
		"""`amount` for each expense account, over the `doctype` documents the user may read, as the
		ledger keeps to the entries they may read."""
		if not can_read(doctype):
			return []
		readable = frappe.qb.get_query(doctype, fields=["name"], ignore_permissions=False)
		return (
			query.where(item.project == self.project.name)
			.where(item.parent.isin(readable))
			.select(item.expense_account, Sum(amount))
			.groupby(item.expense_account)
			.run()
		)

	def monthly(self) -> list[dict]:
		"""Expense to date and the expense budget accumulated to date, month by month, from the start
		of the fiscal year to this month or its end.

		With budgets, both lines cover the budgeted expense accounts only, so spend on an account
		without a budget never shows as going over one. Without budgets, the actual line covers
		every expense account."""
		last = min(getdate(), getdate(self.fiscal_year.year_end_date))
		months = month_range(str(self.fiscal_year.year_start_date)[:7], str(last)[:7])
		expense = {account.name for account in self.accounts if account.root_type == "Expense"}
		if self.budgets:
			expense &= set(self.budgets)
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
		"""Profit and Loss accounts with ledger entries, a budget or a commitment for the project,
		that the user may read: an account hidden by a User Permission leaves out its budget and
		commitments too."""
		names = set(self.ledger_totals) | set(self.budgets) | set(self.ordered) | set(self.requested)
		names.discard(None)
		return frappe.get_list(
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

	@cached_property
	def budget_spend(self) -> dict[str, dict[str, float]]:
		"""Debit less credit on each budgeted account over its Budget's whole period, in all and to
		the end of this month. ERPNext's ledger check measures an expense this way, so a Budget that
		runs over several fiscal years counts what its earlier years spent."""
		if not self.budgets:
			return {}
		gle = qb.DocType("GL Entry")
		amount = gle.debit - gle.credit
		periods = Criterion.any(
			[
				(gle.account == account)
				& gle.posting_date[budget["budget_start_date"] : budget["budget_end_date"]]
				for account, budget in self.budgets.items()
			]
		)
		to_date = Case().when(gle.posting_date <= get_last_day(getdate()), amount).else_(0)
		rows = (
			self.readable_ledger()
			.where(periods)
			.select(gle.account, Sum(amount).as_("spent"), Sum(to_date).as_("spent_to_date"))
			.groupby(gle.account)
			.run(as_dict=True)
		)
		return {
			row.account: {"spent": flt(row.spent), "spent_to_date": flt(row.spent_to_date)} for row in rows
		}

	def ledger_query(self):
		"""The project's GL Entries in the fiscal year that the user may read."""
		gle = qb.DocType("GL Entry")
		return self.readable_ledger().where(
			gle.posting_date[self.fiscal_year.year_start_date : self.fiscal_year.year_end_date]
		)

	def readable_ledger(self):
		"""The project's GL Entries that the user may read. The rules come from the framework's query
		builder, so User Permissions on accounts, cost centers and the like apply, as they do to the
		ledger list."""
		gle = qb.DocType("GL Entry")
		readable = frappe.qb.get_query(
			"GL Entry", fields=["name"], filters={"project": self.project.name}, ignore_permissions=False
		)
		return (
			qb.from_(gle)
			.where(gle.name.isin(readable))
			.where(gle.project == self.project.name)
			.where(gle.company == self.project.company)
			.where(gle.is_cancelled == 0)
		)

	@cached_property
	def budgets(self) -> dict[str, dict]:
		"""The submitted Budget on each account that applies today, as ERPNext picks the one to check
		a new document against, with its distribution by month."""
		if not self.can_read_budgets:
			return {}
		today = getdate()
		budgets = frappe.get_list(
			"Budget",
			filters={
				"budget_against": "Project",
				"project": self.project.name,
				"company": self.project.company,
				"docstatus": 1,
				"budget_start_date": ["<=", today],
				"budget_end_date": [">=", today],
			},
			fields=BUDGET_FIELDS,
		)
		by_month = self.distribution_by_month([budget.name for budget in budgets])
		return {budget.account: {**budget, "by_month": by_month.get(budget.name, {})} for budget in budgets}

	def distribution_by_month(self, budgets: list[str]) -> dict[str, dict[str, float]]:
		rows = frappe.get_all(
			"Budget Distribution",
			filters={"parenttype": "Budget", "parent": ["in", budgets]},
			fields=["parent", "start_date", "amount"],
		)
		by_month = {}
		for row in rows:
			months = by_month.setdefault(row.parent, {})
			month = str(row.start_date)[:7]
			months[month] = months.get(month, 0) + flt(row.amount)
		return by_month
