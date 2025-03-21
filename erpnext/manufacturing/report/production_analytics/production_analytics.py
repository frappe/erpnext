# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.utils import getdate, today

from erpnext.stock.report.stock_analytics.stock_analytics import get_period, get_period_date_ranges


def execute(filters=None):
	columns = get_columns(filters)
	data, chart = get_data(filters, columns)
	return columns, data, None, chart


def get_columns(filters):
	columns = [{"label": _("Status"), "fieldname": "Status", "fieldtype": "Data", "width": 140}]

	ranges = get_period_date_ranges(filters)

	for _dummy, end_date in ranges:
		period = get_period(end_date, filters)

		columns.append({"label": _(period), "fieldname": scrub(period), "fieldtype": "Float", "width": 120})

	return columns


def get_periodic_data(filters, entry):
	periodic_data = {
		"Not Started": {},
		"Overdue": {},
		"Pending": {},
		"Completed": {},
		"Closed": {},
		"Stopped": {},
	}

	ranges = get_period_date_ranges(filters)

	for from_date, end_date in ranges:
		period = get_period(end_date, filters)
		for d in entry:
			if getdate(from_date) <= getdate(d.creation) <= getdate(end_date) and d.status not in [
				"Draft",
				"Submitted",
				"Completed",
				"Cancelled",
			]:
				if d.status in ["Not Started", "Closed", "Stopped"]:
					periodic_data = update_periodic_data(periodic_data, d.status, period)
				elif getdate(today()) > getdate(d.planned_end_date):
					periodic_data = update_periodic_data(periodic_data, "Overdue", period)
				elif getdate(today()) < getdate(d.planned_end_date):
					periodic_data = update_periodic_data(periodic_data, "Pending", period)

			if (
				getdate(from_date) <= getdate(d.actual_end_date) <= getdate(end_date)
				and d.status == "Completed"
			):
				periodic_data = update_periodic_data(periodic_data, "Completed", period)

	return periodic_data


def update_periodic_data(periodic_data, status, period):
	if periodic_data.get(status).get(period):
		periodic_data[status][period] += 1
	else:
		periodic_data[status][period] = 1

	return periodic_data


def get_data(filters, columns):
	data = []
	entry = frappe.get_all(
		"Work Order",
		fields=[
			"creation",
			"actual_end_date",
			"planned_end_date",
			"status",
		],
		filters={"docstatus": 1, "company": filters["company"]},
	)

	periodic_data = get_periodic_data(filters, entry)

	labels = ["Not Started", "Overdue", "Pending", "Completed", "Closed", "Stopped"]
	chart_data = get_chart_data(periodic_data, columns)
	ranges = get_period_date_ranges(filters)

	for label in labels:
		work = {}
		work["Status"] = _(label)
		for _dummy, end_date in ranges:
			period = get_period(end_date, filters)
			if periodic_data.get(label).get(period):
				work[scrub(period)] = periodic_data.get(label).get(period)
			else:
				work[scrub(period)] = 0.0
		data.append(work)

	return data, chart_data


def get_chart_data(periodic_data, columns):
	labels = [d.get("label") for d in columns[1:]]

	not_start, overdue, pending, completed, closed, stopped = [], [], [], [], [], []
	datasets = []

	for d in labels:
		not_start.append(periodic_data.get("Not Started").get(d))
		overdue.append(periodic_data.get("Overdue").get(d))
		pending.append(periodic_data.get("Pending").get(d))
		completed.append(periodic_data.get("Completed").get(d))
		closed.append(periodic_data.get("Closed").get(d))
		stopped.append(periodic_data.get("Stopped").get(d))

	datasets.append({"name": _("Not Started"), "values": not_start})
	datasets.append({"name": _("Overdue"), "values": overdue})
	datasets.append({"name": _("Pending"), "values": pending})
	datasets.append({"name": _("Completed"), "values": completed})
	datasets.append({"name": _("Closed"), "values": closed})
	datasets.append({"name": _("Stopped"), "values": stopped})

	chart = {"data": {"labels": labels, "datasets": datasets}}
	chart["type"] = "line"

	return chart
