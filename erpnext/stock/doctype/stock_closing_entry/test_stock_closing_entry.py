# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import add_days, flt, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
	StockClosing,
	prepare_closing_stock_balance,
)
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

	def test_carried_balances_only_update_their_stored_key(self):
		module = "erpnext.stock.doctype.stock_closing_entry.stock_closing_entry"
		item_details = frappe._dict(
			item_group="All Item Groups", item_name="Closing Test", stock_uom="Nos", has_serial_no=0
		)
		stored_keys = [
			("item_code", "warehouse"),
			("item_code", "warehouse", "batch_no"),
			("item_code", "warehouse", "location"),
			("item_code", "warehouse", "shelf"),
			("item_code", "warehouse", "location", "shelf"),
		]
		values = frappe._dict(
			item_code="Closing Test",
			warehouse=WAREHOUSE,
			batch_no="Batch A",
			location="Room A",
			shelf="Shelf A",
		)
		for opening_qty, opening_value, movement_qty, deleted_shelf in (
			(100, 1000, 0, False),
			(100, 1000, 10, False),
			(0, 50, 10, False),
			(100, 1000, 0, True),
			(100, 1000, 10, True),
		):
			with self.subTest(
				opening_qty=opening_qty, movement_qty=movement_qty, deleted_shelf=deleted_shelf
			):
				dimension_fields = ["location"] if deleted_shelf else ["location", "shelf"]
				dimensions = [frappe._dict(fieldname=field) for field in dimension_fields]
				expected_keys = stored_keys[:3] if deleted_shelf else stored_keys
				opening_rows = []
				for index, fields in enumerate(stored_keys):
					row = frappe._dict({field: values[field] for field in fields})
					row.update(
						name=f"Closing Balance {index}",
						stock_closing_entry="Previous Closing",
						inventory_dimension_key=json.dumps(fields) if index > 1 else None,
						actual_qty=opening_qty,
						stock_value_difference=opening_value,
						posting_date="2026-01-31",
					)
					opening_rows.append(row)

				movement = values.copy()
				movement.update(
					name="New SLE",
					actual_qty=movement_qty,
					stock_value_difference=movement_qty * 10,
					posting_date="2026-02-01",
				)

				def get_entries(doctype, fields, filters):
					rows = (
						opening_rows
						if doctype == "Stock Closing Balance"
						else ([movement] if movement_qty else [])
					)
					fields = [*fields, *dimension_fields]
					return [frappe._dict({field: row.get(field) for field in fields}) for row in rows]

				with (
					patch(f"{module}.get_inventory_dimensions", return_value=dimensions),
					patch.object(
						StockClosing,
						"get_last_stock_closing_entry",
						return_value=frappe._dict(name="Previous Closing", to_date="2026-01-31"),
					),
					patch.object(StockClosing, "get_entries", side_effect=get_entries),
					patch("frappe.get_cached_value", return_value=item_details),
				):
					entries = StockClosing(COMPANY, "2026-02-01", "2026-02-28").get_stock_closing_entries()

				self.assertEqual(
					set(entries), {tuple(values[field] for field in fields) for fields in expected_keys}
				)
				for fields in expected_keys:
					balance = entries[tuple(values[field] for field in fields)]
					self.assertEqual(balance.actual_qty, opening_qty + movement_qty)
					self.assertEqual(balance.stock_value_difference, opening_value + movement_qty * 10)
					self.assertEqual(
						balance.inventory_dimension_key,
						json.dumps(fields) if len(fields) > 2 and fields[-1] != "batch_no" else None,
					)

	def test_closing_entry_reads_previous_closing_balance(self):
		"""A closing entry created after another one must read the previous balance.

		Regression for the query that filtered `Stock Closing Balance` by a
		non-existent `closing_stock_balance` column, raising an OperationalError
		for every closing entry created after the first one.
		"""
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "_T-CBAL-CARRY-.####",
			}
		).name
		first_date = add_days(today(), -10)
		make_stock_entry(
			item_code=item,
			to_warehouse=WAREHOUSE,
			qty=100,
			rate=100,
			posting_date=first_date,
			company=COMPANY,
		)

		# Complete the previous closing before looking up its balance.
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			entry = self.make_stock_closing_entry(first_date, first_date)
		prepare_closing_stock_balance(entry.name)
		self.assertEqual(frappe.db.get_value("Stock Closing Entry", entry.name, "status"), "Completed")
		first_balances = frappe.get_all(
			"Stock Closing Balance",
			filters={"stock_closing_entry": entry.name, "item_code": item},
			fields=["batch_no", "actual_qty", "stock_value_difference", "inventory_dimension_key"],
		)
		self.assertEqual(len(first_balances), 2)
		batch_no = next(row.batch_no for row in first_balances if row.batch_no)
		self.assertEqual({row.batch_no or None for row in first_balances}, {None, batch_no})
		for row in first_balances:
			self.assertEqual(row.actual_qty, 100)
			self.assertEqual(row.stock_value_difference, 10000)
			self.assertFalse(row.inventory_dimension_key)

		second_from_date = add_days(first_date, 1)
		make_stock_entry(
			item_code=item,
			to_warehouse=WAREHOUSE,
			qty=10,
			batch_no=batch_no,
			rate=100,
			posting_date=second_from_date,
			company=COMPANY,
		)

		closing = StockClosing(COMPANY, second_from_date, add_days(second_from_date, 1))
		entries = closing.get_sle_entries()

		self.assertEqual(closing.last_closing_balance.name, self.last_closing_entry)
		self.assertIn(item, {row.item_code for row in entries})

		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			second_entry = self.make_stock_closing_entry(second_from_date, add_days(second_from_date, 1))
		prepare_closing_stock_balance(second_entry.name)
		self.assertEqual(frappe.db.get_value("Stock Closing Entry", second_entry.name, "status"), "Completed")
		second_balances = frappe.get_all(
			"Stock Closing Balance",
			filters={"stock_closing_entry": second_entry.name, "item_code": item},
			fields=["batch_no", "actual_qty", "stock_value_difference", "inventory_dimension_key"],
		)
		self.assertEqual(len(second_balances), 2)
		self.assertEqual({row.batch_no or None for row in second_balances}, {None, batch_no})
		for row in second_balances:
			self.assertEqual(row.actual_qty, 110)
			self.assertEqual(row.stock_value_difference, 11000)
			self.assertFalse(row.inventory_dimension_key)

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
