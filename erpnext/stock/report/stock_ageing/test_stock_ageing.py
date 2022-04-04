# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, format_report_data


class TestStockAgeing(FrappeTestCase):
	def setUp(self) -> None:
		self.filters = frappe._dict(
			company="_Test Company", to_date="2021-12-10", range1=30, range2=60, range3=90
		)

	def test_normal_inward_outward_queue(self):
		"Reference: Case 1 in stock_ageing_fifo_logic.md (same wh)"
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=30,
				qty_after_transaction=30,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20,
				qty_after_transaction=50,
				warehouse="WH 1",
				posting_date="2021-12-02",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10),
				qty_after_transaction=40,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False,
				serial_no=None,
			),
		]

		slots = FIFOSlots(self.filters, sle).generate()

		self.assertTrue(slots["Flask Item"]["fifo_queue"])
		result = slots["Flask Item"]
		queue = result["fifo_queue"]

		self.assertEqual(result["qty_after_transaction"], result["total_qty"])
		self.assertEqual(queue[0][0], 20.0)

	def test_insufficient_balance(self):
		"Reference: Case 3 in stock_ageing_fifo_logic.md (same wh)"
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=(-30),
				qty_after_transaction=(-30),
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20,
				qty_after_transaction=(-10),
				warehouse="WH 1",
				posting_date="2021-12-02",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20,
				qty_after_transaction=10,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=10,
				qty_after_transaction=20,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="004",
				has_serial_no=False,
				serial_no=None,
			),
		]

		slots = FIFOSlots(self.filters, sle).generate()

		result = slots["Flask Item"]
		queue = result["fifo_queue"]

		self.assertEqual(result["qty_after_transaction"], result["total_qty"])
		self.assertEqual(queue[0][0], 10.0)
		self.assertEqual(queue[1][0], 10.0)

	def test_basic_stock_reconciliation(self):
		"""
		Ledger (same wh): [+30, reco reset >> 50, -10]
		Bal: 40
		"""
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=30,
				qty_after_transaction=30,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=0,
				qty_after_transaction=50,
				warehouse="WH 1",
				posting_date="2021-12-02",
				voucher_type="Stock Reconciliation",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10),
				qty_after_transaction=40,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False,
				serial_no=None,
			),
		]

		slots = FIFOSlots(self.filters, sle).generate()

		result = slots["Flask Item"]
		queue = result["fifo_queue"]

		self.assertEqual(result["qty_after_transaction"], result["total_qty"])
		self.assertEqual(result["total_qty"], 40.0)
		self.assertEqual(queue[0][0], 20.0)
		self.assertEqual(queue[1][0], 20.0)

	def test_sequential_stock_reco_same_warehouse(self):
		"""
		Test back to back stock recos (same warehouse).
		Ledger: [reco opening >> +1000, reco reset >> 400, -10]
		Bal: 390
		"""
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=0,
				qty_after_transaction=1000,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Reconciliation",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=0,
				qty_after_transaction=400,
				warehouse="WH 1",
				posting_date="2021-12-02",
				voucher_type="Stock Reconciliation",
				voucher_no="003",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10),
				qty_after_transaction=390,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False,
				serial_no=None,
			),
		]
		slots = FIFOSlots(self.filters, sle).generate()

		result = slots["Flask Item"]
		queue = result["fifo_queue"]

		self.assertEqual(result["qty_after_transaction"], result["total_qty"])
		self.assertEqual(result["total_qty"], 390.0)
		self.assertEqual(queue[0][0], 390.0)

	def test_sequential_stock_reco_different_warehouse(self):
		"""
		Ledger:
		WH	| Voucher | Qty
		-------------------
		WH1 | Reco	  | 1000
		WH2 | Reco	  | 400
		WH1 | SE	  | -10

		Bal: WH1 bal + WH2 bal = 990 + 400 = 1390
		"""
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=0,
				qty_after_transaction=1000,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Reconciliation",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=0,
				qty_after_transaction=400,
				warehouse="WH 2",
				posting_date="2021-12-02",
				voucher_type="Stock Reconciliation",
				voucher_no="003",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10),
				qty_after_transaction=990,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="004",
				has_serial_no=False,
				serial_no=None,
			),
		]

		item_wise_slots, item_wh_wise_slots = generate_item_and_item_wh_wise_slots(
			filters=self.filters, sle=sle
		)

		# test without 'show_warehouse_wise_stock'
		item_result = item_wise_slots["Flask Item"]
		queue = item_result["fifo_queue"]

		self.assertEqual(item_result["qty_after_transaction"], item_result["total_qty"])
		self.assertEqual(item_result["total_qty"], 1390.0)
		self.assertEqual(queue[0][0], 990.0)
		self.assertEqual(queue[1][0], 400.0)

		# test with 'show_warehouse_wise_stock' checked
		item_wh_balances = [
			item_wh_wise_slots.get(i).get("qty_after_transaction") for i in item_wh_wise_slots
		]
		self.assertEqual(sum(item_wh_balances), item_result["qty_after_transaction"])

	def test_repack_entry_same_item_split_rows(self):
		"""
		Split consumption rows and have single repacked item row (same warehouse).
		Ledger:
		Item	| Qty | Voucher
		------------------------
		Item 1  | 500 | 001
		Item 1  | -50 | 002 (repack)
		Item 1  | -50 | 002 (repack)
		Item 1  | 100 | 002 (repack)

		Case most likely for batch items. Test time bucket computation.
		"""
		sle = [
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=500,
				qty_after_transaction=500,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=450,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=400,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=100,
				qty_after_transaction=500,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
		]
		slots = FIFOSlots(self.filters, sle).generate()
		item_result = slots["Flask Item"]
		queue = item_result["fifo_queue"]

		self.assertEqual(item_result["total_qty"], 500.0)
		self.assertEqual(queue[0][0], 400.0)
		self.assertEqual(queue[1][0], 50.0)
		self.assertEqual(queue[2][0], 50.0)
		# check if time buckets add up to balance qty
		self.assertEqual(sum([i[0] for i in queue]), 500.0)

	def test_repack_entry_same_item_overconsume(self):
		"""
		Over consume item and have less repacked item qty (same warehouse).
		Ledger:
		Item	| Qty  | Voucher
		------------------------
		Item 1  | 500  | 001
		Item 1  | -100 | 002 (repack)
		Item 1  | 50   | 002 (repack)

		Case most likely for batch items. Test time bucket computation.
		"""
		sle = [
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=500,
				qty_after_transaction=500,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-100),
				qty_after_transaction=400,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=50,
				qty_after_transaction=450,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
		]
		slots = FIFOSlots(self.filters, sle).generate()
		item_result = slots["Flask Item"]
		queue = item_result["fifo_queue"]

		self.assertEqual(item_result["total_qty"], 450.0)
		self.assertEqual(queue[0][0], 400.0)
		self.assertEqual(queue[1][0], 50.0)
		# check if time buckets add up to balance qty
		self.assertEqual(sum([i[0] for i in queue]), 450.0)

	def test_repack_entry_same_item_overconsume_with_split_rows(self):
		"""
		Over consume item and have less repacked item qty (same warehouse).
		Ledger:
		Item	| Qty  | Voucher
		------------------------
		Item 1  | 20   | 001
		Item 1  | -50  | 002 (repack)
		Item 1  | -50  | 002 (repack)
		Item 1  | 50   | 002 (repack)
		"""
		sle = [
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=20,
				qty_after_transaction=20,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=(-30),
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=(-80),
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=50,
				qty_after_transaction=(-30),
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
		]
		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots["Flask Item"]
		queue = item_result["fifo_queue"]

		self.assertEqual(item_result["total_qty"], -30.0)
		self.assertEqual(queue[0][0], -30.0)

		# check transfer bucket
		transfer_bucket = fifo_slots.transferred_item_details[("002", "Flask Item", "WH 1")]
		self.assertEqual(transfer_bucket[0][0], 50)

	def test_repack_entry_same_item_overproduce(self):
		"""
		Under consume item and have more repacked item qty (same warehouse).
		Ledger:
		Item	| Qty  | Voucher
		------------------------
		Item 1  | 500  | 001
		Item 1  | -50  | 002 (repack)
		Item 1  | 100  | 002 (repack)

		Case most likely for batch items. Test time bucket computation.
		"""
		sle = [
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=500,
				qty_after_transaction=500,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=450,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=100,
				qty_after_transaction=550,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
		]
		slots = FIFOSlots(self.filters, sle).generate()
		item_result = slots["Flask Item"]
		queue = item_result["fifo_queue"]

		self.assertEqual(item_result["total_qty"], 550.0)
		self.assertEqual(queue[0][0], 450.0)
		self.assertEqual(queue[1][0], 50.0)
		self.assertEqual(queue[2][0], 50.0)
		# check if time buckets add up to balance qty
		self.assertEqual(sum([i[0] for i in queue]), 550.0)

	def test_repack_entry_same_item_overproduce_with_split_rows(self):
		"""
		Over consume item and have less repacked item qty (same warehouse).
		Ledger:
		Item	| Qty  | Voucher
		------------------------
		Item 1  | 20   | 001
		Item 1  | -50  | 002 (repack)
		Item 1  | 50  | 002 (repack)
		Item 1  | 50   | 002 (repack)
		"""
		sle = [
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=20,
				qty_after_transaction=20,
				warehouse="WH 1",
				posting_date="2021-12-03",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=(-30),
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=50,
				qty_after_transaction=20,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=50,
				qty_after_transaction=70,
				warehouse="WH 1",
				posting_date="2021-12-04",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				serial_no=None,
			),
		]
		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots["Flask Item"]
		queue = item_result["fifo_queue"]

		self.assertEqual(item_result["total_qty"], 70.0)
		self.assertEqual(queue[0][0], 20.0)
		self.assertEqual(queue[1][0], 50.0)

		# check transfer bucket
		transfer_bucket = fifo_slots.transferred_item_details[("002", "Flask Item", "WH 1")]
		self.assertFalse(transfer_bucket)

	def test_negative_stock_same_voucher(self):
		"""
		Test negative stock scenario in transfer bucket via repack entry (same wh).
		Ledger:
		Item	| Qty  | Voucher
		------------------------
		Item 1  | -50  | 001
		Item 1  | -50  | 001
		Item 1  | 30   | 001
		Item 1  | 80   | 001
		"""
		sle = [
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=(-50),
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=(-50),
				qty_after_transaction=(-100),
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=30,
				qty_after_transaction=(-70),
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
		]
		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots["Flask Item"]

		# check transfer bucket
		transfer_bucket = fifo_slots.transferred_item_details[("001", "Flask Item", "WH 1")]
		self.assertEqual(transfer_bucket[0][0], 20)
		self.assertEqual(transfer_bucket[1][0], 50)
		self.assertEqual(item_result["fifo_queue"][0][0], -70.0)

		sle.append(
			frappe._dict(
				name="Flask Item",
				actual_qty=80,
				qty_after_transaction=10,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			)
		)

		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots["Flask Item"]

		transfer_bucket = fifo_slots.transferred_item_details[("001", "Flask Item", "WH 1")]
		self.assertFalse(transfer_bucket)
		self.assertEqual(item_result["fifo_queue"][0][0], 10.0)

	def test_precision(self):
		"Test if final balance qty is rounded off correctly."
		sle = [
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=0.3,
				qty_after_transaction=0.3,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(  # stock up item
				name="Flask Item",
				actual_qty=0.6,
				qty_after_transaction=0.9,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				serial_no=None,
			),
		]

		slots = FIFOSlots(self.filters, sle).generate()
		report_data = format_report_data(self.filters, slots, self.filters["to_date"])
		row = report_data[0]  # first row in report
		bal_qty = row[5]
		range_qty_sum = sum([i for i in row[7:11]])  # get sum of range balance

		# check if value of Available Qty column matches with range bucket post format
		self.assertEqual(bal_qty, 0.9)
		self.assertEqual(bal_qty, range_qty_sum)


def generate_item_and_item_wh_wise_slots(filters, sle):
	"Return results with and without 'show_warehouse_wise_stock'"
	item_wise_slots = FIFOSlots(filters, sle).generate()

	filters.show_warehouse_wise_stock = True
	item_wh_wise_slots = FIFOSlots(filters, sle).generate()
	filters.show_warehouse_wise_stock = False

	return item_wise_slots, item_wh_wise_slots
