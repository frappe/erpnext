# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.exceptions import ValidationError
import unittest

class TestQualityInspection(unittest.TestCase):
	def test_stock_no(self):
		self.assertRaises(ValidationError, frappe.get_doc({
			"doctype": "Quality Inspection",
			"name": "_Test Quality Inspection 1",
			"inspection_type": "Manufacture",
			"report_date": "12-09-2014",
			"item_code" : "_Test Item",
			"sample_size": "1",
			"inspected_by": "test Inspector",
			"stock_entry_no": ""
		}).save)
