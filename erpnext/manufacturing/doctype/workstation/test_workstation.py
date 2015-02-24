# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_dependencies = ["Warehouse"]
test_records = frappe.get_test_records('Workstation')

class TestWorkstation(unittest.TestCase):

	def test_validate_timings(self):
		wks = frappe.get_doc("Workstation", "_Test Workstation 1")
		self.assertEqual(1,wks.check_workstation_for_operation_time("2013-02-01 05:00:00", "2013-02-02 20:00:00"))
		self.assertEqual(None,wks.check_workstation_for_operation_time("2013-02-03 10:00:00", "2013-02-03 20:00:00"))
