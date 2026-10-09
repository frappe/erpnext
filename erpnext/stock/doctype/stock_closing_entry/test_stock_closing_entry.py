# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import add_days, flt, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
	StockClosing,
	StockClosingEntry,
	prepare_closing_stock_balance,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
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

	def test_batch_zero_values_in_closing_balance(self):
		module = "erpnext.stock.doctype.stock_closing_entry.stock_closing_entry"
		item_details = frappe._dict(
			item_group="All Item Groups", item_name="Closing Test", stock_uom="Nos", has_serial_no=0
		)
		for batch_qty, batch_value, ledger_qty, balance_qty, expected_qty, expected_value in (
			(10, 0, 20, 20, 20, 0),
			(0, 0, 20, 20, 0, 0),
			(0, 0, 0, 20, 0, 0),
			(10, 50, 20, 20, 20, 100),
			(None, None, 20, 20, 40, 200),
			(None, None, 0, None, 0, 200),
		):
			with self.subTest(batch_qty=batch_qty, batch_value=batch_value, ledger_qty=ledger_qty):
				rows = [
					frappe._dict(
						name=f"Closing SLE {index}",
						item_code="Closing Test",
						warehouse=WAREHOUSE,
						batch_no="Closing Batch",
						sabb_qty=batch_qty,
						sabb_stock_value_difference=batch_value,
						actual_qty=ledger_qty,
						qty_after_transaction=balance_qty,
						stock_value_difference=100,
						posting_date="2026-01-01",
					)
					for index in range(2)
				]
				with (
					patch(f"{module}.get_inventory_dimensions", return_value=[]),
					patch.object(StockClosing, "get_last_stock_closing_entry", return_value=None),
					patch.object(StockClosing, "get_sle_entries", return_value=rows),
					patch("frappe.get_cached_value", return_value=item_details),
				):
					entries = StockClosing(COMPANY, "2026-01-01", "2026-01-03").get_stock_closing_entries()

				balance = entries[("Closing Test", WAREHOUSE, "Closing Batch")]
				self.assertEqual(balance.actual_qty, expected_qty)
				self.assertEqual(balance.stock_value_difference, expected_value)
				self.assertEqual(entries[("Closing Test", WAREHOUSE)].stock_value_difference, 200)

	def test_zero_value_batch_in_joined_closing_entries(self):
		module = "erpnext.stock.doctype.stock_closing_entry.stock_closing_entry"
		item_details = frappe._dict(
			item_group="All Item Groups", item_name="Closing Test", stock_uom="Nos", has_serial_no=0
		)
		rows = [
			frappe._dict(
				name="Closing SLE",
				item_code="Closing Test",
				warehouse=WAREHOUSE,
				batch_no=None,
				sabb_batch_no=batch,
				sabb_qty=-10,
				sabb_stock_value_difference=value,
				actual_qty=-20,
				qty_after_transaction=0,
				stock_value_difference=-100,
				posting_date="2026-01-01",
			)
			for batch, value in (("Batch A", 0), ("Batch B", -100))
		]
		with (
			patch(f"{module}.get_inventory_dimensions", return_value=[]),
			patch.object(StockClosing, "get_last_stock_closing_entry", return_value=None),
			patch.object(StockClosing, "get_sle_entries", return_value=rows),
			patch("frappe.get_cached_value", return_value=item_details),
		):
			entries = StockClosing(COMPANY, "2026-01-01", "2026-01-03").get_stock_closing_entries()

		self.assertEqual(len(entries), 3)
		for batch, expected_value in (("Batch A", 0), ("Batch B", -100)):
			balance = entries[("Closing Test", WAREHOUSE, batch)]
			self.assertEqual(balance.actual_qty, -10)
			self.assertEqual(balance.stock_value_difference, expected_value)

		total = entries[("Closing Test", WAREHOUSE)]
		self.assertEqual(total.actual_qty, -20)
		self.assertEqual(total.stock_value_difference, -100)

	def test_closing_entry_reads_previous_closing_balance(self):
		"""A closing entry created after another one must read the previous balance.

		Regression for the query that filtered `Stock Closing Balance` by a
		non-existent `closing_stock_balance` column, raising an OperationalError
		for every closing entry created after the first one.
		"""
		item = make_item(properties={"is_stock_item": 1}).name
		first_date = add_days(today(), -10)

		# Complete the previous closing before looking up its balance.
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			entry = self.make_stock_closing_entry(first_date, first_date)
		prepare_closing_stock_balance(entry.name)
		self.assertEqual(frappe.db.get_value("Stock Closing Entry", entry.name, "status"), "Completed")

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

	def test_chained_closing_does_not_double_count_batch_rows(self):
		"""The previous closing's batch rows must only carry forward onto their own batch key.
		Spreading them onto the item + warehouse key too added them on top of the item + warehouse
		row that already includes them, doubling the opening of every batched item."""
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "_T-CBAL-CHAIN-.####",
			}
		).name
		first_date = add_days(today(), -10)

		make_stock_entry(
			item_code=item,
			to_warehouse=WAREHOUSE,
			qty=10,
			rate=100,
			posting_date=first_date,
			company=COMPANY,
		)

		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			first_closing = self.make_stock_closing_entry(first_date, first_date)

		prepare_closing_stock_balance(first_closing.name)
		self.assertEqual(
			frappe.db.get_value("Stock Closing Entry", first_closing.name, "status"), "Completed"
		)

		second_from_date = add_days(first_date, 1)
		entries = StockClosing(
			COMPANY, second_from_date, add_days(second_from_date, 1)
		).get_stock_closing_entries()

		self.assertEqual(flt(entries[(item, WAREHOUSE)].actual_qty), 10)
		self.assertEqual(flt(entries[(item, WAREHOUSE)].stock_value_difference), 1000)


