# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Literal

import frappe
from frappe import _
from frappe.model.docstatus import DocStatus
from frappe.query_builder.functions import Coalesce, Count, NullIf, Round, Sum
from frappe.utils.data import get_timespan_date_range


def execute(filters=None):
	columns = get_columns(filters.get("group_by"))
	from_date, to_date = get_timespan_date_range(filters.get("timespan").lower())
	lost_quotations = get_lost_quotations(filters.get("company"), from_date, to_date)
	currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")
	data = get_data(lost_quotations, filters.get("group_by"), currency)
	report_summary = get_report_summary(lost_quotations, currency)
	return columns, data, None, None, report_summary


def get_columns(group_by: Literal["Lost Reason", "Competitor"]):
	return [
		{
			"fieldname": "lost_reason" if group_by == "Lost Reason" else "competitor",
			"label": _("Lost Reason") if group_by == "Lost Reason" else _("Competitor"),
			"fieldtype": "Link",
			"options": "Quotation Lost Reason" if group_by == "Lost Reason" else "Competitor",
			"width": 200,
		},
		{
			"fieldname": "lost_quotations",
			"label": _("Lost Quotations"),
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"fieldname": "lost_quotations_pct",
			"label": _("% of Lost Quotations"),
			"fieldtype": "Percent",
			"width": 200,
		},
		{
			"fieldname": "lost_value",
			"label": _("Lost Value"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "lost_value_pct",
			"label": _("Lost Value %"),
			"fieldtype": "Percent",
			"width": 200,
		},
		{
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
			"width": 0,
		},
	]


def get_lost_quotations(company: str, from_date: str, to_date: str) -> list[str]:
	# get_list applies the user's permissions, so the figures only cover quotations they may see
	return frappe.get_list(
		"Quotation",
		filters={
			"status": "Lost",
			"is_active": 1,
			"docstatus": DocStatus.submitted(),
			"company": company,
			"transaction_date": ["between", [from_date, to_date]],
		},
		pluck="name",
		limit_page_length=0,
	)


def get_data(lost_quotations: list[str], group_by: Literal["Lost Reason", "Competitor"], currency: str):
	"""Return quotation value grouped by lost reason or competitor"""
	if group_by == "Lost Reason":
		fieldname = "lost_reason"
		dimension = frappe.qb.DocType("Quotation Lost Reason Detail")
	elif group_by == "Competitor":
		fieldname = "competitor"
		dimension = frappe.qb.DocType("Competitor Detail")
	else:
		frappe.throw(_("Invalid Group By"))

	if not lost_quotations:
		return []

	q = frappe.qb.DocType("Quotation")
	total_quotations = len(lost_quotations)
	total_value = frappe.qb.from_(q).where(q.name.isin(lost_quotations)).select(Sum(q.base_net_total))

	# distinct (quotation, reason) pairs so the same reason entered twice is counted once
	pairs = (
		frappe.qb.from_(q)
		.left_join(dimension)
		.on(dimension.parent == q.name)
		.where(q.name.isin(lost_quotations))
		.select(
			q.name.as_("quotation"),
			q.base_net_total.as_("value"),
			Coalesce(dimension[fieldname], _("Not Specified")).as_("reason"),
		)
		.distinct()
	).as_("pairs")

	reasons_per_quotation = (
		frappe.qb.from_(pairs)
		.select(pairs.quotation, Count(pairs.reason).as_("reasons"))
		.groupby(pairs.quotation)
	).as_("reasons_per_quotation")

	# split each quotation's value evenly across its distinct reasons so shares sum to the lost total
	split = (
		frappe.qb.from_(pairs)
		.join(reasons_per_quotation)
		.on(pairs.quotation == reasons_per_quotation.quotation)
		.select(
			pairs.reason,
			pairs.quotation,
			(pairs.value / reasons_per_quotation.reasons).as_("value"),
		)
	).as_("split")

	query = (
		frappe.qb.from_(split)
		.select(
			split.reason,
			Count(split.quotation).distinct(),
			# `* 100.0` before dividing: count/count is integer division on Postgres (truncates to 0)
			Round((Count(split.quotation).distinct() * 100.0 / total_quotations), 2),
			Sum(split.value),
			Round((Sum(split.value) / NullIf(total_value, 0) * 100), 2),
		)
		.groupby(split.reason)
	)

	return [(*row, currency) for row in query.run()]


def get_report_summary(lost_quotations: list[str], currency: str):
	# surface the denominator so the per-reason percentages are readable
	total_value = 0
	if lost_quotations:
		q = frappe.qb.DocType("Quotation")
		total_value = (
			frappe.qb.from_(q).where(q.name.isin(lost_quotations)).select(Sum(q.base_net_total)).run()
		)[0][0] or 0

	return [
		{
			"label": _("Total Lost Quotations"),
			"value": len(lost_quotations),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"label": _("Total Lost Value"),
			"value": total_value,
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Red",
		},
	]
