# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Literal

import frappe
from frappe import _
from frappe.model.docstatus import DocStatus
from frappe.query_builder.functions import Coalesce, Count, Round, Sum
from frappe.utils.data import get_timespan_date_range


def execute(filters=None):
	columns = get_columns(filters.get("group_by"))
	from_date, to_date = get_timespan_date_range(filters.get("timespan").lower())
	data = get_data(filters.get("company"), from_date, to_date, filters.get("group_by"))
	return columns, data


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
			"filedname": "lost_quotations",
			"label": _("Lost Quotations"),
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"filedname": "lost_quotations_pct",
			"label": _("Lost Quotations %"),
			"fieldtype": "Percent",
			"width": 200,
		},
		{
			"fieldname": "lost_value",
			"label": _("Lost Value"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"filedname": "lost_value_pct",
			"label": _("Lost Value %"),
			"fieldtype": "Percent",
			"width": 200,
		},
	]


def get_data(
	company: str, from_date: str, to_date: str, group_by: Literal["Lost Reason", "Competitor"]
):
	"""Return quotation value grouped by lost reason or competitor"""
	if group_by == "Lost Reason":
		fieldname = "lost_reason"
		dimension = frappe.qb.DocType("Quotation Lost Reason Detail")
	elif group_by == "Competitor":
		fieldname = "competitor"
		dimension = frappe.qb.DocType("Competitor Detail")
	else:
		frappe.throw(_("Invalid Group By"))

	q = frappe.qb.DocType("Quotation")

	lost_quotation_condition = (
		(q.status == "Lost")
		& (q.docstatus == DocStatus.submitted())
		& (q.transaction_date >= from_date)
		& (q.transaction_date <= to_date)
		& (q.company == company)
	)

	from_lost_quotations = frappe.qb.from_(q).where(lost_quotation_condition)
	total_quotations = from_lost_quotations.select(Count(q.name))
	total_value = from_lost_quotations.select(Sum(q.base_net_total))

	query = (
		frappe.qb.from_(q)
		.select(
			Coalesce(dimension[fieldname], _("Not Specified")),
			Count(q.name).distinct(),
			Round((Count(q.name).distinct() / total_quotations * 100), 2),
			Sum(q.base_net_total),
			Round((Sum(q.base_net_total) / total_value * 100), 2),
		)
		.left_join(dimension)
		.on(dimension.parent == q.name)
		.where(lost_quotation_condition)
		.groupby(dimension[fieldname])
	)

	return query.run()
