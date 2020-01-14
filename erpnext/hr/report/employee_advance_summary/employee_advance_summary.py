# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	advances_list = get_advances(filters)
	columns = get_columns()

	if not advances_list:
		msgprint(_("No record found"))
		return columns, advances_list

	data = []
	for advance in advances_list:
		row = [advance.name, advance.employee, advance.company, advance.posting_date,
		advance.advance_amount, advance.paid_amount,  advance.claimed_amount, advance.status]
		data.append(row)

	return columns, data


def get_columns():
	return [
		{
			"label": _("Title"),
			"fieldname": "title",
			"fieldtype": "Link",
			"options": "Employee Advance",
			"width": 120
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": _("Advance Amount"),
			"fieldname": "advance_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Claimed Amount"),
			"fieldname": "claimed_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120
		}
	]

def get_conditions(filters):
	conditions = ""

	if filters.get("employee"):
		conditions += "and employee = %(employee)s"
	if filters.get("company"):
		conditions += " and company = %(company)s"
	if filters.get("status"):
		conditions += " and status = %(status)s"
	if filters.get("from_date"):
		conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"):
		conditions += " and posting_date<=%(to_date)s"

	return conditions

def get_advances(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, employee, paid_amount, status, advance_amount, claimed_amount, company,
		posting_date, purpose
		from `tabEmployee Advance`
		where docstatus<2 %s order by posting_date, name desc""" %
		conditions, filters, as_dict=1)
