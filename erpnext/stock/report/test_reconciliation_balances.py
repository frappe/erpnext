# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, flt, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
	make_plant_dimension,
)
from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance
from erpnext.stock.report.stock_ledger.stock_ledger import execute as stock_ledger
from erpnext.tests.utils import ERPNextTestSuite

STORES = "Stores - _TC"
FINISHED_GOODS = "Finished Goods - _TC"
ALL_WAREHOUSES = "All Warehouses - _TC"


class TestReconciliationBalances(ERPNextTestSuite):
	"""Stock Balance and Stock Ledger must show the balance the ledger holds after a Stock Reconciliation."""

	def make_stock_item(self, **properties):
		return make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO", **properties}).name

	def make_batch_item(self, **properties):
		return self.make_stock_item(
			has_batch_no=1, create_new_batch=1, batch_number_series="RBB-.#####", **properties
		)

	def make_serial_item(self, **properties):
		return self.make_stock_item(has_serial_no=1, serial_no_series="RBS-.#####", **properties)

	def receive(self, item_code, qty, rate=100, warehouse=STORES, days_ago=5, **extra):
		return make_stock_entry(
			item_code=item_code,
			to_warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=add_days(today(), -days_ago),
			**extra,
		)

	def reconcile(self, item_code, qty, rate=100, warehouse=STORES, days_ago=2, **extra):
		return create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=add_days(today(), -days_ago),
			posting_time="12:00:00",
			**extra,
		)

	def get_filters(self, item_code, warehouse=STORES, **extra):
		return frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(today(), -30),
				"to_date": today(),
				"item_code": [item_code] if isinstance(item_code, str) else item_code,
				"warehouse": [warehouse] if isinstance(warehouse, str) else warehouse,
				**extra,
			}
		)

	def get_balance_rows(self, item_code, warehouse=STORES, **extra):
		return [
			frappe._dict(row) for row in stock_balance(self.get_filters(item_code, warehouse, **extra))[1]
		]

	def get_ledger_rows(self, item_code, warehouse=STORES, **extra):
		rows = stock_ledger(self.get_filters(item_code, warehouse, **extra))[1]
		return [frappe._dict(row) for row in rows if row.get("voucher_no")]

	def get_ledger_balance(self, item_code, warehouse=STORES):
		return frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_code, "warehouse": warehouse, "is_cancelled": 0},
			fields=["qty_after_transaction", "stock_value"],
			order_by="posting_datetime desc, creation desc",
			limit=1,
		)[0]

	def assertStockBalance(self, item_code, qty, value, warehouse=STORES, **filters):
		rows = [
			row
			for row in self.get_balance_rows(item_code, warehouse, **filters)
			if row.warehouse == warehouse
		]
		self.assertEqual(len(rows), 1, rows)
		row = rows[0]
		self.assertEqual((flt(row.bal_qty, 3), flt(row.bal_val, 2)), (qty, value))
		self.assertAlmostEqual(row.bal_qty, row.opening_qty + row.in_qty - row.out_qty, 3)
		self.assertAlmostEqual(row.bal_val, row.opening_val + row.in_val - row.out_val, 2)

	def assertStockLedger(self, item_code, qty, value, warehouse=STORES, **filters):
		rows = stock_ledger(self.get_filters(item_code, warehouse, **filters))[1]
		last = [row for row in rows if not row.get("voucher_no") or row.get("warehouse") == warehouse][-1]
		self.assertEqual((flt(last["qty_after_transaction"], 3), flt(last["stock_value"], 2)), (qty, value))

	def assertReportsMatchLedger(self, item_code, qty, value, warehouse=STORES, **filters):
		ledger = self.get_ledger_balance(item_code, warehouse)
		self.assertEqual((flt(ledger.qty_after_transaction, 3), flt(ledger.stock_value, 2)), (qty, value))

		self.assertStockBalance(item_code, qty, value, warehouse=warehouse, **filters)
		self.assertStockLedger(item_code, qty, value, warehouse=warehouse, **filters)

	def test_reconciliation_raises_the_balance_of_an_item(self):
		item = self.make_stock_item()
		self.receive(item, 5)
		self.reconcile(item, 8)

		self.assertReportsMatchLedger(item, 8, 800)
		(row,) = self.get_balance_rows(item)
		self.assertEqual((row.in_qty, row.out_qty), (8, 0))
		self.assertEqual(self.get_ledger_rows(item)[-1].in_qty, 3)

	def test_reconciliation_lowers_the_balance_of_an_item(self):
		item = self.make_stock_item()
		self.receive(item, 10)
		self.reconcile(item, 4, rate=120)
		self.receive(item, 2, days_ago=1)

		self.assertReportsMatchLedger(item, 6, 680)
		(row,) = self.get_balance_rows(item)
		self.assertEqual((row.in_qty, row.out_qty), (12, 6))
		reconciliation = self.get_ledger_rows(item)[1]
		self.assertEqual((reconciliation.out_qty, reconciliation.qty_after_transaction), (-6, 4))

	def test_reconciliation_before_the_from_date_is_in_the_opening(self):
		item = self.make_stock_item()
		self.receive(item, 10, days_ago=10)
		self.reconcile(item, 7, days_ago=6)
		self.receive(item, 3, days_ago=1)

		from_date = add_days(today(), -3)
		self.assertReportsMatchLedger(item, 10, 1000, from_date=from_date)
		(row,) = self.get_balance_rows(item, from_date=from_date)
		self.assertEqual((row.opening_qty, row.in_qty), (7, 3))
		self.assertEqual(
			stock_ledger(self.get_filters(item, from_date=from_date))[1][0]["qty_after_transaction"], 7
		)

	def test_reconciliation_on_the_from_date(self):
		item = self.make_stock_item()
		self.receive(item, 10, days_ago=10)
		self.reconcile(item, 4, days_ago=3)

		self.assertReportsMatchLedger(item, 4, 400, from_date=add_days(today(), -3))
		(row,) = self.get_balance_rows(item, from_date=add_days(today(), -3))
		self.assertEqual((row.opening_qty, row.out_qty), (10, 6))

	def test_opening_stock_reconciliation_in_the_period_is_the_opening(self):
		item = self.make_stock_item()
		batch_item = self.make_batch_item()
		for item_code in (item, batch_item):
			self.reconcile(item_code, 5, days_ago=10, purpose="Opening Stock")
			self.receive(item_code, 2, days_ago=1)

			self.assertReportsMatchLedger(item_code, 7, 700)
			(row,) = self.get_balance_rows(item_code)
			self.assertEqual((row.opening_qty, row.opening_val, row.in_qty), (5, 500, 2))

	def test_reconciliations_of_items_and_warehouses_are_kept_apart(self):
		items = [self.make_stock_item() for _item in range(2)]
		for item, qty in zip(items, (5, 7), strict=True):
			for warehouse in (STORES, FINISHED_GOODS):
				self.receive(item, 10, warehouse=warehouse)
				self.reconcile(item, qty, warehouse=warehouse)
		self.receive(items[0], 1, warehouse=FINISHED_GOODS, days_ago=1)

		expected = {
			(items[0], STORES): 5,
			(items[0], FINISHED_GOODS): 6,
			(items[1], STORES): 7,
			(items[1], FINISHED_GOODS): 7,
		}
		for (item, warehouse), qty in expected.items():
			self.assertReportsMatchLedger(item, qty, qty * 100, warehouse=warehouse)

		rows = self.get_balance_rows(items, ALL_WAREHOUSES)
		self.assertEqual({(row.item_code, row.warehouse): row.bal_qty for row in rows}, expected)

		ledger_rows = self.get_ledger_rows(items, ALL_WAREHOUSES)
		balances = {(row.item_code, row.warehouse): row.qty_after_transaction for row in ledger_rows}
		self.assertEqual(balances, expected)

	def test_reconciliation_of_a_batch(self):
		item = self.make_batch_item()
		first_batch = get_batch_from_bundle(self.receive(item, 10).items[0].serial_and_batch_bundle)
		second_batch = get_batch_from_bundle(
			self.receive(item, 5, rate=200, days_ago=4).items[0].serial_and_batch_bundle
		)
		self.reconcile(item, 6, batch_no=first_batch, reconcile_all_serial_batch=0)

		self.assertReportsMatchLedger(item, 11, 1600)
		ledger_rows = self.get_ledger_rows(item, batch_no=first_batch)
		self.assertEqual(ledger_rows[-1].qty_after_transaction, 6)
		self.assertEqual(self.get_ledger_rows(item, batch_no=second_batch)[-1].qty_after_transaction, 5)

	def test_reconciliation_of_all_batches_in_batch_filtered_ledger(self):
		item = self.make_batch_item()
		first_batch = get_batch_from_bundle(self.receive(item, 10).items[0].serial_and_batch_bundle)
		second_batch = get_batch_from_bundle(
			self.receive(item, 5, rate=200, days_ago=4).items[0].serial_and_batch_bundle
		)
		self.reconcile(item, 6, batch_no=first_batch)

		self.assertReportsMatchLedger(item, 6, 600)
		for segregate in (0, 1):
			for batch, qty, value in ((first_batch, 6, 600), (second_batch, 0, 0)):
				rows = self.get_ledger_rows(item, batch_no=batch, segregate_serial_batch_bundle=segregate)
				self.assertEqual(
					(rows[-1].qty_after_transaction, rows[-1].stock_value),
					(qty, value),
					f"{batch=} {segregate=}",
				)

	def test_batch_filtered_ledger_after_entries_without_a_bundle(self):
		item = self.make_batch_item()
		receipts = [self.receive(item, qty, days_ago=days_ago) for qty, days_ago in ((10, 5), (5, 4))]
		batch = get_batch_from_bundle(receipts[0].items[0].serial_and_batch_bundle)
		for receipt in receipts:
			frappe.db.set_value(
				"Stock Ledger Entry",
				{"voucher_no": receipt.name},
				{"batch_no": batch, "serial_and_batch_bundle": None},
			)
		make_stock_entry(
			item_code=item,
			from_warehouse=STORES,
			qty=3,
			batch_no=batch,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
		)

		for segregate in (0, 1):
			rows = self.get_ledger_rows(item, batch_no=batch, segregate_serial_batch_bundle=segregate)
			self.assertEqual(
				[(row.qty_after_transaction, row.stock_value) for row in rows],
				[(10, 1000), (15, 1500), (12, 1200)],
				f"{segregate=}",
			)

	def test_reconciliation_of_a_batch_in_segregated_ledger(self):
		item = self.make_batch_item()
		batch = get_batch_from_bundle(self.receive(item, 10).items[0].serial_and_batch_bundle)
		self.reconcile(item, 6, batch_no=batch, reconcile_all_serial_batch=0)

		rows = self.get_ledger_rows(item, segregate_serial_batch_bundle=1)
		self.assertEqual(rows[-1].qty_after_transaction, 6)
		rows = self.get_ledger_rows(item, batch_no=batch, segregate_serial_batch_bundle=1)
		self.assertEqual(rows[-1].qty_after_transaction, 6)

	def test_reconciliation_of_serial_nos(self):
		item = self.make_serial_item()
		receipt = self.receive(item, 5)
		serial_nos = get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)
		self.reconcile(item, 3, serial_no=serial_nos[:3])

		self.assertReportsMatchLedger(item, 3, 300)

	def test_reconciliation_replaces_serial_nos(self):
		item = self.make_serial_item()
		self.receive(item, 2)
		new_serial_nos = [
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": frappe.generate_hash(length=12),
					"item_code": item,
					"company": "_Test Company",
				}
			)
			.insert()
			.name
			for _serial_no in range(4)
		]
		self.reconcile(
			item,
			4,
			rate=150,
			serial_no="\n".join(new_serial_nos),
			use_serial_batch_fields=1,
		)

		self.assertReportsMatchLedger(item, 4, 600)

	def test_reconciliation_of_serial_nos_in_a_batch(self):
		item = self.make_serial_item(has_batch_no=1, create_new_batch=1, batch_number_series="RBSB-.#####")
		receipt = self.receive(item, 4)
		bundle = receipt.items[0].serial_and_batch_bundle
		self.reconcile(
			item, 2, batch_no=get_batch_from_bundle(bundle), serial_no=get_serial_nos_from_bundle(bundle)[:2]
		)

		self.assertReportsMatchLedger(item, 2, 200)

	def receive_into_plant(self, item_code, qty, plant, days_ago=5):
		receipt = self.receive(item_code, qty, days_ago=days_ago, do_not_save=True)
		receipt.items[0].to_id_plant = plant
		receipt.insert()
		receipt.submit()
		receipt.load_from_db()
		return receipt

	def reconcile_plant(self, item_code, qty, plant, days_ago=2, **extra):
		reconciliation = self.reconcile(item_code, qty, days_ago=days_ago, do_not_save=True, **extra)
		reconciliation.items[0].id_plant = plant
		reconciliation.insert()
		reconciliation.submit()
		return reconciliation

	def test_reconciliation_of_an_inventory_dimension(self):
		plant_a, plant_b = make_plant_dimension()
		item = self.make_stock_item()
		self.receive_into_plant(item, 10, plant_b)
		self.reconcile_plant(item, 4, plant_a)
		self.receive_into_plant(item, 2, plant_a, days_ago=1)

		self.assertReportsMatchLedger(item, 16, 1600)
		self.assertStockBalance(item, 6, 600, id_plant=[plant_a])
		self.assertStockBalance(item, 10, 1000, id_plant=[plant_b])
		self.assertStockLedger(item, 6, 600, id_plant=[plant_a])
		self.assertStockLedger(item, 10, 1000, id_plant=[plant_b])

		rows = self.get_balance_rows(item, show_dimension_wise_stock=1)
		self.assertEqual(
			{row.id_plant: (row.bal_qty, row.bal_val) for row in rows},
			{plant_a: (6, 600), plant_b: (10, 1000)},
		)

	def test_opening_reconciliation_of_inventory_dimensions(self):
		plant_a, plant_b = make_plant_dimension()
		item = self.make_stock_item()
		self.reconcile_plant(item, 5, plant_a, days_ago=10, purpose="Opening Stock")
		self.reconcile_plant(item, 3, plant_b, days_ago=10, purpose="Opening Stock")
		self.receive_into_plant(item, 2, plant_a, days_ago=1)

		self.assertReportsMatchLedger(item, 10, 1000)
		self.assertStockBalance(item, 7, 700, id_plant=[plant_a])
		self.assertStockBalance(item, 3, 300, id_plant=[plant_b])
		self.assertStockLedger(item, 7, 700, id_plant=[plant_a])
		self.assertStockLedger(item, 3, 300, id_plant=[plant_b])

	def test_reconciliation_of_an_inventory_dimension_before_the_from_date(self):
		plant_a, plant_b = make_plant_dimension()
		item = self.make_stock_item()
		self.receive_into_plant(item, 10, plant_b, days_ago=10)
		self.reconcile_plant(item, 4, plant_a, days_ago=6)
		self.receive_into_plant(item, 2, plant_a, days_ago=1)

		from_date = add_days(today(), -3)
		self.assertReportsMatchLedger(item, 16, 1600, from_date=from_date)
		self.assertStockBalance(item, 6, 600, id_plant=[plant_a], from_date=from_date)
		(row,) = self.get_balance_rows(item, id_plant=[plant_a], from_date=from_date)
		self.assertEqual((row.opening_qty, row.in_qty), (4, 2))
		opening = stock_ledger(self.get_filters(item, id_plant=[plant_a], from_date=from_date))[1][0]
		self.assertEqual((opening["qty_after_transaction"], opening["stock_value"]), (4, 400))
		self.assertStockLedger(item, 6, 600, id_plant=[plant_a], from_date=from_date)

	def test_reconciliation_of_a_batch_with_an_inventory_dimension(self):
		plant_a, plant_b = make_plant_dimension()
		item = self.make_batch_item()
		batches = {
			plant: get_batch_from_bundle(
				self.receive_into_plant(item, 10, plant).items[0].serial_and_batch_bundle
			)
			for plant in (plant_a, plant_b)
		}
		self.reconcile_plant(item, 4, plant_a, batch_no=batches[plant_a], use_serial_batch_fields=1)

		self.assertReportsMatchLedger(item, 14, 1400)
		self.assertStockBalance(item, 4, 400, id_plant=[plant_a])
		self.assertStockBalance(item, 10, 1000, id_plant=[plant_b])
		self.assertStockLedger(item, 4, 400, id_plant=[plant_a])
		self.assertStockLedger(item, 10, 1000, id_plant=[plant_b])

	def strand_stock_value(self, item_code, value, warehouse=STORES, **extra):
		receipt = self.receive(item_code, 10, warehouse=warehouse, days_ago=10, **extra)
		make_stock_entry(
			item_code=item_code,
			from_warehouse=warehouse,
			qty=10,
			posting_date=add_days(today(), -9),
			batch_no=get_batch_from_bundle(receipt.items[0].serial_and_batch_bundle)
			if receipt.items[0].serial_and_batch_bundle
			else None,
			use_serial_batch_fields=1,
		)
		receipt_entry = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": receipt.name}, "name")
		frappe.db.set_value(
			"Stock Ledger Entry",
			receipt_entry,
			"stock_value_difference",
			flt(frappe.db.get_value("Stock Ledger Entry", receipt_entry, "stock_value_difference")) + value,
		)
		return receipt

	def make_adjustment_entry(self, item_code, warehouse=STORES, days_ago=6, **row):
		reconciliation = self.reconcile(
			item_code, 0, rate=0, warehouse=warehouse, days_ago=days_ago, do_not_save=True
		)
		reconciliation.items[0].update({"allow_zero_valuation_rate": 1, **row})
		reconciliation.insert()
		reconciliation.submit()
		self.assertEqual(
			frappe.get_all(
				"Stock Ledger Entry",
				filters={"voucher_no": reconciliation.name, "is_cancelled": 0},
				pluck="is_adjustment_entry",
			),
			[1],
		)
		return reconciliation

	def test_adjustment_entry_writes_off_stranded_value(self):
		item = self.make_stock_item()
		self.strand_stock_value(item, 500)
		self.make_adjustment_entry(item)

		self.assertReportsMatchLedger(item, 0, 0, include_zero_stock_items=1)
		(row,) = self.get_balance_rows(item, include_zero_stock_items=1)
		self.assertEqual((row.in_qty, row.out_qty, row.out_val), (10, 10, 1500))

	def test_adjustment_entry_before_the_from_date(self):
		item = self.make_stock_item()
		self.strand_stock_value(item, 500)
		self.make_adjustment_entry(item)
		self.receive(item, 3, days_ago=1)

		from_date = add_days(today(), -3)
		self.assertReportsMatchLedger(item, 3, 300, from_date=from_date)
		(row,) = self.get_balance_rows(item, from_date=from_date)
		self.assertEqual((row.opening_qty, row.opening_val, row.in_qty), (0, 0, 3))

	def test_adjustment_entry_is_not_a_balance_for_later_entries(self):
		item = self.make_stock_item()
		self.strand_stock_value(item, 500)
		self.make_adjustment_entry(item)
		self.receive(item, 4, days_ago=5)
		self.reconcile(item, 6, days_ago=2)

		self.assertReportsMatchLedger(item, 6, 600)
		adjustment = next(row for row in self.get_ledger_rows(item) if row.stock_value_difference == -500)
		self.assertEqual((adjustment.in_qty, adjustment.out_qty, adjustment.qty_after_transaction), (0, 0, 0))

	def test_adjustment_entry_of_a_batch_item(self):
		item = self.make_batch_item()
		self.strand_stock_value(item, 300)
		self.make_adjustment_entry(item)

		self.assertReportsMatchLedger(item, 0, 0, include_zero_stock_items=1)

	def test_adjustment_entry_with_an_inventory_dimension(self):
		plant_a, _plant_b = make_plant_dimension()
		item = self.make_stock_item()
		self.strand_stock_value(item, 500)
		frappe.db.set_value("Stock Ledger Entry", {"item_code": item}, "id_plant", plant_a)
		self.make_adjustment_entry(item, id_plant=plant_a)
		self.receive(item, 2, days_ago=1)

		self.assertReportsMatchLedger(item, 2, 200)
		self.assertStockBalance(item, 0, 0, id_plant=[plant_a], include_zero_stock_items=1)
		self.assertStockLedger(item, 0, 0, id_plant=[plant_a])
		rows = self.get_balance_rows(item, show_dimension_wise_stock=1, include_zero_stock_items=1)
		self.assertEqual(sum(row.bal_qty for row in rows), 2)
		self.assertEqual(sum(row.bal_val for row in rows), 200)

	def close_stock(self, days_ago):
		from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
			prepare_closing_stock_balance,
		)

		closing = frappe.new_doc("Stock Closing Entry")
		closing.company = "_Test Company"
		closing.to_date = add_days(today(), -days_ago)
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			closing.submit()
		prepare_closing_stock_balance(closing.name)

	def test_reconciliation_before_a_stock_closing(self):
		item = self.make_stock_item()
		self.receive(item, 10, days_ago=20)
		self.reconcile(item, 4, days_ago=18)
		self.close_stock(15)
		self.receive(item, 2, days_ago=5)
		self.reconcile(item, 9, days_ago=2)

		from_date = add_days(today(), -10)
		self.assertReportsMatchLedger(item, 9, 900, from_date=from_date)
		(row,) = self.get_balance_rows(item, from_date=from_date)
		self.assertEqual((row.opening_qty, row.opening_val, row.in_qty), (4, 400, 5))

	def test_batch_reconciliation_before_a_stock_closing(self):
		item = self.make_batch_item()
		batch = get_batch_from_bundle(self.receive(item, 10, days_ago=20).items[0].serial_and_batch_bundle)
		self.receive(item, 5, rate=200, days_ago=20)
		self.reconcile(item, 6, batch_no=batch, reconcile_all_serial_batch=0, days_ago=18)
		self.close_stock(15)
		self.receive(item, 1, days_ago=5)

		from_date = add_days(today(), -10)
		self.assertReportsMatchLedger(item, 12, 1700, from_date=from_date)
		(row,) = self.get_balance_rows(item, from_date=from_date)
		self.assertEqual((row.opening_qty, row.opening_val), (11, 1600))

	def test_serial_reconciliation_before_a_stock_closing(self):
		item = self.make_serial_item()
		receipt = self.receive(item, 5, days_ago=20)
		self.reconcile(
			item,
			3,
			serial_no=get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)[:3],
			days_ago=18,
		)
		self.close_stock(15)

		from_date = add_days(today(), -10)
		self.assertReportsMatchLedger(item, 3, 300, from_date=from_date)
		(row,) = self.get_balance_rows(item, from_date=from_date)
		self.assertEqual((row.opening_qty, row.opening_val), (3, 300))

	def test_inventory_dimension_reconciliation_before_a_stock_closing(self):
		plant_a, plant_b = make_plant_dimension()
		item = self.make_stock_item()
		self.receive_into_plant(item, 10, plant_b, days_ago=20)
		self.reconcile_plant(item, 4, plant_a, days_ago=18)
		self.close_stock(15)
		self.receive_into_plant(item, 2, plant_a, days_ago=5)

		from_date = add_days(today(), -10)
		self.assertReportsMatchLedger(item, 16, 1600, from_date=from_date)
		self.assertStockBalance(item, 6, 600, id_plant=[plant_a], from_date=from_date)
		self.assertStockBalance(item, 10, 1000, id_plant=[plant_b], from_date=from_date)
		rows = self.get_balance_rows(item, show_dimension_wise_stock=1, from_date=from_date)
		self.assertEqual(
			{row.id_plant: (row.bal_qty, row.bal_val) for row in rows},
			{plant_a: (6, 600), plant_b: (10, 1000)},
		)

	def test_adjustment_entry_before_a_stock_closing(self):
		item = self.make_stock_item()
		self.strand_stock_value(item, 500)
		self.make_adjustment_entry(item)
		self.close_stock(5)
		self.receive(item, 3, days_ago=2)

		from_date = add_days(today(), -3)
		self.assertReportsMatchLedger(item, 3, 300, from_date=from_date)
		(row,) = self.get_balance_rows(item, from_date=from_date)
		self.assertEqual((row.opening_qty, row.opening_val), (0, 0))
