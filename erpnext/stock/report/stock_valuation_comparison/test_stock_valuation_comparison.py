# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_return
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.stock.expected_valuation import (
	BASIS_BATCH_AVERAGE,
	BASIS_PURCHASE_RETURN,
	BASIS_SERIAL_RATE,
	MovingAveragePool,
	QueuePool,
	get_expected_valuation,
)
from erpnext.stock.report.stock_valuation_comparison.stock_valuation_comparison import (
	SHOW_ALL_DIFFERENCES,
	SHOW_ALL_ENTRIES,
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "_Test Warehouse - _TC"


class TestValuationPools(ERPNextTestSuite):
	def test_fifo_issues_oldest_layer_first(self):
		pool = QueuePool()
		pool.receive(10, 100)
		pool.receive(10, 120)

		self.assertEqual(pool.issue(15), 10 * 100 + 5 * 120)
		self.assertEqual(pool.layers, [[5, 120]])

	def test_lifo_issues_newest_layer_first(self):
		pool = QueuePool(last_in_first_out=True)
		pool.receive(10, 100)
		pool.receive(10, 120)

		self.assertEqual(pool.issue(15), 10 * 120 + 5 * 100)
		self.assertEqual(pool.layers, [[5, 100]])

	def test_fifo_return_takes_layer_of_its_receipt_rate(self):
		pool = QueuePool()
		pool.receive(10, 100)
		pool.receive(10, 120)

		self.assertEqual(pool.issue(4, preferred_rate=120), 4 * 120)
		self.assertEqual(pool.layers, [[10, 100], [6, 120]])

	def test_queue_goes_negative_and_receipt_makes_up_the_shortfall(self):
		pool = QueuePool()
		pool.receive(5, 100)
		pool.issue(8)
		self.assertEqual(pool.layers, [[-3, 100]])

		pool.receive(10, 110)
		self.assertEqual(pool.layers, [[7, 110]])

	def test_moving_average(self):
		pool = MovingAveragePool()
		pool.receive(10, 100)
		pool.receive(10, 120)
		self.assertEqual(pool.rate, 110)

		self.assertEqual(pool.issue(5), 550)
		self.assertEqual(pool.qty, 15)
		self.assertEqual(pool.rate, 110)

	def test_moving_average_receipt_after_shortfall_resets_rate(self):
		pool = MovingAveragePool()
		pool.receive(5, 100)
		pool.issue(8)
		pool.receive(10, 130)

		self.assertEqual(pool.qty, 7)
		self.assertEqual(pool.rate, 130)


class TestStockValuationComparison(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)

	def run_report(self, item_code, show=SHOW_ALL_DIFFERENCES, **filters):
		return execute(frappe._dict(company="_Test Company", item_code=item_code, show=show, **filters))[1]

	def assertNoDifferences(self, item_code):
		differences = self.run_report(item_code)
		self.assertEqual(differences, [], msg=frappe.as_json(differences))

	def test_fifo_ledger_matches_expected(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100)
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=120)
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=15)

		self.assertNoDifferences(item)

		issue = get_expected_valuation(item, WAREHOUSE)[-1][1]
		self.assertEqual(issue.stock_value_difference, -(10 * 100 + 5 * 120))
		self.assertEqual(issue.stock_value, 5 * 120)

	def test_moving_average_ledger_matches_expected(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "Moving Average"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100)
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=120)
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=5)

		self.assertNoDifferences(item)

		issue = get_expected_valuation(item, WAREHOUSE)[-1][1]
		self.assertEqual(issue.stock_value_difference, -5 * 110)

	def test_batch_wise_valued_batches_go_out_at_their_own_rate(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"valuation_method": "FIFO",
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SVC-BWV-.#####",
			}
		).name

		first = make_purchase_receipt(item_code=item, warehouse=WAREHOUSE, qty=10, rate=100)
		make_purchase_receipt(item_code=item, warehouse=WAREHOUSE, qty=10, rate=150)
		first_batch = get_batch_of_receipt(first)
		self.assertTrue(frappe.db.get_value("Batch", first_batch, "use_batchwise_valuation"))

		make_stock_entry(item_code=item, source=WAREHOUSE, qty=4, batch_no=first_batch)

		self.assertNoDifferences(item)

		issue = get_expected_valuation(item, WAREHOUSE)[-1][1]
		self.assertEqual(issue.stock_value_difference, -4 * 100)
		self.assertEqual(issue.basis, BASIS_BATCH_AVERAGE)

	def test_batches_without_batch_wise_valuation_go_through_the_fifo_queue(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"valuation_method": "FIFO",
				"has_batch_no": 1,
			}
		).name

		first_batch, second_batch = (make_batch_without_batch_wise_valuation(item) for _i in range(2))
		make_purchase_receipt(item_code=item, warehouse=WAREHOUSE, qty=10, rate=100, batch_no=first_batch)
		make_purchase_receipt(item_code=item, warehouse=WAREHOUSE, qty=10, rate=150, batch_no=second_batch)

		# issued from the newer batch, but valued from the oldest layer of the queue
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=4, batch_no=second_batch)

		self.assertNoDifferences(item)

		issue = get_expected_valuation(item, WAREHOUSE)[-1][1]
		self.assertEqual(issue.stock_value_difference, -4 * 100)

	def test_serial_nos_go_out_at_their_receipt_rate(self):
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SVC-SR-.#####"}
		).name

		first = make_stock_entry(item_code=item, target=WAREHOUSE, qty=2, rate=100)
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=2, rate=200)
		serial_no = get_serial_nos_of_entry(first)[0]

		make_stock_entry(item_code=item, source=WAREHOUSE, qty=1, serial_no=[serial_no])

		self.assertNoDifferences(item)

		issue = get_expected_valuation(item, WAREHOUSE)[-1][1]
		self.assertEqual(issue.stock_value_difference, -100)
		self.assertEqual(issue.basis, BASIS_SERIAL_RATE)

	def test_serial_nos_without_serial_no_wise_valuation_go_out_at_the_pool_rate(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SVC-NSV-.#####",
				"valuation_method": "Moving Average",
				"use_serial_no_wise_valuation": 0,
			}
		).name

		first = make_stock_entry(item_code=item, target=WAREHOUSE, qty=2, rate=100)
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=2, rate=200)
		serial_no = get_serial_nos_of_entry(first)[0]

		# the serial no came in at 100, but goes out at the item's moving average
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=1, serial_no=[serial_no])

		self.assertNoDifferences(item)

		issue = get_expected_valuation(item, WAREHOUSE)[-1][1]
		self.assertEqual(issue.stock_value_difference, -150)

	def test_moving_average_with_fractional_rates_has_no_rounding_differences(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "Moving Average"}).name

		for qty, rate in ((3, 10.333), (7, 12.777), (11, 9.119), (13, 14.421)):
			make_stock_entry(item_code=item, target=WAREHOUSE, qty=qty, rate=rate)
			make_stock_entry(item_code=item, source=WAREHOUSE, qty=2)

		rows = self.run_report(item, tolerance=0)
		self.assertEqual(rows, [], msg=frappe.as_json(rows))

	def test_zero_tolerance_shows_every_difference(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100)
		issue = make_stock_entry(item_code=item, source=WAREHOUSE, qty=4)

		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": issue.name, "is_cancelled": 0}, "name")
		frappe.db.set_value(
			"Stock Ledger Entry", sle, "stock_value_difference", -400.005, update_modified=False
		)

		self.assertEqual(self.run_report(item), [])
		self.assertEqual(len(self.run_report(item, tolerance=0)), 1)

	def test_fifo_purchase_return_goes_out_at_the_returned_receipt_rate(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		make_purchase_receipt(item_code=item, warehouse=WAREHOUSE, qty=10, rate=100)
		second = make_purchase_receipt(item_code=item, warehouse=WAREHOUSE, qty=10, rate=150)

		purchase_return = make_purchase_return(second.name)
		purchase_return.items[0].qty = -4
		purchase_return.items[0].received_qty = -4
		purchase_return.submit()

		self.assertNoDifferences(item)

		issue = get_expected_valuation(item, WAREHOUSE)[-1][1]
		self.assertEqual(issue.stock_value_difference, -4 * 150)
		self.assertEqual(issue.basis, BASIS_PURCHASE_RETURN)

	def test_stock_reconciliation_sets_qty_and_rate(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100)
		create_stock_reconciliation(item_code=item, warehouse=WAREHOUSE, qty=6, rate=130)
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=2)

		self.assertNoDifferences(item)

		reconciliation, issue = (expected for _entry, expected in get_expected_valuation(item, WAREHOUSE)[1:])
		self.assertEqual(reconciliation.stock_value, 6 * 130)
		self.assertEqual(issue.stock_value_difference, -2 * 130)

	def test_tampered_entry_is_reported(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100)
		issue = make_stock_entry(item_code=item, source=WAREHOUSE, qty=4)

		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": issue.name, "is_cancelled": 0}, "name")
		frappe.db.set_value("Stock Ledger Entry", sle, "stock_value_difference", -450, update_modified=False)

		rows = self.run_report(item)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].stock_ledger_entry, sle)
		self.assertEqual(flt(rows[0].stock_value_difference_difference), -50)

		all_entries = self.run_report(item, show=SHOW_ALL_ENTRIES)
		self.assertEqual(len(all_entries), 2)


def make_batch_without_batch_wise_valuation(item_code) -> str:
	batch = frappe.get_doc(doctype="Batch", batch_id=frappe.generate_hash(length=10), item=item_code).insert()
	batch.db_set("use_batchwise_valuation", 0)
	return batch.name


def get_batch_of_receipt(purchase_receipt) -> str:
	bundle = purchase_receipt.items[0].serial_and_batch_bundle
	return frappe.db.get_value("Serial and Batch Entry", {"parent": bundle}, "batch_no")


def get_serial_nos_of_entry(stock_entry) -> list[str]:
	bundle = stock_entry.items[0].serial_and_batch_bundle
	return frappe.get_all(
		"Serial and Batch Entry", filters={"parent": bundle}, pluck="serial_no", order_by="idx"
	)
