# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.desk.reportview import execute as runreport

def execute(filters=None):
	if not filters: filters = {}

	employee_filters = {
		"status": "Active"
	}
	
	if filters.get("company"):
		filters["company"] = filters.company

	employees = runreport(doctype="Employee", fields=["name", "employee_name", "department"],
		filters=employee_filters, limit_page_length=None)

	if not employees:
		frappe.throw(_("No employee found!"))

	leave_types = frappe.db.sql_list("select name from `tabLeave Type`")

	employee_names = [d.name for d in employees]

	allocations = frappe.db.sql("""select employee, leave_type, sum(new_leaves_allocated) as leaves_allocated
	 	from `tabLeave Allocation`
		where docstatus=1 and employee in (%s) and to_date >= '%s' and from_date <= '%s' """ %
		(','.join(['%s']*len(employee_names)), filters.get("from_date"),
		 filters.get("to_date")), employee_names, as_dict=True)
		
	applications = frappe.db.sql("""select employee, leave_type,
			SUM(total_leave_days) as leaves
		from `tabLeave Application`
		where status="Approved" and docstatus = 1 and employee in (%s)
		and to_date >= '%s' and from_date <= '%s' 
		group by employee, leave_type""" %
		(','.join(['%s']*len(employee_names)), filters.get("from_date"),
		 filters.get("to_date")), employee_names, as_dict=True)

	columns = [
		_("Employee") + ":Link/Employee:150", _("Employee Name") + "::200", _("Department") +"::150"
	]

	for leave_type in leave_types:
		columns.append(_(leave_type) + " " + _("Opening") + ":Float")
		columns.append(_(leave_type) + " " + _("Taken") + ":Float")
		columns.append(_(leave_type) + " " + _("Balance") + ":Float")

	data = {}
	for d in allocations:
		data.setdefault((d.employee,d.leave_type), frappe._dict()).allocation = d.leaves_allocated

	for d in applications:
		data.setdefault((d.employee, d.leave_type), frappe._dict()).leaves = d.leaves

	result = []
	for employee in employees:
		row = [employee.name, employee.employee_name, employee.department]
		result.append(row)
		for leave_type in leave_types:
			tmp = data.get((employee.name, leave_type), frappe._dict())
			row.append(tmp.allocation or 0)
			row.append(tmp.leaves or 0)
			row.append((tmp.allocation or 0) - (tmp.leaves or 0))

	return columns, result
