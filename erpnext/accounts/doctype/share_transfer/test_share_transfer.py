# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe import ValidationError

test_dependencies = ["Share Type", "Shareholder"]

class TestShareTransfer(unittest.TestCase):
	def test_invalid_share_transfer(self):
		doc = frappe.get_doc({
			"doctype"			: "Share Transfer",
			"transfer_type"		: "Transfer",
			"date"				: "2018-01-05",
			"from_shareholder"	: "SH-00003",
			"to_shareholder"	: "SH-00002",
			"share_type"		: "Equity",
			"from_no"			: 1,
			"to_no"				: 100,
			"no_of_shares"		: 100,
			"rate"				: 15,
			"company"			: "Stark Tower"
		})
		self.assertRaises(ValidationError, doc.insert)

	def test_invalid_share_purchase(self):
		doc = frappe.get_doc({
			"doctype"			: "Share Transfer",
			"transfer_type"		: "Purchase",
			"date"				: "2018-01-02",
			"from_shareholder"	: "SH-00001",
			"share_type"		: "Equity",
			"from_no"			: 1,
			"to_no"				: 200,
			"no_of_shares"		: 200,
			"rate"				: 15,
			"company"			: "Stark Tower"
		})
		self.assertRaises(ValidationError, doc.insert)
