# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model import get_permitted_fields
from frappe.utils import flt


def get_unbilled_time(project: str) -> dict | None:
	"""Billable time on the project's submitted Timesheets that is not yet on a Sales Invoice.

	None when the user can't read Timesheets or their billing amount, so the overview leaves the Unbilled
	card out; hours are None when the user's permission levels hide them.
	"""
	if not frappe.has_permission("Timesheet", "read"):
		return None
	permitted = get_permitted_fields("Timesheet Detail", parenttype="Timesheet", permission_type="read")
	if "base_billing_amount" not in permitted:
		return None

	logs = unbilled_time_logs(project)
	return {
		# a Timesheet converts its billing into the site's default currency, not the company's
		"currency": frappe.defaults.get_global_default("currency"),
		"amount": sum(flt(log.base_billing_amount) for log in logs),
		"hours": sum(flt(log.billing_hours) for log in logs) if "billing_hours" in permitted else None,
	}


def unbilled_time_logs(project: str) -> list[frappe._dict]:
	# get_list, so the user's Timesheet permissions decide which ones count
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
