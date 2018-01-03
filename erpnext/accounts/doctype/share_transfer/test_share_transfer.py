# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe import ValidationError

test_dependencies = ["Shareholder", "Share Type"]

class TestShareTransfer(unittest.TestCase):
	def test_invalid_share_purchase(self):
		doc = frappe.get_doc({
			"doctype": "Share Transfer",
			"transfer_type": "Purchase",
			"date": "2018-01-04",
			"from_shareholder": "SH00001",
			"share_type": "Class A",
			"no_of_shares": 10,
			"rate": 10.00,
			"company": "Stark Tower"
		})
		self.assertRaises(ValidationError, doc.insert)

	def test_invalid_share_transfer(self):
		doc = frappe.get_doc({
			"doctype": "Share Transfer",
			"transfer_type": "Transfer",
			"date": "2018-01-04",
			"from_shareholder": "SH00001",
			"to_shareholder": "SH00000",
			"share_type": "Class A",
			"no_of_shares": 10,
			"rate": 10.00,
			"company": "Stark Tower"
		})
		self.assertRaises(ValidationError, doc.insert)
