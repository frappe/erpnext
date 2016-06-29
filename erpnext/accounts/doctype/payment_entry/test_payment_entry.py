# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.accounts.doctype.payment_entry.payment_entry import make_payment_entry

class TestPaymentEntry(unittest.TestCase):
	def test_payment_entry_against_order(self):
		so = make_sales_order()
		pe = make_payment_entry("Sales Order", so.name)
		pe.paid_to = "_Test Bank - _TC"
		pe.insert()
		pe.submit()
		
		expected_gle = {
			"_Test Bank - _TC": {
				"account_currency": "INR",
				"debit": 1000,
				"debit_in_account_currency": 1000,
				"credit": 0,
				"credit_in_account_currency": 0,
				"against_voucher": None
			},
			"_Test Receivable - _TC": {
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 1000,
				"credit_in_account_currency": 1000,
				"against_voucher": so.name
			}
		}
		
		self.validate_gl_entries(pe.name, expected_gle)
		
		so.load_from_db()
		
	def validate_gl_entries(self, voucher_no, expected_gle):
		gl_entries = frappe.db.sql("""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency, against_voucher
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""", voucher_no, as_dict=1)

		self.assertTrue(gl_entries)
		
		for field in ("account_currency", "debit", "debit_in_account_currency", 
			"credit", "credit_in_account_currency"):
				for i, gle in enumerate(gl_entries):
					self.assertEquals(expected_gle[gle.account][field], gle[field])
		
