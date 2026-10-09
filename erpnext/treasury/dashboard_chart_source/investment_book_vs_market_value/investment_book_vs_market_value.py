# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.dashboard import cache_source

from erpnext.treasury.dashboard import HELD_STATUSES, get_company


@frappe.whitelist()
@cache_source
def get(
	chart_name: str | None = None,
	chart: str | dict | None = None,
	no_cache: bool | int | str | None = None,
	filters: str | dict | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	timespan: str | None = None,
	time_interval: str | None = None,
	heatmap_year: str | int | None = None,
) -> dict:
	"""Book value next to market value (at the last revaluation) of held investments, per investment type."""
	types = frappe.get_list(
		"Investment",
		filters={"company": get_company(filters), "docstatus": 1, "status": ("in", HELD_STATUSES)},
		fields=[
			"investment_type",
			{"SUM": "total_cost", "as": "book_value"},
			{"SUM": "market_value", "as": "market_value"},
		],
		group_by="investment_type",
		order_by="book_value desc",
	)

	return {
		"labels": [row.investment_type for row in types],
		"datasets": [
			{"name": _("Book Value"), "values": [row.book_value for row in types]},
			{"name": _("Market Value"), "values": [row.market_value for row in types]},
		],
		"type": "bar",
	}
