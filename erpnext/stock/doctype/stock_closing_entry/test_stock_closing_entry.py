# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import StockClosing
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


class TestStockClosingEntry(ERPNextTestSuite):
	"""
	Integration tests for StockClosingEntry.
	Use this class for testing interactions between multiple components.
	"""

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

	def make_stock_closing_entry(self, from_date, to_date):
		entry = frappe.get_doc(
			doctype="Stock Closing Entry",
			company=COMPANY,
			from_date=from_date,
			to_date=to_date,
		).submit()
		self.last_closing_entry = entry.name
		return entry


class TestStockClosingEntryDuplicate(ERPNextTestSuite):
	"""validate_duplicate blocks a second submitted closing entry whose date range
	overlaps an existing one for the same scope (company + warehouse/item filters)."""

	def make_closing(self, from_date, to_date, **fields):
		doc = frappe.new_doc("Stock Closing Entry")
		doc.company = COMPANY
		doc.from_date = from_date
		doc.to_date = to_date
		doc.update(fields)
		return doc

	def submit_closing(self, doc):
		# the closing-balance build is enqueued on submit; skip it here
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			doc.submit()
		return doc

	def test_overlapping_range_is_rejected(self):
		self.submit_closing(self.make_closing("2026-01-01", "2026-03-31"))
		overlap = self.make_closing("2026-02-01", "2026-04-30")
		self.assertRaises(frappe.ValidationError, overlap.insert)

	def test_fully_contained_range_is_rejected(self):
		# a range entirely inside an existing entry's range is still a duplicate
		self.submit_closing(self.make_closing("2026-01-01", "2026-12-31"))
		contained = self.make_closing("2026-03-01", "2026-03-31")
		self.assertRaises(frappe.ValidationError, contained.insert)

	def test_enclosing_range_is_rejected(self):
		# and so is a range that fully encloses an existing entry's range
		self.submit_closing(self.make_closing("2026-03-01", "2026-03-31"))
		enclosing = self.make_closing("2026-01-01", "2026-12-31")
		self.assertRaises(frappe.ValidationError, enclosing.insert)

	def test_non_overlapping_range_is_allowed(self):
		self.submit_closing(self.make_closing("2026-01-01", "2026-03-31"))
		later = self.make_closing("2026-04-01", "2026-06-30")
		later.insert()  # would raise if validate_duplicate wrongly flagged it as overlapping
		self.assertTrue(frappe.db.exists("Stock Closing Entry", later.name))
