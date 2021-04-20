# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import get_employee_currency
from erpnext.accounts.utils import get_currency_precision
from frappe.utils import flt
from erpnext.setup.utils import get_exchange_rate

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	charts = get_chart_data(data)
	return columns, data, None, charts

def get_data(filters):
	data = get_rows(filters)
	data = handle_multi_currency(data, filters)
	data = calculate_cost_and_profit(data)
	return data

def get_rows(filters):
	conditions = get_conditions(filters)
	standard_working_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours")
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
						join `tabSalary Slip` as ss on ss.name = sst.parent and ss.status != "Cancelled" """.format(standard_working_hours)
	if conditions:
		sql += """
				WHERE
					{0}) as t""".format(conditions)
	return frappe.db.sql(sql,filters, as_dict=True)

def handle_multi_currency(data, filters):
	currency_precision = get_currency_precision() or 2
	company_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")
	
	for row in data:
		row.currency = company_currency

		if filters.get("employee"):
			party_currency = get_employee_currency(row.employee)

		if filters.get("customer_name"):
			party_currency = frappe.db.get_value("Customer", row.customer_name, ["default_currency"])

			if party_currency and party_currency != company_currency:
				exchange_rate = get_exchange_rate(company_currency, party_currency)
				row.currency = party_currency

				row.base_grand_total = flt(flt(row.base_grand_total) *
				flt(exchange_rate), currency_precision)

				row.base_gross_pay = flt(flt(row.base_gross_pay) *
				flt(exchange_rate), currency_precision)

				row.profit = flt(flt(row.profit) *
				flt(exchange_rate), currency_precision)

				row.fractional_cost = flt(flt(row.fractional_cost) *
				flt(exchange_rate), currency_precision)

	return data

def calculate_cost_and_profit(data):
	for row in data:
		row.fractional_cost = row.base_gross_pay * row.utilization
		row.profit = row.base_grand_total - row.base_gross_pay * row.utilization
	return data

def get_conditions(filters):
	conditions = []

	if filters.get("company"):
		conditions.append("tabTimesheet.company='{0}'".format(filters.get("company")))

	if filters.get("start_date"):
		conditions.append("tabTimesheet.start_date>='{0}'".format(filters.get("start_date")))

	if filters.get("end_date"):
		conditions.append("tabTimesheet.end_date<='{0}'".format(filters.get("end_date")))

	if filters.get("customer_name"):
		conditions.append("si.customer_name='{0}'".format(filters.get("customer_name")))

	if filters.get("employee"):
		conditions.append("tabTimesheet.employee='{0}'".format(filters.get("employee")))

	if filters.get("project"):
		conditions.append("tabTimesheet.parent_project='{0}'".format(filters.get("project")))
	
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
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": "Utilization",
					"values": utilization
				}
			]
		},
		"type": "bar",
		"colors": ["#84BDD5"]
	}
	return charts

def get_columns():
	return [
		{
			"fieldname": "customer_name",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "voucher_no",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 180
		},
		{
			"fieldname": "timesheet",
			"label": _("Timesheet"),
			"fieldtype": "Link",
			"options": "Timesheet",
			"width": 130
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 100
		},
		{
			"fieldname": "base_grand_total",
			"label": _("Bill Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100
		},
		{
			"fieldname": "base_gross_pay",
			"label": _("Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100
		},
		{
			"fieldname": "profit",
			"label": _("Profit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100
		},
		{
			"fieldname": "utilization",
			"label": _("Utilization"),
			"fieldtype": "Percentage",
			"width": 120
		},
		{
			"fieldname": "fractional_cost",
			"label": _("Fractional Cost"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_billed_hours",
			"label": _("Total Billed Hours"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "start_date",
			"label": _("Start Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "end_date",
			"label": _("End Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100
		}
	]