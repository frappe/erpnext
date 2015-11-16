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

	allocations = get_allocated_leaves(employee_names, filters)
	
	la = get_leave_allocation_record(filters.get("from_date"))
	till_date_leaves = get_leaves_till_from_date(employee_names, la.from_date, filters.get("from_date"))
	
	applications = get_leave_applications_for_filtered_dates(employee_names, filters)

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

	for d in till_date_leaves:
		data.setdefault((d.employee, d.leave_type), frappe._dict()).till_date_leaves = d.till_date_leaves

	for d in applications:
		data.setdefault((d.employee, d.leave_type), frappe._dict()).leaves = d.leaves
	
	result = []
	for employee in employees:
		row = [employee.name, employee.employee_name, employee.department]
		result.append(row)
		for leave_type in leave_types:
			tmp = data.get((employee.name, leave_type), frappe._dict())
			opening_balance = (tmp.allocation or 0) - (tmp.till_date_leaves or 0)
			
			row.append(opening_balance)
			row.append(tmp.leaves or 0)
			row.append(opening_balance - (tmp.leaves or 0))

	return columns, result

def get_allocated_leaves(employee_names, filters):
	return frappe.db.sql("""select sum(new_leaves_allocated) as leaves_allocated,
			leave_type, employee from `tabLeave Allocation` 
				where docstatus = 1 and employee in (%(employee)s) 
				and (from_date <= '%(from_date)s' and  to_date >= '%(to_date)s')
					or (from_date between '%(from_date)s' and '%(to_date)s' 
					or to_date between '%(from_date)s' and '%(to_date)s') 
				group by employee,leave_type """ % {"employee":','.join(['%s']*len(employee_names)), 
			"from_date": filters.get("from_date"), "to_date": filters.get("to_date")}, employee_names, as_dict=True)
	
def get_leave_allocation_record(date):
	name = frappe.db.sql("""select name from `tabLeave Allocation` 
		where %s between from_date and to_date """,(date), as_list=1)
	
	if name and name[0][0]:
		return frappe.get_doc("Leave Allocation", name[0][0])
	
	else:
		frappe.throw(_("No leave allocated for period"))

def get_leaves_till_from_date(employee_names, from_date, to_date):
	till_date_leaves = frappe.db.sql("""select employee, leave_type,
		SUM(total_leave_days) as till_date_leaves from `tabLeave Application`
			where status="Approved" and docstatus = 1 
			and employee in (%(employee)s) 
			and (from_date between '%(from_date)s' and '%(to_date)s' 
				or to_date between '%(from_date)s' and '%(to_date)s') 
			and to_date < '%(to_date)s'
			group by employee, leave_type""" % {"employee":','.join(['%s']*len(employee_names)), 
		"from_date": from_date, "to_date": to_date}, employee_names, as_dict=True)
			
	return till_date_leaves

def get_leave_applications_for_filtered_dates(employee_names, filters):
	return frappe.db.sql("""select employee, leave_type,
		SUM(total_leave_days) as leaves from `tabLeave Application`
			where status="Approved" and docstatus = 1 
			and employee in (%(employee)s) and (from_date between '%(from_date)s' and '%(to_date)s' 
				or to_date between '%(from_date)s' and '%(to_date)s') 
			group by employee, leave_type""" % {"employee": ','.join(['%s']*len(employee_names)),
		"from_date": filters.get("from_date"), "to_date": filters.get("to_date")}, employee_names, as_dict=True)
