# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document


class EmployeeAttendanceTool(Document):
	pass


@frappe.whitelist()
def get_employees(date, department=None, branch=None, company=None):
	attendance_not_marked = []
	attendance_marked = []
	employee_list = frappe.get_list("Employee", fields=["employee", "employee_name"], filters={
		"status": "Active", "department": department, "branch": branch, "company": company}, order_by="employee_name")
	marked_employee = {}
	for emp in frappe.get_list("Attendance", fields=["employee", "status"],
							   filters={"att_date": date}):
		marked_employee[emp['employee']] = emp['status']

	for employee in employee_list:
		employee['status'] = marked_employee.get(employee['employee'])
		if employee['employee'] not in marked_employee:
			attendance_not_marked.append(employee)
		else:
			attendance_marked.append(employee)
	return {
		"marked": attendance_marked,
		"unmarked": attendance_not_marked
	}

from datetime import timedelta, date

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)
        
@frappe.whitelist()
def mark_employee_attendance_bulk():
	from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
	from datetime import date
	from frappe.utils import getdate,cstr
	from frappe.utils.data import today, add_to_date
	
	employee_list = frappe.get_list("Employee",fields=["*"])
	status = "Present"
	company = "Tawari"
	
	start_date = getdate("2017-01-01")
	end_date = getdate("2017-05-20")
	
	if employee_list:
		for employee in employee_list :
			print employee
			holiday_list = get_holiday_list_for_employee(employee.name)
			holidays = frappe.db.sql_list('''select holiday_date from `tabHoliday`
				where
					parent=%(holiday_list)s
					and holiday_date >= %(start_date)s
					and holiday_date <= %(end_date)s''', {
						"holiday_list": holiday_list,
						"start_date": start_date,
						"end_date": end_date
					})

			#~ holidays = [cstr(i) for i in holidays]
			print holidays
			for single_date in daterange(start_date, end_date):
				if single_date in holidays:
					print "IN LIST"+single_date.strftime("%Y-%m-%d")
				else:
					print single_date.strftime("%Y-%m-%d")
					attendance = frappe.new_doc("Attendance")
					attendance.employee = employee['name']
					attendance.employee_name = employee['employee_name']
					attendance.att_date = single_date
					attendance.attendance_date = single_date
					attendance.status = status
					if company:
						attendance.company = company
					else:
						attendance.company = frappe.db.get_value("Employee", employee['employee'], "Company")
					attendance.submit()
	#~ for employee in employee_list:
		#~ attendance = frappe.new_doc("Attendance")
		#~ attendance.employee = employee['employee']
		#~ attendance.employee_name = employee['employee_name']
		#~ attendance.att_date = date
		#~ attendance.attendance_date = date
		#~ attendance.status = status
		#~ if company:
			#~ attendance.company = company
		#~ else:
			#~ attendance.company = frappe.db.get_value("Employee", employee['employee'], "Company")
		#~ attendance.submit()
	
@frappe.whitelist()
def mark_employee_attendance(employee_list, status, date, company=None):
	employee_list = json.loads(employee_list)
	for employee in employee_list:
		attendance = frappe.new_doc("Attendance")
		attendance.employee = employee['employee']
		attendance.employee_name = employee['employee_name']
		attendance.att_date = date
		attendance.attendance_date = date
		attendance.status = status
		if company:
			attendance.company = company
		else:
			attendance.company = frappe.db.get_value("Employee", employee['employee'], "Company")
		attendance.submit()
