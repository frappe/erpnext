# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: See license.txt

from __future__ import unicode_literals

import frappe
test_records = frappe.get_test_records('Address Template')

import unittest
import frappe

class TestAddressTemplate(unittest.TestCase):
	def test_default_is_unset(self):
		a = frappe.get_doc("Address Template", "India")
		a.is_default = 1
		a.save()

		b = frappe.get_doc("Address Template", "Brazil")
		b.is_default = 1
		b.save()

		self.assertEqual(frappe.db.get_value("Address Template", "India", "is_default"), 0)

	def tearDown(self):
		a = frappe.get_doc("Address Template", "India")
		a.is_default = 1
		a.save()
