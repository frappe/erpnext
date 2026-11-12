# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.stock.doctype.closing_stock_balance.closing_stock_balance import (
	prepare_closing_stock_balance,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.utils import PendingRepostingError

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


class TestClosingStockBalance(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("closing_stock_balance_test")

	def tearDown(self):
		frappe.db.rollback(save_point="closing_stock_balance_test")

	def make_closing(self):
		doc = frappe.new_doc("Closing Stock Balance")
		doc.company = COMPANY
		doc.from_date = add_days(today(), -30)
		doc.to_date = add_days(today(), -1)
		return doc

	def submit_closing(self, doc):
		with patch("erpnext.stock.doctype.closing_stock_balance.closing_stock_balance.enqueue"):
			doc.submit()
		return doc

	def make_queued_repost(self):
		repost = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": make_item(properties={"is_stock_item": 1}).name,
				"warehouse": WAREHOUSE,
				"company": COMPANY,
				"posting_date": add_days(today(), -20),
				"posting_time": "00:00:00",
			}
		)
		repost.flags.dont_run_in_test = True
		repost.submit()
		return repost

	def test_closing_balance_waits_for_pending_reposts(self):
		self.make_queued_repost()

		self.assertRaises(PendingRepostingError, self.submit_closing, self.make_closing())

	def test_queued_closing_waits_for_reposts_added_after_queueing(self):
		closing = self.submit_closing(self.make_closing())
		self.make_queued_repost()

		prepare_closing_stock_balance(closing.name)

		self.assertEqual(frappe.db.get_value("Closing Stock Balance", closing.name, "status"), "Failed")
		self.assertFalse(closing.get_prepared_data())
