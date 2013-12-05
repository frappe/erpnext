# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, cint
from webnotes import msgprint, _

def execute(filters=None):
	if not filters: filters = {}
	
	conditions, filters = get_conditions(filters)
	columns = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)
	emp_map = get_employee_details()
	
	data = []
	for emp in sorted(att_map):
		emp_det = emp_map.get(emp)
		row = [emp, emp_det.employee_name, emp_det.branch, emp_det.department, emp_det.designation, 
			emp_det.company]
			
		total_p = total_a = 0.0
		for day in range(filters["total_days_in_month"]):
			status = att_map.get(emp).get(day + 1, "Absent")
			status_map = {"Present": "P", "Absent": "A", "Half Day": "HD"}
			row.append(status_map[status])
			
			if status == "Present":
				total_p += 1
			elif status == "Absent":
				total_a += 1
			elif status == "Half Day":
				total_p += 0.5
				total_a += 0.5
	
		row += [total_p, total_a]
		
		data.append(row)
	
	return columns, data
	
def get_columns(filters):
	columns = [
		"Employee:Link/Employee:120", "Employee Name::140", "Branch:Link/Branch:120", 
		"Department:Link/Department:120", "Designation:Link/Designation:120",
		 "Company:Link/Company:120"
	]
	
	for day in range(filters["total_days_in_month"]):
		columns.append(cstr(day+1) +"::20")
		
	columns += ["Total Present:Float:80", "Total Absent:Float:80"]
	return columns
	
def get_attendance_list(conditions, filters):
	attendance_list = webnotes.conn.sql("""select employee, day(att_date) as day_of_month, 
		status from tabAttendance where docstatus = 1 %s order by employee, att_date""" % 
		conditions, filters, as_dict=1)
		
	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.employee, webnotes._dict()).setdefault(d.day_of_month, "")
		att_map[d.employee][d.day_of_month] = d.status

	return att_map
	
def get_conditions(filters):	
	if not (filters.get("month") and filters.get("fiscal_year")):
		msgprint(_("Please select month and year"), raise_exception=1)
		
	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
		"Dec"].index(filters["month"]) + 1
	
	from calendar import monthrange	
	filters["total_days_in_month"] = monthrange(cint(filters["fiscal_year"].split("-")[-1]), 
		filters["month"])[1]
	
	conditions = " and month(att_date) = %(month)s and fiscal_year = %(fiscal_year)s"
	
	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"
	
	return conditions, filters
	
def get_employee_details():
	employee = webnotes.conn.sql("""select name, employee_name, designation, department, 
		branch, company from tabEmployee where docstatus < 2 and status = 'Active'""", as_dict=1)
	
	emp_map = {}
	for emp in employee:
		emp_map[emp.name] = emp
		
	return emp_map