# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from functools import cached_property

import frappe
from frappe.model import get_permitted_fields
from frappe.utils import add_months, flt, getdate

from erpnext.projects.doctype.project.costing.billing import ProjectBilling
from erpnext.projects.doctype.project.costing.drivers import CostDrivers
from erpnext.projects.doctype.project.costing.queries import MonthlyAmounts, ProjectCostQueries
from erpnext.projects.doctype.project.project_overview import check_access

PROJECT_FIELDS = ("name", "status", "customer", "company", "percent_complete", "estimated_costing")
# A forecast this far over the estimate (in percent) still counts as on budget.
FORECAST_TOLERANCE = 5
RUNNING_STATUSES = ("Open", "On hold")
# What each part of the Costing tab opens, and the doctype whose read permission it needs.
SOURCE_DOCTYPES = {
	"purchases": "Purchase Invoice",
	"invoices": "Sales Invoice",
	"sales_orders": "Sales Order",
}


@frappe.whitelist()
def get_project_costing(project: str) -> dict:
	"""Return the data behind the Project form's Costing tab.

	Every amount is calculated from the documents booked against the project when the tab asks,
	not read from the totals the Project stores, so it is current even before those are updated.
	"""
	check_access(project)
	return ProjectCosting(project).build()


class ProjectCosting:
	"""Builds the sections of one project's Costing tab. Amounts are in the company's currency.

	Each section is built on its own: one that fails comes back as None and is flagged in
	`errors`, so the tab can still render the others.
	"""

	SECTIONS = ("summary", "monthly", "billing", "drivers", "rate_gaps")

	def __init__(self, project: str):
		self.project = frappe.db.get_value("Project", project, PROJECT_FIELDS, as_dict=True)
		self.queries = ProjectCostQueries(project)
		self.access = get_costing_access(project)
		self.currency = frappe.get_cached_value("Company", self.project.company, "default_currency")

	def build(self) -> dict:
		payload = {
			"project": self.project.name,
			# the Project stores the customer's ID, which a naming series makes unreadable
			"customer_name": self.customer_name(),
			"as_of": str(getdate()),
			"currency": self.currency,
			"access": self.access,
			"errors": {},
		}
		for section in self.SECTIONS:
			try:
				payload[section] = getattr(self, section)()
			except Exception:
				payload[section] = None
				payload["errors"][section] = 1
				frappe.log_error(title="Project Costing: " + section)
		return payload

	def customer_name(self) -> str | None:
		if not self.project.customer:
			return None
		return frappe.get_cached_value("Customer", self.project.customer, "customer_name")

	def summary(self) -> dict:
		summary = CostingSummary(self.project, self.totals, self.contract).build()
		summary["hours"] = sum(self.monthly_hours.values())
		return summary

	def monthly(self) -> list[dict]:
		return monthly_rows({**self.monthly_amounts, "hours": self.monthly_hours})

	def billing(self) -> dict:
		billed = self.totals["billed"]
		return ProjectBilling(self.project.name, self.access, self.currency, self.contract, billed).build()

	def drivers(self) -> dict:
		return self.cost_drivers.build()

	def rate_gaps(self) -> dict | None:
		return self.cost_drivers.rate_gaps()

	@cached_property
	def cost_drivers(self) -> CostDrivers:
		return CostDrivers(self.project.name, self.access)

	@cached_property
	def monthly_amounts(self) -> dict[str, MonthlyAmounts]:
		"""Each cost source, then billing, by month. Expense Claims count only with HRMS, which adds
		them to the Project's gross margin."""
		amounts = {
			"labour": self.queries.labour_cost(by_month=True),
			"purchases": self.queries.purchase_cost(by_month=True),
			"materials": self.queries.material_cost(by_month=True),
		}
		if has_hrms():
			amounts["expenses"] = self.queries.expense_claim_cost(by_month=True)
		amounts["billed"] = self.queries.billed_amount(by_month=True)
		return amounts

	@cached_property
	def monthly_hours(self) -> MonthlyAmounts:
		return self.queries.labour_hours(by_month=True)

	@cached_property
	def totals(self) -> dict[str, float]:
		return {source: sum(months.values()) for source, months in self.monthly_amounts.items()}

	@cached_property
	def contract(self) -> float:
		return self.queries.sales_order_amount()


def get_costing_access(project: str) -> dict[str, bool]:
	"""What the user may open behind the Costing tab's totals.

	Every user who can read the Project sees the totals. The documents behind them, and the
	amounts split by person or supplier, follow the user's permission on each doctype.
	"""
	access = {key: can_read(doctype) for key, doctype in SOURCE_DOCTYPES.items()}
	access["labour"] = can_read_labour_cost()
	# Materials open as Stock Entries; the list behind them reads stock ledger rows.
	access["materials"] = can_read("Stock Entry") and can_read("Stock Ledger Entry")
	access["edit_estimate"] = can_edit_estimate(project)
	return access


