# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, getdate

from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_employee


class TestEmployeePromotion(unittest.TestCase):
	def setUp(self):
		self.employee = make_employee("employee@promotions.com")
		frappe.db.sql("""delete from `tabEmployee Promotion`""")

	def test_submit_before_promotion_date(self):
		promotion_obj = frappe.get_doc(
			{
				"doctype": "Employee Promotion",
				"employee": self.employee,
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
		promotion_obj.promotion_date = add_days(getdate(), 1)
		promotion_obj.save()
		self.assertRaises(frappe.DocstatusTransitionError, promotion_obj.submit)
		promotion = frappe.get_doc("Employee Promotion", promotion_obj.name)
		promotion.promotion_date = getdate()
		promotion.submit()
		self.assertEqual(promotion.docstatus, 1)
