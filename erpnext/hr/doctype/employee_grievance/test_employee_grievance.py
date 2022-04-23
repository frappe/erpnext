# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import today
from erpnext.hr.doctype.employee.test_employee import make_employee
class TestEmployeeGrievance(unittest.TestCase):
	def test_create_employee_grievance(self):
		create_employee_grievance()

def create_employee_grievance():
	grievance_type = create_grievance_type()
	emp_1 = make_employee("test_emp_grievance_@example.com", company="_Test Company")
	emp_2 = make_employee("testculprit@example.com", company="_Test Company")

	grievance = frappe.new_doc("Employee Grievance")
	grievance.subject = "Test Employee Grievance"
	grievance.raised_by = emp_1
	grievance.date = today()
	grievance.grievance_type = grievance_type
	grievance.grievance_against_party = "Employee"
	grievance.grievance_against = emp_2
	grievance.description = "test descrip"

	#set cause
	grievance.cause_of_grievance = "test cause"

	#resolution details
	grievance.resolution_date = today()
	grievance.resolution_detail = "test resolution detail"
	grievance.resolved_by = "test_emp_grievance_@example.com"
	grievance.employee_responsible = emp_2
	grievance.status = "Resolved"

	grievance.save()
	grievance.submit()

	return grievance


def create_grievance_type():
	if frappe.db.exists("Grievance Type", "Employee Abuse"):
		return frappe.get_doc("Grievance Type", "Employee Abuse")
	grievance_type = frappe.new_doc("Grievance Type")
	grievance_type.name = "Employee Abuse"
	grievance_type.description = "Test"
	grievance_type.save()

	return grievance_type.name

