# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from erpnext.accounts.doctype.share_transfer.share_transfer import ShareDontExists

test_dependencies = ["Share Type", "Shareholder"]

class TestShareTransfer(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabShare Transfer`")
		frappe.db.sql("delete from `tabShare Balance`")
		share_transfers = [
			{
				"doctype": "Share Transfer",
				"transfer_type": "Issue",
				"date": "2018-01-01",
				"to_shareholder": "SH-00001",
				"share_type": "Equity",
				"from_no": 1,
				"to_no": 500,
				"no_of_shares": 500,
				"rate": 10,
				"company": "_Test Company",
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC"
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": "2018-01-02",
				"from_shareholder": "SH-00001",
				"to_shareholder": "SH-00002",
				"share_type": "Equity",
				"from_no": 101,
				"to_no": 200,
				"no_of_shares": 100,
				"rate": 15,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC"
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": "2018-01-03",
				"from_shareholder": "SH-00001",
				"to_shareholder": "SH-00003",
				"share_type": "Equity",
				"from_no": 201,
				"to_no": 500,
				"no_of_shares": 300,
				"rate": 20,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC"
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": "2018-01-04",
				"from_shareholder": "SH-00003",
				"to_shareholder": "SH-00002",
				"share_type": "Equity",
				"from_no": 201,
				"to_no": 400,
				"no_of_shares": 200,
				"rate": 15,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC"
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Purchase",
				"date": "2018-01-05",
				"from_shareholder": "SH-00003",
				"share_type": "Equity",
				"from_no": 401,
				"to_no": 500,
				"no_of_shares": 100,
				"rate": 25,
				"company": "_Test Company",
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC"
			}
		]
		for d in share_transfers:
			st = frappe.get_doc(d)
			st.submit()

	def test_invalid_share_transfer(self):
		doc = frappe.get_doc({
			"doctype": "Share Transfer",
			"transfer_type": "Transfer",
			"date": "2018-01-05",
			"from_shareholder": "SH-00003",
			"to_shareholder": "SH-00002",
			"share_type": "Equity",
			"from_no": 1,
			"to_no": 100,
			"no_of_shares": 100,
			"rate": 15,
			"company": "_Test Company",
			"equity_or_liability_account": "Creditors - _TC"
		})
		self.assertRaises(ShareDontExists, doc.insert)

		doc = frappe.get_doc({
			"doctype": "Share Transfer",
			"transfer_type": "Purchase",
			"date": "2018-01-02",
			"from_shareholder": "SH-00001",
			"share_type": "Equity",
			"from_no": 1,
			"to_no": 200,
			"no_of_shares": 200,
			"rate": 15,
			"company": "_Test Company",
			"asset_account": "Cash - _TC",
			"equity_or_liability_account": "Creditors - _TC"
		})
		self.assertRaises(ShareDontExists, doc.insert)
