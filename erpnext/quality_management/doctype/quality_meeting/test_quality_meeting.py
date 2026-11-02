# Copyright (c) 2018, Frappe and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestQualityMeeting(ERPNextTestSuite):
	def test_two_meetings_on_the_same_day(self):
		first = frappe.get_doc(doctype="Quality Meeting").insert()
		second = frappe.get_doc(doctype="Quality Meeting").insert()
		self.assertNotEqual(first.name, second.name)
