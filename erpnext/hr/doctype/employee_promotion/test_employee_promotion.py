# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_employee


class TestEmployeePromotion(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Employee Promotion")

	def test_submit_before_promotion_date(self):
		employee = make_employee("employee@promotions.com")
		promotion = frappe.get_doc(
			{
				"doctype": "Employee Promotion",
				"employee": employee,
				"promotion_details": [
					{
						"property": "Designation",
						"current": "Software Developer",
						"new": "Project Manager",
						"fieldname": "designation",
					}
				],
			}
		)
		promotion.promotion_date = add_days(getdate(), 1)
		self.assertRaises(frappe.DocstatusTransitionError, promotion.submit)

		promotion.promotion_date = getdate()
		promotion.submit()
		self.assertEqual(promotion.docstatus, 1)

	def test_employee_history(self):
		for grade in ["L1", "L2"]:
			frappe.get_doc({"doctype": "Employee Grade", "__newname": grade}).insert()

		employee = make_employee(
			"test_employee_promotion@example.com",
			company="_Test Company",
			date_of_birth=getdate("30-09-1980"),
			date_of_joining=getdate("01-10-2021"),
			designation="Software Developer",
			grade="L1",
			salary_currency="INR",
			ctc="500000",
		)

		promotion = frappe.get_doc(
			{
				"doctype": "Employee Promotion",
				"employee": employee,
				"promotion_date": getdate(),
				"revised_ctc": "1000000",
				"promotion_details": [
					{
						"property": "Designation",
						"current": "Software Developer",
						"new": "Project Manager",
						"fieldname": "designation",
					},
					{"property": "Grade", "current": "L1", "new": "L2", "fieldname": "grade"},
				],
			}
		).submit()

		# employee fields updated
		employee = frappe.get_doc("Employee", employee)
		self.assertEqual(employee.grade, "L2")
		self.assertEqual(employee.designation, "Project Manager")
		self.assertEqual(employee.ctc, 1000000)

		# internal work history updated
		self.assertEqual(employee.internal_work_history[0].designation, "Software Developer")
		self.assertEqual(employee.internal_work_history[0].from_date, getdate("01-10-2021"))

		self.assertEqual(employee.internal_work_history[1].designation, "Project Manager")
		self.assertEqual(employee.internal_work_history[1].from_date, getdate())

		promotion.cancel()
		employee.reload()

		# fields restored
		self.assertEqual(employee.grade, "L1")
		self.assertEqual(employee.designation, "Software Developer")
		self.assertEqual(employee.ctc, 500000)

		# internal work history updated on cancellation
		self.assertEqual(len(employee.internal_work_history), 1)
		self.assertEqual(employee.internal_work_history[0].designation, "Software Developer")
		self.assertEqual(employee.internal_work_history[0].from_date, getdate("01-10-2021"))
