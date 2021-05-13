# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import today, add_days, get_date_str
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.employee_grievance.employee_grievance import create_additional_salary, suspend_employee, unsuspend_employee

class TestEmployeeGrievance(unittest.TestCase):
	def tearDown(self):
		frappe.db.sql("DELETE FROM `tabEmployee Grievance`")
		frappe.db.sql("DELETE FROM `tabGrievance Type`")

	def test_creation_paycut_suspension_and_unsuspension(self):
		grievance = create_employee_grievance()

		# Pay cut Creation
		pay_cut_doc = create_additional_salary(grievance)
		self.assertEqual(grievance.employee_responsible, pay_cut_doc.employee)
		self.assertEqual(pay_cut_doc.type, "Deduction")
		self.assertEqual(pay_cut_doc.ref_docname, grievance.name)
		self.assertEqual(pay_cut_doc.ref_doctype, "Employee Grievance")

		# suspension
		suspend_employee(grievance.name)
		grievance.reload()
		self.assertEqual(today(), get_date_str(grievance.suspended_from))
		self.assertEqual(add_days(today(), 30), get_date_str(grievance.suspended_to))

		# unsuspension
		unsuspend_employee(grievance.name)
		grievance.reload()
		self.assertEqual(today(), get_date_str(grievance.unsuspended_on))

def create_employee_grievance():
	grievance_type = create_grievance_type()
	emp_1 = make_employee("test_emp_grievance_@example.com", company="_Test Company")
	emp_2 = make_employee("testculprit@example.com", company="_Test Company")

	grievance = frappe.new_doc("Employee Grievance")
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
	grievance_type.name="Employee Abuse"
	grievance_type.is_applicable_for_pay_cut = 1
	grievance_type.is_applicable_for_suspension = 1
	grievance_type.number_of_days_for_suspension = 30
	grievance_type.description = "Test"

	grievance_type.save()

	return grievance_type.name

