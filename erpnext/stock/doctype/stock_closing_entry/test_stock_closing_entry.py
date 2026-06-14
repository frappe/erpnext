# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

<<<<<<< HEAD
from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import today

from erpnext.stock.doctype.item.test_item import make_item
=======
import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import StockClosing
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
>>>>>>> 8e627db (fix(stock): use correct field when reading previous stock closing balance)
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


class TestStockClosingEntry(ERPNextTestSuite):
	"""
	Integration tests for StockClosingEntry.
	Use this class for testing interactions between multiple components.
	"""

<<<<<<< HEAD
=======
	def test_closing_entry_reads_previous_closing_balance(self):
		"""A closing entry created after another one must read the previous balance.

		Regression for the query that filtered `Stock Closing Balance` by a
		non-existent `closing_stock_balance` column, raising an OperationalError
		for every closing entry created after the first one.
		"""
		item = make_item(properties={"is_stock_item": 1}).name
		first_date = add_days(today(), -10)

		# A submitted closing entry makes the next closing look up its balance.
		self.make_stock_closing_entry(first_date, first_date)

		second_from_date = add_days(first_date, 1)
		make_stock_entry(
			item_code=item,
			to_warehouse=WAREHOUSE,
			qty=10,
			rate=100,
			posting_date=second_from_date,
			company=COMPANY,
		)

		closing = StockClosing(COMPANY, second_from_date, add_days(second_from_date, 1))
		entries = closing.get_sle_entries()

		self.assertEqual(closing.last_closing_balance.name, self.last_closing_entry)
		self.assertIn(item, {row.item_code for row in entries})

>>>>>>> 8e627db (fix(stock): use correct field when reading previous stock closing balance)
	def make_stock_closing_entry(self, from_date, to_date):
		entry = frappe.get_doc(
			doctype="Stock Closing Entry",
			company=COMPANY,
			from_date=from_date,
			to_date=to_date,
		).submit()
		self.last_closing_entry = entry.name
		return entry
<<<<<<< HEAD

	def test_non_administrator_can_generate_closing_balance(self):
		item = make_item(properties={"is_stock_item": 1}).name
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			entry = self.make_stock_closing_entry(today(), today())

		user = create_user("test_stock_closing_balance@example.com", "Stock User")
		self.assertFalse(frappe.has_permission("Stock Closing Balance", "create", user=user.name))

		balance = frappe._dict(
			item_code=item,
			warehouse=WAREHOUSE,
			actual_qty=1,
			stock_value_difference=100,
			fifo_queue=None,
		)
		with (
			patch(
				"erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.StockClosing"
			) as stock_closing,
			self.set_user(user.name),
		):
			stock_closing.return_value.get_stock_closing_entries.return_value = {(item, WAREHOUSE): balance}
			entry.create_stock_closing_balance_entries()

		self.assertTrue(
			frappe.db.exists("Stock Closing Balance", {"stock_closing_entry": entry.name, "item_code": item})
		)
=======
>>>>>>> 8e627db (fix(stock): use correct field when reading previous stock closing balance)
