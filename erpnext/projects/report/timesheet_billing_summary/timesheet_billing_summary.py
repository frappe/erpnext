import frappe
from frappe import _
from frappe.desk.query_report import get_filtered_data
from frappe.model.docstatus import DocStatus
from frappe.utils import getdate

VALUE_FIELDNAMES = ("hours", "billing_hours", "billing_amount")


def execute(filters=None):
	group_fieldname = filters.pop("group_by", None)

	filters = frappe._dict(filters or {})
	columns = get_columns(filters, group_fieldname)

	data = get_data(filters)
	data = get_filtered_data("Timesheet", columns, data, frappe.session.user)
	report_summary = get_report_summary(data)

	if group_fieldname:
		data = group_by(data, group_fieldname)

	return columns, data, None, None, report_summary, 1


def get_columns(filters, group_fieldname=None):
	group_columns = {
		"date": {
			"label": _("Date"),
			"fieldtype": "Date",
			"fieldname": "date",
			"width": 150,
		},
		"project": {
			"label": _("Project"),
			"fieldtype": "Link",
			"fieldname": "project",
			"options": "Project",
			"width": 200,
			"hidden": int(bool(filters.get("project"))),
		},
		"employee": {
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Employee",
			"width": 200,
			"hidden": int(bool(filters.get("employee"))),
		},
	}
	columns = []
	if group_fieldname in group_columns:
		# the grouped column labels the group rows: keep it visible even when it is filtered too
		group_columns[group_fieldname]["hidden"] = 0
		columns.append(group_columns.pop(group_fieldname))

	columns.extend(group_columns.values())

	columns.extend(
		[
			{
				"label": _("Employee Name"),
				"fieldtype": "data",
				"fieldname": "employee_name",
				"hidden": 1,
			},
			{
				"label": _("Timesheet"),
				"fieldtype": "Link",
				"fieldname": "timesheet",
				"options": "Timesheet",
				"width": 150,
			},
			{"label": _("Working Hours"), "fieldtype": "Float", "fieldname": "hours", "width": 150},
			{
				"label": _("Billing Hours"),
				"fieldtype": "Float",
				"fieldname": "billing_hours",
				"width": 150,
			},
			{
				"label": _("Billing Amount"),
				"fieldtype": "Currency",
				"fieldname": "billing_amount",
				"width": 150,
			},
		]
	)

	return columns


def get_data(filters):
	_filters = []
	if filters.get("employee"):
		_filters.append(("employee", "=", filters.get("employee")))
	if filters.get("project"):
		_filters.append(("Timesheet Detail", "project", "=", filters.get("project")))
	if filters.get("from_date"):
		_filters.append(("Timesheet Detail", "from_time", ">=", filters.get("from_date")))
	if filters.get("to_date"):
		_filters.append(("Timesheet Detail", "to_time", "<=", filters.get("to_date") + " 23:59:59"))
	if not filters.get("include_draft_timesheets"):
		_filters.append(("docstatus", "=", DocStatus.submitted()))
	else:
		_filters.append(("docstatus", "in", (DocStatus.submitted(), DocStatus.draft())))

	data = frappe.get_list(
		"Timesheet",
		fields=[
			"name as timesheet",
			"`tabTimesheet`.employee",
			"`tabTimesheet`.employee_name",
			"`tabTimesheet Detail`.from_time as date",
			"`tabTimesheet Detail`.project",
			"`tabTimesheet Detail`.hours",
			"`tabTimesheet Detail`.billing_hours",
			"`tabTimesheet Detail`.billing_amount",
		],
		filters=_filters,
		order_by="`tabTimesheet Detail`.from_time",
	)

	return data


def group_by(data, fieldname):
	groups = {}
	for row in data:
		groups.setdefault(get_group_value(row, fieldname), []).append(row)

	grouped_data = []
	for group in sorted(groups, key=lambda g: (g is None, g)):
		hours = billing_hours = billing_amount = 0
		child_rows = []
		for row in groups[group]:
			hours += row.get("hours") or 0
			billing_hours += row.get("billing_hours") or 0
			billing_amount += row.get("billing_amount") or 0

			_row = row.copy()
			_row[fieldname] = None
			_row["indent"] = 1
			_row["is_group"] = 0
			child_rows.append(_row)

		group_row = {
			fieldname: group,
			"hours": hours,
			"billing_hours": billing_hours,
			"billing_amount": billing_amount,
			"indent": 0,
			"is_group": 1,
		}
		if fieldname == "employee":
			group_row["employee_name"] = groups[group][0].get("employee_name")

		grouped_data.append(group_row)
		grouped_data.extend(child_rows)

	return grouped_data


def get_group_value(row, fieldname):
	value = row.get(fieldname)
	# `date` is `Timesheet Detail.from_time`, a datetime: everything logged on a day is one group
	return getdate(value) if fieldname == "date" and value else value


def get_report_summary(data):
	if not data:
		return None

	totals = dict.fromkeys(VALUE_FIELDNAMES, 0.0)
	for row in data:
		for value_fieldname in VALUE_FIELDNAMES:
			totals[value_fieldname] += row.get(value_fieldname) or 0

	return [
		{
			"value": totals["hours"],
			"indicator": "Blue",
			"label": _("Total Working Hours"),
			"datatype": "Float",
		},
		{
			"value": totals["billing_hours"],
			"indicator": "Blue",
			"label": _("Total Billing Hours"),
			"datatype": "Float",
		},
		{
			"value": totals["billing_amount"],
			"indicator": "Green",
			"label": _("Total Billing Amount"),
			"datatype": "Currency",
		},
	]
