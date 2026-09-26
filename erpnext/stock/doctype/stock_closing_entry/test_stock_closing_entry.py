# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import add_days, flt, today

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

	def test_reconciliation_quantity_in_closing_balance(self):
		module = "erpnext.stock.doctype.stock_closing_entry.stock_closing_entry"
		item_details = frappe._dict(
			item_group="All Item Groups", item_name="Closing Test", stock_uom="Nos", has_serial_no=0
		)
		for reconciled_qty, expected_qty in ((0, 50), (20, 70), (None, 150)):
			with self.subTest(reconciled_qty=reconciled_qty):
				rows = [
					frappe._dict(
						item_code="Closing Test",
						warehouse=WAREHOUSE,
						actual_qty=qty,
						qty_after_transaction=balance,
						stock_value_difference=value,
						posting_date="2026-01-01",
					)
					for qty, balance, value in (
						(100, 100, 1000),
						(0, reconciled_qty, (reconciled_qty - 100) * 10 if reconciled_qty is not None else 0),
						(50, expected_qty, 500),
					)
				]
				# Carried-forward balances have no qty_after_transaction and must not reset quantity.
				if reconciled_qty is None:
					del rows[1]["qty_after_transaction"]

				with (
					patch(f"{module}.get_inventory_dimensions", return_value=[]),
					patch.object(StockClosing, "get_last_stock_closing_entry", return_value=None),
					patch.object(StockClosing, "get_sle_entries", return_value=rows),
					patch("frappe.get_cached_value", return_value=item_details),
				):
					entries = StockClosing(COMPANY, "2026-01-01", "2026-01-03").get_stock_closing_entries()

				balance = entries[("Closing Test", WAREHOUSE)]
				self.assertEqual(balance.actual_qty, expected_qty)
				self.assertEqual(balance.stock_value_difference, expected_qty * 10)

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

	def test_adjustment_entry_write_off_uses_ledger_basis_for_batched_item(self):
		"""An is_adjustment_entry writes off stock value stranded on the Stock Ledger Entry, so the
		item + warehouse closing total has to be built from sle.stock_value_difference. Building it
		from the per-batch values instead subtracts the write-off from a batch total that already
		nets out, and the phantom balance is then carried forward as the Stock Balance opening."""
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "_T-CBAL-ADJ-.####",
			}
		).name
		receipt_date = add_days(today(), -10)
		issue_date = add_days(today(), -9)

		receipt = make_stock_entry(
			item_code=item,
			to_warehouse=WAREHOUSE,
			qty=10,
			rate=100,
			posting_date=receipt_date,
			company=COMPANY,
		)
		batch_no = frappe.db.get_value(
			"Serial and Batch Entry",
			{
				"parent": frappe.db.get_value(
					"Stock Ledger Entry", {"voucher_no": receipt.name}, "serial_and_batch_bundle"
				)
			},
			"batch_no",
		)
		issue = make_stock_entry(
			item_code=item,
			from_warehouse=WAREHOUSE,
			qty=10,
			batch_no=batch_no,
			posting_date=issue_date,
			company=COMPANY,
		)

		# Strand 100 of value: the batch ledger nets out but the Stock Ledger Entries no longer do.
		outgoing_sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": issue.name}, "name")
		frappe.db.set_value(
			"Stock Ledger Entry",
			outgoing_sle,
			"stock_value_difference",
			flt(frappe.db.get_value("Stock Ledger Entry", outgoing_sle, "stock_value_difference")) + 100,
			update_modified=False,
		)

		# The write-off a Stock Reconciliation emits for it: no quantity, no bundle, value only.
		adjustment_entry = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item_code": item,
				"warehouse": WAREHOUSE,
				"company": COMPANY,
				"posting_date": add_days(today(), -8),
				"posting_time": "10:00:00",
				"voucher_type": "Stock Reconciliation",
				"voucher_no": "_T-CBAL-ADJ-RECO",
				"actual_qty": 0,
				"qty_after_transaction": 0,
				"stock_value": 0,
				"stock_value_difference": -100,
				"is_adjustment_entry": 1,
			}
		)
		adjustment_entry.flags.ignore_links = True
		adjustment_entry.submit()

		entries = StockClosing(COMPANY, receipt_date, today()).get_stock_closing_entries()

		self.assertEqual(flt(entries[(item, WAREHOUSE)].stock_value_difference), 0.0)
		self.assertEqual(flt(entries[(item, WAREHOUSE, batch_no)].stock_value_difference), 0.0)

	def make_stock_closing_entry(self, from_date, to_date):
		entry = frappe.get_doc(
			doctype="Stock Closing Entry",
			company=COMPANY,
			from_date=from_date,
			to_date=to_date,
		).submit()
		self.last_closing_entry = entry.name
		return entry

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