def has_hrms() -> bool:
	"""HRMS adds Expense Claims to a project's cost, so the Costing tab counts them only with HRMS."""
	return "hrms" in frappe.get_installed_apps()


def can_read(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def can_read_labour_cost() -> bool:
	"""Costing rates sit on a higher permission level of Timesheet Detail than hours do."""
	if not can_read("Timesheet"):
		return False
	if frappe.session.user == "Administrator":
		return True
	permitted = get_permitted_fields("Timesheet Detail", parenttype="Timesheet", permission_type="read")
	return "costing_rate" in permitted


def can_edit_estimate(project: str) -> bool:
	return bool(frappe.has_permission("Project", "write", doc=project))


class CostingSummary:
	"""The headline numbers of a project's Costing tab: cost against the estimate, billing against
	the contract, and the margin between them.

	`totals` holds the amount of each cost source plus "billed", all in the company's currency.
	"""

	def __init__(self, project: frappe._dict, totals: dict[str, float], contract: float):
		self.project = project
		self.billed = flt(totals.get("billed"))
		self.sources = {source: amount for source, amount in totals.items() if source != "billed"}
		self.cost = sum(self.sources.values())
		self.estimate = flt(project.estimated_costing)
		self.contract = flt(contract)

	def build(self) -> dict:
		return {
			"status": self.project.status,
			"percent_complete": flt(self.project.percent_complete, 1),
			"sources": self.sources,
			"cost": self.cost,
			"estimate": self.estimate or None,
			"used_percent": self.percent_of(self.cost, self.estimate),
			"forecast": self.forecast,
			"variance": self.forecast - self.estimate if self.estimate else None,
			"health": self.health(),
			"contract": self.contract or None,
			"billed": self.billed,
			"billed_percent": self.percent_of(self.billed, self.contract),
			**self.margins(),
			"internal": self.is_internal(),
		}

	@property
	def forecast(self) -> float:
		"""Cost at completion if the rest of the work costs what the done part did: cost to date
		scaled by percent complete. A finished, cancelled or not yet started project forecasts its
		cost to date."""
		percent_complete = flt(self.project.percent_complete)
		if self.project.status in RUNNING_STATUSES and 0 < percent_complete < 100:
			return self.cost * 100 / percent_complete
		return self.cost

	def health(self) -> str:
		"""empty: nothing booked or billed yet; none: no estimate; over: cost to date is past the
		estimate; risk: the forecast is past it beyond the tolerance; ok otherwise."""
		if not self.cost and not self.billed:
			return "empty"
		if not self.estimate:
			return "none"
		if self.cost > self.estimate:
			return "over"
		if self.forecast > self.estimate * (100 + FORECAST_TOLERANCE) / 100:
			return "risk"
		return "ok"

	def margins(self) -> dict:
		"""Gross margin is billed less cost to date. The projected margin expects the contract to be
		billed in full, or what was billed when that is more; the planned one compares the contract
		with the estimate. Both need a contract."""
		margin = self.billed - self.cost
		billable = max(self.contract, self.billed)
		return {
			"margin": margin,
			"margin_percent": self.percent_of(margin, self.billed),
			"projected_margin": billable - self.forecast if self.contract else None,
			"planned_margin": self.contract - self.estimate if self.contract and self.estimate else None,
		}

	def is_internal(self) -> bool:
		"""A project with no customer, no sales order and nothing billed is run for the company itself."""
		return not self.project.customer and not self.contract and not self.billed

	@staticmethod
	def percent_of(amount: float, whole: float) -> float | None:
		return flt(amount * 100 / whole, 1) if whole else None


def monthly_rows(amounts: dict[str, MonthlyAmounts]) -> list[dict]:
	"""One row per month from the first to the last month with a value, months between included,
	each with every series' value for that month."""
	months = sorted({month for months in amounts.values() for month in months})
	if not months:
		return []
	return [
		{"month": month, **{source: flt(by_month.get(month)) for source, by_month in amounts.items()}}
		for month in month_range(months[0], months[-1])
	]


def month_range(first: str, last: str) -> list[str]:
	"""Every "YYYY-MM" month from `first` to `last`, both included."""
	month, end = getdate(first + "-01"), getdate(last + "-01")
	months = []
	while month <= end:
		months.append(month.strftime("%Y-%m"))
		month = getdate(add_months(month, 1))
	return months
