# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	charts = get_chart_data(data)
	return columns, data, None, charts


def get_data(filters):
	data = get_rows(filters)
	data = calculate_cost_and_profit(data)
	return data


def get_rows(filters):
	conditions = get_conditions(filters)
	standard_working_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours")
	if not standard_working_hours:
		msg = _(
			"The metrics for this report are calculated based on the Standard Working Hours. Please set {0} in {1}."
		).format(
			frappe.bold("Standard Working Hours"),
			frappe.utils.get_link_to_form("HR Settings", "HR Settings"),
		)

		frappe.msgprint(msg)
		return []

	sql = """
			SELECT
				*
			FROM
				(SELECT
					si.customer_name,si.base_grand_total,
					si.name as voucher_no,tabTimesheet.employee,
					tabTimesheet.title as employee_name,tabTimesheet.parent_project as project,
					tabTimesheet.start_date,tabTimesheet.end_date,
					tabTimesheet.total_billed_hours,tabTimesheet.name as timesheet,
					ss.base_gross_pay,ss.total_working_days,
					tabTimesheet.total_billed_hours/(ss.total_working_days * {0}) as utilization
					FROM
						`tabSalary Slip Timesheet` as sst join `tabTimesheet` on tabTimesheet.name = sst.time_sheet
						join `tabSales Invoice Timesheet` as sit on sit.time_sheet = tabTimesheet.name
						join `tabSales Invoice` as si on si.name = sit.parent and si.status != "Cancelled"
						join `tabSalary Slip` as ss on ss.name = sst.parent and ss.status != "Cancelled" """.format(
		standard_working_hours
	)
	if conditions:
		sql += """
				WHERE
					{0}) as t""".format(
			conditions
		)
	return frappe.db.sql(sql, filters, as_dict=True)


def calculate_cost_and_profit(data):
	for row in data:
		row.fractional_cost = flt(row.base_gross_pay) * flt(row.utilization)
		row.profit = flt(row.base_grand_total) - flt(row.base_gross_pay) * flt(row.utilization)
	return data


def get_conditions(filters):
	conditions = []

	if filters.get("company"):
		conditions.append("tabTimesheet.company={0}".format(frappe.db.escape(filters.get("company"))))

	if filters.get("start_date"):
		conditions.append("tabTimesheet.start_date>='{0}'".format(filters.get("start_date")))

	if filters.get("end_date"):
		conditions.append("tabTimesheet.end_date<='{0}'".format(filters.get("end_date")))

	if filters.get("customer_name"):
		conditions.append("si.customer_name={0}".format(frappe.db.escape(filters.get("customer_name"))))

	if filters.get("employee"):
		conditions.append("tabTimesheet.employee={0}".format(frappe.db.escape(filters.get("employee"))))

	if filters.get("project"):
		conditions.append(
			"tabTimesheet.parent_project={0}".format(frappe.db.escape(filters.get("project")))
		)

	conditions = " and ".join(conditions)
	return conditions


def get_chart_data(data):
	if not data:
		return None

	labels = []
	utilization = []

	for entry in data:
		labels.append(entry.get("employee_name") + " - " + str(entry.get("end_date")))
		utilization.append(entry.get("utilization"))

	charts = {
		"data": {"labels": labels, "datasets": [{"name": "Utilization", "values": utilization}]},
		"type": "bar",
		"colors": ["#84BDD5"],
	}
	return charts


def get_columns():
	return [
		{
			"fieldname": "customer_name",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 120},
		{
			"fieldname": "voucher_no",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 120,
		},
		{
			"fieldname": "timesheet",
			"label": _("Timesheet"),
			"fieldtype": "Link",
			"options": "Timesheet",
			"width": 120,
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 100,
		},
		{
			"fieldname": "base_grand_total",
			"label": _("Bill Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"fieldname": "base_gross_pay",
			"label": _("Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"fieldname": "profit",
			"label": _("Profit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{"fieldname": "utilization", "label": _("Utilization"), "fieldtype": "Percentage", "width": 100},
		{
			"fieldname": "fractional_cost",
			"label": _("Fractional Cost"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "total_billed_hours",
			"label": _("Total Billed Hours"),
			"fieldtype": "Int",
			"width": 150,
		},
		{"fieldname": "start_date", "label": _("Start Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "end_date", "label": _("End Date"), "fieldtype": "Date", "width": 100},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
	]
