# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import os

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSerialNoWarrantyExpiry(ERPNextTestSuite):
	def get_report_spec(self):
		path = os.path.join(os.path.dirname(__file__), "serial_no_warranty_expiry.json")
		return json.loads(json.load(open(path))["json"])

	def test_report_shows_the_warranty_expiry_date(self):
		spec = self.get_report_spec()

		self.assertIn(["warranty_expiry_date", "Serial No"], spec["columns"])
		self.assertEqual(spec["sort_by"], "Serial No.warranty_expiry_date")
