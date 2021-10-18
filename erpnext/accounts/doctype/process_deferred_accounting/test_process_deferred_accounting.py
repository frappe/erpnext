# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	check_gl_entries,
	create_sales_invoice,
)
from erpnext.stock.doctype.item.test_item import create_item


class TestProcessDeferredAccounting(unittest.TestCase):
	def test_creation_of_ledger_entry_on_submit(self):
		''' test creation of gl entries on submission of document '''
		deferred_account = create_account(account_name="Deferred Revenue",
			parent_account="Current Liabilities - _TC", company="_Test Company")

		item = create_item("_Test Item for Deferred Accounting")
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = deferred_account
		item.no_of_months = 12
		item.save()

		si = create_sales_invoice(item=item.name, update_stock=0, posting_date="2019-01-10", do_not_submit=True)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2019-01-10"
		si.items[0].service_end_date = "2019-03-15"
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()

		process_deferred_accounting = doc = frappe.get_doc(dict(
			doctype='Process Deferred Accounting',
			posting_date="2019-01-01",
			start_date="2019-01-01",
			end_date="2019-01-31",
			type="Income"
		))

		process_deferred_accounting.insert()
		process_deferred_accounting.submit()

		expected_gle = [
			[deferred_account, 33.85, 0.0, "2019-01-31"],
			["Sales - _TC", 0.0, 33.85, "2019-01-31"]
		]

		check_gl_entries(self, si.name, expected_gle, "2019-01-10")
