# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class EmployeeAttendanceTool(Document):
	pass


@frappe.whitelist()
def get_employees(date, department=None, branch=None, company=None):
	attendance_not_marked = []
	attendance_marked = []
	filters = {"status": "Active", "date_of_joining": ["<=", date]}

	for field, value in {"department": department, "branch": branch, "company": company}.items():
		if value:
			filters[field] = value

	employee_list = frappe.get_list(
		"Employee", fields=["employee", "employee_name"], filters=filters, order_by="employee_name"
	)
	marked_employee = {}
	for emp in frappe.get_list(
		"Attendance", fields=["employee", "status"], filters={"attendance_date": date}
	):
		marked_employee[emp["employee"]] = emp["status"]

	for employee in employee_list:
		employee["status"] = marked_employee.get(employee["employee"])
		if employee["employee"] not in marked_employee:
			attendance_not_marked.append(employee)
		else:
			attendance_marked.append(employee)
	return {"marked": attendance_marked, "unmarked": attendance_not_marked}


@frappe.whitelist()
def mark_employee_attendance(employee_list, status, date, leave_type=None, company=None):

	employee_list = json.loads(employee_list)
	for employee in employee_list:

		if status == "On Leave" and leave_type:
			leave_type = leave_type
		else:
			leave_type = None

		company = frappe.db.get_value("Employee", employee["employee"], "Company", cache=True)

		attendance = frappe.get_doc(
			dict(
				doctype="Attendance",
				employee=employee.get("employee"),
				employee_name=employee.get("employee_name"),
				attendance_date=getdate(date),
				status=status,
				leave_type=leave_type,
				company=company,
			)
		)
		attendance.insert()
		attendance.submit()
