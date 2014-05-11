# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.widgets.reportview import execute as runreport

def execute(filters=None):
	if not filters: filters = {}
	
	employee_filters = filters.get("company") and \
		[["Employee", "company", "=", filters.get("company")]] or None
	employees = runreport(doctype="Employee", fields=["name", "employee_name", "department"],
		filters=employee_filters)
	leave_types = webnotes.conn.sql_list("select name from `tabLeave Type`")
	
	if filters.get("fiscal_year"):
		fiscal_years = [filters["fiscal_year"]]
	else:
		fiscal_years = webnotes.conn.sql_list("select name from `tabFiscal Year` order by name desc")
		
	employee_in = '", "'.join([e.name for e in employees])
	
	allocations = webnotes.conn.sql("""select employee, fiscal_year, leave_type, total_leaves_allocated
	 	from `tabLeave Allocation` 
		where docstatus=1 and employee in ("%s")""" % employee_in, as_dict=True)
	applications = webnotes.conn.sql("""select employee, fiscal_year, leave_type, SUM(total_leave_days) as leaves
			from `tabLeave Application` 
			where status="Approved" and docstatus = 1 and employee in ("%s")
			group by employee, fiscal_year, leave_type""" % employee_in, as_dict=True)
	
	columns = [
		"Fiscal Year", "Employee:Link/Employee:150", "Employee Name::200", "Department::150"
	]
	
	for leave_type in leave_types:
		columns.append(leave_type + " Allocated:Float")
		columns.append(leave_type + " Taken:Float")
		columns.append(leave_type + " Balance:Float")

	data = {}
	for d in allocations:
		data.setdefault((d.fiscal_year, d.employee, 
			d.leave_type), webnotes._dict()).allocation = d.total_leaves_allocated

	for d in applications:
		data.setdefault((d.fiscal_year, d.employee, 
			d.leave_type), webnotes._dict()).leaves = d.leaves
	
	result = []
	for fiscal_year in fiscal_years:
		for employee in employees:
			row = [fiscal_year, employee.name, employee.employee_name, employee.department]
			result.append(row)
			for leave_type in leave_types:
				tmp = data.get((fiscal_year, employee.name, leave_type), webnotes._dict())
				row.append(tmp.allocation or 0)
				row.append(tmp.leaves or 0)
				row.append((tmp.allocation or 0) - (tmp.leaves or 0))

	return columns, result