class TestStockClosingEntryDates(ERPNextTestSuite):
	"""From Date is not entered by the user: it follows on from the previous closing, so closings
	always form an unbroken chain."""

	def make_closing(self, to_date):
		doc = frappe.new_doc("Stock Closing Entry")
		doc.company = COMPANY
		doc.to_date = to_date
		return doc

	def submit_closing(self, doc):
		# the closing-balance build is enqueued on submit; skip it here
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			doc.submit()
		return doc

	def test_from_date_follows_previous_closing(self):
		self.submit_closing(self.make_closing("2026-03-31"))

		later = self.make_closing("2026-06-30")
		later.from_date = "2026-01-01"  # a user supplied value is ignored
		later.insert()

		self.assertEqual(str(later.from_date), "2026-04-01")

	def test_first_closing_starts_from_first_stock_ledger_entry(self):
		first_posting_date = frappe.db.get_value(
			"Stock Ledger Entry",
			{"company": COMPANY, "is_cancelled": 0, "docstatus": 1},
			[{"MIN": "posting_date"}],
		)

		doc = self.make_closing(today())
		doc.insert()

		self.assertEqual(str(doc.from_date), str(first_posting_date or today()))

	def test_to_date_before_previous_closing_is_rejected(self):
		self.submit_closing(self.make_closing("2026-06-30"))

		earlier = self.make_closing("2026-03-31")
		self.assertRaises(frappe.ValidationError, earlier.insert)

		same = self.make_closing("2026-06-30")
		self.assertRaises(frappe.ValidationError, same.insert)

	def test_cannot_cancel_closing_with_later_closing(self):
		first = self.submit_closing(self.make_closing("2026-03-31"))
		later = self.submit_closing(self.make_closing("2026-06-30"))

		self.assertRaises(frappe.ValidationError, first.cancel)

		later.cancel()
		first.reload()
		first.cancel()
		self.assertEqual(first.docstatus, 2)

	def make_generated_closing(self, to_date):
		closing = self.submit_closing(self.make_closing(to_date))
		prepare_closing_stock_balance(closing.name)
		return closing

	def test_stock_balance_filters_apply_to_closing_opening(self):
		from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance

		item_group = frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "_Test Closing Group",
				"parent_item_group": "All Item Groups",
			}
		).insert(ignore_if_duplicate=True)
		item = make_item(properties={"is_stock_item": 1, "item_group": item_group.name}).name
		warehouse = create_warehouse("_Test Closing Child WH")
		group_warehouse = frappe.db.get_value("Warehouse", warehouse, "parent_warehouse")

		make_stock_entry(
			item_code=item, target=warehouse, qty=10, rate=100, posting_date=add_days(today(), -30)
		)
		self.make_generated_closing(add_days(today(), -10))
		make_stock_entry(
			item_code=item, target=warehouse, qty=2, rate=100, posting_date=add_days(today(), -2)
		)

		filters = frappe._dict(company=COMPANY, from_date=add_days(today(), -5), to_date=today())

		rows = stock_balance(filters.copy().update(warehouse=[group_warehouse], item_code=[item]))[1]
		self.assertEqual((rows[0]["opening_qty"], rows[0]["bal_qty"]), (10, 12))

		rows = stock_balance(filters.copy().update(item_group=item_group.name))[1]
		self.assertEqual({row["item_code"] for row in rows}, {item})

	def test_cannot_regenerate_closing_with_later_closing(self):
		first = self.submit_closing(self.make_closing("2026-03-31"))
		self.submit_closing(self.make_closing("2026-06-30"))

		self.assertRaises(frappe.ValidationError, first.regenerate_closing_balance)

	def test_closing_balance_is_generated_only_for_submitted_entry(self):
		draft = self.make_closing("2026-03-31")
		draft.insert()
		self.assertRaises(frappe.ValidationError, draft.enqueue_job)
		self.assertRaises(frappe.ValidationError, draft.regenerate_closing_balance)

		closing = self.submit_closing(draft)
		closing.cancel()
		self.assertRaises(frappe.ValidationError, closing.regenerate_closing_balance)
		self.assertEqual(frappe.db.get_value("Stock Closing Entry", closing.name, "status"), "Cancelled")

	def test_queued_job_skips_cancelled_closing(self):
		item = make_item("_Test SCE Cancelled Job Item", {"is_stock_item": 1}).name
		make_stock_entry(item_code=item, qty=10, rate=100, to_warehouse=WAREHOUSE, posting_date="2026-03-15")

		closing = self.submit_closing(self.make_closing("2026-03-31"))
		closing.cancel()
		prepare_closing_stock_balance(closing.name)

		self.assertEqual(frappe.db.get_value("Stock Closing Entry", closing.name, "status"), "Cancelled")
		self.assertFalse(frappe.db.exists("Stock Closing Balance", {"stock_closing_entry": closing.name}))

	def test_closing_cancelled_while_job_runs_is_not_completed(self):
		item = make_item("_Test SCE Cancelled Job Item", {"is_stock_item": 1}).name
		make_stock_entry(item_code=item, qty=10, rate=100, to_warehouse=WAREHOUSE, posting_date="2026-03-15")

		closing = self.submit_closing(self.make_closing("2026-03-31"))
		build_balance = StockClosingEntry.create_stock_closing_balance_entries

		def build_then_cancel(doc):
			build_balance(doc)
			self.assertTrue(frappe.db.exists("Stock Closing Balance", {"stock_closing_entry": doc.name}))
			frappe.db.set_value("Stock Closing Entry", doc.name, "docstatus", 2)

		with patch.object(StockClosingEntry, "create_stock_closing_balance_entries", build_then_cancel):
			prepare_closing_stock_balance(closing.name)

		self.assertEqual(frappe.db.get_value("Stock Closing Entry", closing.name, "status"), "Cancelled")
		self.assertFalse(frappe.db.exists("Stock Closing Balance", {"stock_closing_entry": closing.name}))

	def test_reposting_ignores_completed_draft_closing(self):
		draft = self.make_closing(today())
		draft.insert()
		draft.db_set("status", "Completed")

		repost = frappe.get_doc(
			{"doctype": "Repost Item Valuation", "company": COMPANY, "posting_date": add_days(today(), -1)}
		)
		self.assertFalse(repost.get_closing_stock_balance())

	def test_future_to_date_is_rejected(self):
		self.assertRaises(frappe.ValidationError, self.make_closing(add_days(today(), 30)).insert)

	def test_stock_balance_ageing_does_not_count_closed_stock_twice(self):
		from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance

		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		for qty, days in ((10, -60), (10, -50), (10, -40)):
			make_stock_entry(
				item_code=item, target=WAREHOUSE, qty=qty, rate=100, posting_date=add_days(today(), days)
			)
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=12, posting_date=add_days(today(), -20))
		self.make_generated_closing(add_days(today(), -10))

		filters = frappe._dict(
			company=COMPANY,
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			show_stock_ageing_data=1,
		)
		row = stock_balance(filters)[1][0]

		self.assertEqual(sum(slot[0] for slot in row["fifo_queue"]), 18)
		self.assertEqual(row["average_age"], 44.44)

	def test_company_is_mandatory(self):
		closing = self.make_closing(add_days(today(), -1))
		closing.company = None
		self.assertRaises(frappe.MandatoryError, closing.insert)
