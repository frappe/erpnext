# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestDriver(ERPNextTestSuite):
	def test_expiry_cannot_precede_issuing_date(self):
		driver = frappe.get_doc(
			{
				"doctype": "Driver",
				"full_name": "Test Driver",
				"status": "Active",
				"issuing_date": "2025-01-01",
				"expiry_date": "2020-01-01",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			driver.insert()
