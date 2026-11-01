# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from functools import cached_property

from frappe import qb
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Max, Sum
from frappe.utils import flt
from pypika.enums import Order
from pypika.queries import QueryBuilder
from pypika.terms import Term

from erpnext.projects.doctype.project.costing.queries import ProjectCostQueries

DRIVER_LIMIT = 5
# Unpriced hours at this share of all hours (in percent) leave labour cost understated.
UNPRICED_HOURS_ALERT = 5


class CostDrivers:
	"""Where a project's cost comes from: the activities, people, suppliers and items that cost the
	most, at most DRIVER_LIMIT of each. A list the user may not open is None.

	Each list counts only the documents the user may read. Hours show to anyone who can read
	Timesheets; their cost, and hours logged without a costing rate, only to users who can see
	costing rates. A row whose group is not set has no name.
	"""

	def __init__(self, project: str, access: dict[str, bool]):
		self.queries = ProjectCostQueries(project, readable_only=True)
		self.access = access

	def build(self) -> dict:
		timesheet = qb.DocType("Timesheet")
		return {
			"activities": self.activities[:DRIVER_LIMIT],
			"employees": self.labour_by(timesheet.employee, Max(timesheet.employee_name), DRIVER_LIMIT),
			"suppliers": self.suppliers() if self.access["purchases"] else None,
			"items": self.items() if self.access["materials"] else None,
		}

	def rate_gaps(self) -> dict | None:
		return summarise_rate_gaps(self.activities) if self.access["labour"] else None

	@cached_property
	def activities(self) -> list[dict]:
		"""Every activity type, as the rate gaps need them all."""
		return self.labour_by(qb.DocType("Timesheet Detail").activity_type)

	def labour_by(self, group: Term, label: Term | None = None, limit: int | None = None) -> list[dict]:
		detail = qb.DocType("Timesheet Detail")
		timesheet = qb.DocType("Timesheet")
		query = self.queries.time_logs().join(timesheet).on(timesheet.name == detail.parent)
		measures = {"hours": Sum(detail.hours)}
		if label is not None:
			measures["label"] = label
		if self.access["labour"]:
			unpriced = detail.costing_rate == 0
			measures["amount"] = Sum(detail.base_costing_amount)
			measures["unpriced_hours"] = Sum(Case().when(unpriced, detail.hours).else_(0))
		order_by = "amount" if self.access["labour"] else "hours"
		return grouped_rows(query, group, measures, order_by, limit)

	def suppliers(self) -> list[dict]:
		invoice = qb.DocType("Purchase Invoice")
		invoice_item = qb.DocType("Purchase Invoice Item")
		measures = {
			"label": Max(invoice.supplier_name),
			"amount": Sum(invoice_item.base_net_amount),
			"documents": Count(invoice.name).distinct(),
		}
		return grouped_rows(self.queries.non_stock_purchase_items(), invoice.supplier, measures)

	def items(self) -> list[dict]:
		ledger = qb.DocType("Stock Ledger Entry")
		measures = {"amount": Sum(ledger.stock_value_difference * -1)}
		return grouped_rows(self.queries.stock_consumption_entries(), ledger.item_code, measures)


def grouped_rows(
	query: QueryBuilder,
	group: Term,
	measures: dict[str, Term],
	order_by: str = "amount",
	limit: int | None = DRIVER_LIMIT,
) -> list[dict]:
	"""`measures` for each value of `group`, largest `order_by` first."""
	query = (
		query.select(group.as_("name"), *(term.as_(name) for name, term in measures.items()))
		.groupby(group)
		.orderby(measures[order_by], order=Order.desc)
	)
	return (query.limit(limit) if limit else query).run(as_dict=True)


def summarise_rate_gaps(activities: list[dict]) -> dict:
	"""Hours logged at a costing rate of zero, which add no labour cost. The estimate prices them at
	the average rate of the hours that do have one."""
	unpriced_hours = sum(flt(row.unpriced_hours) for row in activities)
	all_hours = sum(flt(row.hours) for row in activities)
	priced_hours = all_hours - unpriced_hours
	average_rate = sum(flt(row.amount) for row in activities) / priced_hours if priced_hours else 0
	share = flt(unpriced_hours * 100 / all_hours, 1) if all_hours else 0
	return {
		"hours": unpriced_hours,
		"share": share,
		"estimate": unpriced_hours * average_rate if average_rate else None,
		"understated": share >= UNPRICED_HOURS_ALERT,
	}
