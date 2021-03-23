# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	return columns, data

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
			"fieldname": "title",
			"label": _("Name"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "employee",
			"width": 150
		},
		{
			"fieldname": "grand_total",
			"label": _("Bill Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "gross_pay",
			"label": _("Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "profit",
			"label": _("Profit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "end_date",
			"label": _("End Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "total_billed_hours",
			"label": _("Total Billed Hours"),
			"fieldtype": "Int",
			"width": 120
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
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	sql = """ 
			select 
				*, 
				t.gross_pay * t.utilization as fractional_cost, 
				t.grand_total - t.gross_pay * t.utilization as profit
			from 
				(select
				si.customer_name,tabTimesheet.title,tabTimesheet.employee,si.grand_total,si.name as voucher_no,
				ss.gross_pay,ss.total_working_days,tabTimesheet.end_date,tabTimesheet.total_billed_hours,
				tabTimesheet.total_billed_hours/(ss.total_working_days * 8) as utilization
				from 
					`tabSalary Slip Timesheet` as sst join `tabTimesheet` on tabTimesheet.name = sst.time_sheet
					join `tabSales Invoice Timesheet` as sit on sit.time_sheet = tabTimesheet. name
					join `tabSales Invoice` as si on si. name = sit.parent and si.status != "Cancelled"
					join `tabSalary Slip` as ss on ss.name = sst.parent and ss.status != "Cancelled" """
	if conditions:
		sql += """
				where
					%s) as t"""%(conditions)
	data = frappe.db.sql(sql,filters, as_dict=True)

	return data

def get_conditions(filters):
	conditions = []
	if filters.get("customer_name"):
		conditions.append("si.customer_name='%s'"%filters.get("customer_name"))
	if filters.get("start_date"):
		conditions.append("tabTimesheet.start_date>='%s'"%filters.get("start_date"))
	if filters.get("end_date"):
		conditions.append("tabTimesheet.end_date<='%s'"%filters.get("end_date"))
	if filters.get("employee"):
		conditions.append("tabTimesheet.employee='%s'"%filters.get("employee"))
	conditions = " and ".join(conditions)
	return conditions