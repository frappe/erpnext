# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.utils import getdate, today

from erpnext.stock.report.stock_analytics.stock_analytics import (
	get_period,
	get_period_columns,
	get_period_date_ranges,
)

WORK_ORDER_STATUS_LIST = ["Not Started", "Overdue", "Pending", "Completed", "Closed", "Stopped"]


def execute(filters=None):
	period_columns = get_period_columns(filters)
	columns = get_columns(period_columns)
	data, chart = get_data(filters, period_columns)
	return columns, data, None, chart


def get_columns(period_columns):
	columns = [{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140}]
	columns.extend(period_columns)

	return columns


def get_work_orders(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	WorkOrder = frappe.qb.DocType("Work Order")

	return (
		frappe.qb.from_(WorkOrder)
		.select(WorkOrder.creation, WorkOrder.actual_end_date, WorkOrder.planned_end_date, WorkOrder.status)
		.where(
			(WorkOrder.docstatus == 1)
			& (WorkOrder.company == filters.get("company"))
			& (
				(WorkOrder.creation.between(from_date, to_date))
				| (WorkOrder.actual_end_date.between(from_date, to_date))
			)
		)
		.run(as_dict=True)
	)


def get_data(filters, period_columns):
	ranges = build_ranges(filters)
	period_labels = [scrub(pd) for _fd, _td, pd in ranges]
	periodic_data = {status: {pd: 0 for pd in period_labels} for status in WORK_ORDER_STATUS_LIST}
	entries = get_work_orders(filters)

	for d in entries:
		if d.status == "Completed":
			if not d.actual_end_date:
				continue

			if period := scrub(get_period_for_date(getdate(d.actual_end_date), ranges)):
				periodic_data["Completed"][period] += 1
			continue

		creation_date = getdate(d.creation)
		period = scrub(get_period_for_date(creation_date, ranges))
		if not period:
			continue

		if d.status in ("Not Started", "Closed", "Stopped"):
			periodic_data[d.status][period] += 1
		else:
			if d.planned_end_date and getdate(today()) > getdate(d.planned_end_date):
				periodic_data["Overdue"][period] += 1
			else:
				periodic_data["Pending"][period] += 1

	data = []
	for status in WORK_ORDER_STATUS_LIST:
		row = {"status": _(status)}
		for _fd, _td, period in ranges:
			row[scrub(period)] = periodic_data[status].get(scrub(period), 0)
		data.append(row)

	chart = get_chart_data(periodic_data, period_columns)
	return data, chart


def get_period_for_date(date, ranges):
	for from_date, to_date, period in ranges:
		if from_date <= date <= to_date:
			return period
	return None


def build_ranges(filters):
	ranges = []
	for from_date, end_date in get_period_date_ranges(filters):
		period = get_period(end_date, filters)
		ranges.append((getdate(from_date), getdate(end_date), period))
	return ranges


def get_chart_data(periodic_data, period_columns):
	period_labels = [col.get("label") for col in period_columns]
	period_fieldnames = [col.get("fieldname") for col in period_columns]

	datasets = []
	for status in WORK_ORDER_STATUS_LIST:
		values = [periodic_data.get(status, {}).get(fieldname, 0) for fieldname in period_fieldnames]
		datasets.append({"name": _(status), "values": values})

	return {"data": {"labels": period_labels, "datasets": datasets}, "type": "line"}
