# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.exceptions import ValidationError
import unittest

class TestBatch(unittest.TestCase):
	def test_item_has_batch_enabled(self):
		self.assertRaises(ValidationError, frappe.get_doc({
			"doctype": "Batch",
			"name": "_test Batch",
			"item": "_Test Item"
		}).save)