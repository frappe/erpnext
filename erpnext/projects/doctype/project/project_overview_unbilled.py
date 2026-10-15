# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt


def get_unbilled_time(project: str) -> dict | None:
	"""Billable time on the project's submitted Timesheets that is not yet on a Sales Invoice.

	None when the user can't read Timesheets, so the overview leaves the Unbilled card out.
	"""
	if not frappe.has_permission("Timesheet", "read"):
		return None

	logs = unbilled_time_logs(project)
	company = frappe.db.get_value("Project", project, "company")
	return {
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"amount": sum(flt(log.base_billing_amount) for log in logs),
		"hours": sum(flt(log.billing_hours) for log in logs),
	}


def unbilled_time_logs(project: str) -> list[frappe._dict]:
	# Timesheets are read through get_list so the user's permissions decide which ones count
	timesheets = frappe.get_list(
		"Timesheet",
		filters=[["Timesheet Detail", "project", "=", project], ["docstatus", "=", 1]],
		pluck="name",
		distinct=True,
		limit_page_length=0,
	)
	if not timesheets:
		return []

	return frappe.get_all(
		"Timesheet Detail",
		filters={
			"parenttype": "Timesheet",
			"parent": ["in", timesheets],
			"project": project,
			"is_billable": 1,
			"sales_invoice": ["is", "not set"],
		},
		fields=["base_billing_amount", "billing_hours"],
	)
