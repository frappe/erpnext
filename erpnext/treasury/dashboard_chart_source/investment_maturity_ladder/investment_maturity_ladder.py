# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_first_day, nowdate
from frappe.utils.dashboard import cache_source

from erpnext.treasury.dashboard import HELD_STATUSES, get_company, get_month_ends, get_monthly_chart


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
	"""Book value of held investments maturing in each of the next 12 months."""
	month_ends = get_month_ends(nowdate(), 12)
	investments = frappe.get_list(
		"Investment",
		filters={
			"company": get_company(filters),
			"docstatus": 1,
			"status": ("in", HELD_STATUSES),
			"maturity_date": ("between", [get_first_day(nowdate()), month_ends[-1]]),
		},
		fields=["maturity_date", "total_cost"],
		as_list=True,
	)

	return get_monthly_chart(month_ends, investments, _("Book Value Maturing"), "bar")
