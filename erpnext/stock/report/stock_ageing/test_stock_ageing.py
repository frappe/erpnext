# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, format_report_data, get_average_age
from erpnext.tests.utils import ERPNextTestSuite


class TestStockAgeing(ERPNextTestSuite):
	def setUp(self) -> None:
		self.filters = frappe._dict(company="_Test Company", to_date="2021-12-10", ranges=["30", "60", "90"])

	def test_normal_inward_outward_queue(self):
		"Reference: Case 1 in stock_ageing_fifo_logic.md (same wh)"
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=30,
				qty_after_transaction=30,
				stock_value_difference=30,
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
				stock_value_difference=20,
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
				stock_value_difference=(-10),
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
		data = format_report_data(self.filters, slots, self.filters["to_date"])
		self.assertEqual(data[0][8], 40.0)  # valuating for stock value between age 0-30

	def test_insufficient_balance(self):
		"Reference: Case 3 in stock_ageing_fifo_logic.md (same wh)"
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=(-30),
				qty_after_transaction=(-30),
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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

	def test_item_filter_supports_multi_select_values(self):
		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		query = frappe.qb.from_(bundle).select(bundle.name)

		filtered_query = FIFOSlots(frappe._dict(item_code=["Item A"]), [])._apply_filter(
			query, bundle, "item_code"
		)

		sql = filtered_query.get_sql()
		self.assertIn(" IN ", sql)
		self.assertNotIn("=[", sql)

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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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
				stock_value_difference=0,
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

	def test_ageing_stock_valuation(self):
		"Test stock valuation for each time bucket."
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=10,
				qty_after_transaction=10,
				stock_value_difference=10,
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
				qty_after_transaction=30,
				stock_value_difference=20,
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
				qty_after_transaction=20,
				stock_value_difference=(-10),
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
				qty_after_transaction=30,
				stock_value_difference=20,
				warehouse="WH 1",
				posting_date="2022-01-01",
				voucher_type="Stock Entry",
				voucher_no="004",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-15),
				qty_after_transaction=15,
				stock_value_difference=(-15),
				warehouse="WH 1",
				posting_date="2022-01-02",
				voucher_type="Stock Entry",
				voucher_no="005",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=10,
				qty_after_transaction=25,
				stock_value_difference=5,
				warehouse="WH 1",
				posting_date="2022-02-01",
				voucher_type="Stock Entry",
				voucher_no="006",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=5,
				qty_after_transaction=30,
				stock_value_difference=2.5,
				warehouse="WH 1",
				posting_date="2022-02-02",
				voucher_type="Stock Entry",
				voucher_no="007",
				has_serial_no=False,
				serial_no=None,
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=5,
				qty_after_transaction=35,
				stock_value_difference=15,
				warehouse="WH 1",
				posting_date="2022-03-01",
				voucher_type="Stock Entry",
				voucher_no="008",
				has_serial_no=False,
				serial_no=None,
			),
		]

		slots = FIFOSlots(self.filters, sle).generate()
		report_data = format_report_data(self.filters, slots, "2022-03-31")
		range_values = report_data[0][7:15]
		range_valuations = range_values[1::2]
		self.assertEqual(range_valuations, [15, 7.5, 20, 5])

	def test_batch_item_report_formatting_preserves_mixed_fifo_slots(self):
		item_details = {
			"Batch Mixed Item": {
				"details": frappe._dict(
					name="Batch Mixed Item",
					item_name="Batch Mixed Item",
					description="Batch Mixed Item",
					item_group=None,
					brand=None,
					has_batch_no=True,
					stock_uom="Nos",
				),
				"fifo_queue": [
					["SA-BATCH-MIXED-SLOT", 1, 5.0, "2021-12-01", 50.0],
					[3.0, "2021-12-02", 30.0],
				],
				"has_serial_no": False,
				"total_qty": 8.0,
			}
		}

		report_data = format_report_data(self.filters, item_details, self.filters["to_date"])

		self.assertEqual(report_data[0][7:15], [8.0, 80.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

	def test_average_age_accepts_batchwise_valuation_slots(self):
		fifo_queue = [["SA-BATCH-SLOT", 1, 5.0, "2021-12-01", 50.0]]

		self.assertEqual(get_average_age(fifo_queue, "2021-12-10"), 9.0)

	def test_serial_transfer_replay_preserves_serial_slots(self):
		fifo_slots = FIFOSlots(self.filters, [])
		transfer_key = ("001", "Serial Item", "WH 1")
		fifo_slots.transferred_item_details[transfer_key] = [[2, "2021-12-01", 20]]

		row = frappe._dict(
			name="Serial Item",
			actual_qty=2,
			stock_value_difference=20,
			posting_date="2021-12-05",
			has_serial_no=True,
		)
		fifo_queue = []

		fifo_slots._compute_incoming_stock(row, fifo_queue, transfer_key, ["SN-A", "SN-B"], [])

		self.assertEqual(fifo_queue, [["SN-A", "2021-12-01", 10.0], ["SN-B", "2021-12-01", 10.0]])
		self.assertFalse(fifo_slots.transferred_item_details[transfer_key])

	def test_batch_transfer_replay_removes_zeroed_negative_slot(self):
		fifo_slots = FIFOSlots(self.filters, [])
		fifo_queue = [["SA-ZERO-BATCH", 1, -4, "2021-12-01", -40]]

		fifo_slots._add_transfer_slot_to_fifo_queue(fifo_queue, ["SA-ZERO-BATCH", 1, 4, "2021-12-02", 40])

		self.assertEqual(fifo_queue, [])

	def test_batchwise_valuation(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(
			"Test Stock Ageing Batchwise Valuation",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"valuation_method": "FIFO",
			},
		).name

		def make_batch(batch_id, use_batchwise_valuation):
			if not frappe.db.exists("Batch", batch_id):
				frappe.get_doc(
					{
						"doctype": "Batch",
						"batch_id": batch_id,
						"item": item_code,
					}
				).insert(ignore_permissions=True)

			frappe.db.set_value("Batch", batch_id, "use_batchwise_valuation", use_batchwise_valuation)

		batchwise_above_90 = "SA-BATCHWISE-ABOVE-90"
		non_batchwise_above_90 = "SA-NON-BATCHWISE-ABOVE-90"
		batchwise_61_90 = "SA-BATCHWISE-61-90"
		non_batchwise_61_90 = "SA-NON-BATCHWISE-61-90"
		batchwise_31_60 = "SA-BATCHWISE-31-60"
		non_batchwise_31_60 = "SA-NON-BATCHWISE-31-60"
		batchwise_0_30 = "SA-BATCHWISE-0-30"
		non_batchwise_0_30 = "SA-NON-BATCHWISE-0-30"

		for batch_id, use_batchwise_valuation in {
			batchwise_above_90: 1,
			non_batchwise_above_90: 0,
			batchwise_61_90: 1,
			non_batchwise_61_90: 0,
			batchwise_31_60: 1,
			non_batchwise_31_60: 0,
			batchwise_0_30: 1,
			non_batchwise_0_30: 0,
		}.items():
			make_batch(batch_id, use_batchwise_valuation)

		qty_after_transaction = 0

		def make_sle(posting_date, voucher_no, batch_no, actual_qty, stock_value_difference):
			nonlocal qty_after_transaction

			qty_after_transaction += actual_qty
			return frappe._dict(
				name=item_code,
				actual_qty=actual_qty,
				qty_after_transaction=qty_after_transaction,
				stock_value_difference=stock_value_difference,
				warehouse="WH 1",
				posting_date=posting_date,
				voucher_type="Stock Entry",
				voucher_no=voucher_no,
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=batch_no,
				valuation_rate=10,
			)

		sle = [
			make_sle("2021-08-01", "001", batchwise_above_90, 50, 500),
			make_sle("2021-08-10", "002", non_batchwise_above_90, 60, 600),
			make_sle("2021-08-20", "003", batchwise_above_90, -10, -100),
			make_sle("2021-09-01", "004", non_batchwise_above_90, -15, -150),
			make_sle("2021-09-20", "005", batchwise_61_90, 40, 400),
			make_sle("2021-09-25", "006", non_batchwise_61_90, 50, 500),
			make_sle("2021-09-30", "007", batchwise_61_90, -5, -50),
			make_sle("2021-10-05", "008", non_batchwise_above_90, -20, -200),
			make_sle("2021-10-20", "009", batchwise_31_60, 30, 300),
			make_sle("2021-10-25", "010", non_batchwise_31_60, 40, 400),
			make_sle("2021-10-30", "011", batchwise_31_60, -8, -80),
			make_sle("2021-11-05", "012", non_batchwise_above_90, -25, -250),
			make_sle("2021-11-20", "013", batchwise_0_30, 20, 200),
			make_sle("2021-11-25", "014", non_batchwise_0_30, 30, 300),
			make_sle("2021-11-30", "015", batchwise_0_30, -6, -60),
			make_sle("2021-12-01", "016", non_batchwise_61_90, -10, -100),
		]

		slots = FIFOSlots(self.filters, sle).generate()
		item_result = slots[item_code]

		self.assertEqual(item_result["qty_after_transaction"], item_result["total_qty"])
		self.assertEqual(item_result["total_qty"], 221.0)
		self.assertEqual(
			item_result["fifo_queue"],
			[
				[batchwise_above_90, 1, 40.0, "2021-08-01", 400.0],
				[batchwise_61_90, 1, 35.0, "2021-09-20", 350.0],
				[non_batchwise_61_90, 0, 40.0, "2021-09-25", 400.0],
				[batchwise_31_60, 1, 22.0, "2021-10-20", 220.0],
				[non_batchwise_31_60, 0, 40, "2021-10-25", 400],
				[batchwise_0_30, 1, 14.0, "2021-11-20", 140.0],
				[non_batchwise_0_30, 0, 30, "2021-11-25", 300],
			],
		)

		report_data = format_report_data(self.filters, slots, self.filters["to_date"])
		range_values = report_data[0][7:15]
		self.assertEqual(range_values, [44.0, 440.0, 62.0, 620.0, 75.0, 750.0, 40.0, 400.0])

	def test_batchwise_valuation_same_voucher_transfer(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(
			"Test Stock Ageing Batchwise Transfer",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"valuation_method": "FIFO",
			},
		).name

		def make_batch(batch_id):
			if not frappe.db.exists("Batch", batch_id):
				frappe.get_doc(
					{
						"doctype": "Batch",
						"batch_id": batch_id,
						"item": item_code,
					}
				).insert(ignore_permissions=True)

			frappe.db.set_value("Batch", batch_id, "use_batchwise_valuation", 1)

		source_batch = "SA-BATCHWISE-TRANSFER-SOURCE"
		target_batch = "SA-BATCHWISE-TRANSFER-TARGET"
		make_batch(source_batch)
		make_batch(target_batch)

		sle = [
			frappe._dict(
				name=item_code,
				actual_qty=20,
				qty_after_transaction=20,
				stock_value_difference=200,
				warehouse="WH 1",
				posting_date="2021-09-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=source_batch,
				valuation_rate=10,
			),
			frappe._dict(
				name=item_code,
				actual_qty=-15,
				qty_after_transaction=5,
				stock_value_difference=-150,
				warehouse="WH 1",
				posting_date="2021-10-01",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=source_batch,
				valuation_rate=10,
			),
			frappe._dict(
				name=item_code,
				actual_qty=10,
				qty_after_transaction=15,
				stock_value_difference=100,
				warehouse="WH 1",
				posting_date="2021-10-01",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=target_batch,
				valuation_rate=10,
			),
		]

		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots[item_code]

		self.assertEqual(item_result["total_qty"], 15.0)
		self.assertEqual(
			item_result["fifo_queue"],
			[
				[source_batch, 1, 5.0, "2021-09-01", 50.0],
				[target_batch, 1, 10.0, "2021-09-01", 100.0],
			],
		)
		self.assertEqual(
			fifo_slots.transferred_item_details[("002", item_code, "WH 1")],
			[[5.0, "2021-09-01", 50.0]],
		)

	def test_batchwise_valuation_negative_stock_same_voucher(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(
			"Test Stock Ageing Batchwise Negative Stock",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"valuation_method": "FIFO",
			},
		).name

		batch_no = "SA-BATCHWISE-NEGATIVE-STOCK"
		if not frappe.db.exists("Batch", batch_no):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_no,
					"item": item_code,
				}
			).insert(ignore_permissions=True)

		frappe.db.set_value("Batch", batch_no, "use_batchwise_valuation", 1)

		sle = [
			frappe._dict(
				name=item_code,
				actual_qty=-10,
				qty_after_transaction=-10,
				stock_value_difference=-100,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=batch_no,
				valuation_rate=10,
			)
		]

		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots[item_code]

		self.assertEqual(item_result["fifo_queue"], [[batch_no, 1, -10, "2021-12-01", -100]])
		self.assertEqual(
			fifo_slots.transferred_item_details[("001", item_code, "WH 1")], [[10, "2021-12-01", 100]]
		)

		sle.append(
			frappe._dict(
				name=item_code,
				actual_qty=6,
				qty_after_transaction=-4,
				stock_value_difference=60,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=batch_no,
				valuation_rate=10,
			)
		)

		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots[item_code]

		self.assertEqual(item_result["fifo_queue"], [[batch_no, 1, -4.0, "2021-12-01", -40.0]])
		self.assertEqual(
			fifo_slots.transferred_item_details[("001", item_code, "WH 1")],
			[[4.0, "2021-12-01", 40.0]],
		)

	def test_batchwise_valuation_neutralizes_non_head_negative_batch(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(
			"Test Stock Ageing Batchwise Negative Non Head",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"valuation_method": "FIFO",
			},
		).name

		buffer_batch = "SA-BATCHWISE-NEGATIVE-BUFFER"
		negative_batch = "SA-BATCHWISE-NEGATIVE-NON-HEAD"
		for batch_no in [buffer_batch, negative_batch]:
			if not frappe.db.exists("Batch", batch_no):
				frappe.get_doc(
					{
						"doctype": "Batch",
						"batch_id": batch_no,
						"item": item_code,
					}
				).insert(ignore_permissions=True)

			frappe.db.set_value("Batch", batch_no, "use_batchwise_valuation", 1)

		sle = [
			frappe._dict(
				name=item_code,
				actual_qty=5,
				qty_after_transaction=5,
				stock_value_difference=50,
				warehouse="WH 1",
				posting_date="2021-11-30",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=buffer_batch,
				valuation_rate=10,
			),
			frappe._dict(
				name=item_code,
				actual_qty=-10,
				qty_after_transaction=-5,
				stock_value_difference=-100,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=negative_batch,
				valuation_rate=10,
			),
			frappe._dict(
				name=item_code,
				actual_qty=6,
				qty_after_transaction=1,
				stock_value_difference=60,
				warehouse="WH 1",
				posting_date="2021-12-01",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=negative_batch,
				valuation_rate=10,
			),
		]

		fifo_slots = FIFOSlots(self.filters, sle)
		slots = fifo_slots.generate()
		item_result = slots[item_code]

		self.assertEqual(item_result["qty_after_transaction"], item_result["total_qty"])
		self.assertEqual(
			item_result["fifo_queue"],
			[
				[buffer_batch, 1, 5, "2021-11-30", 50],
				[negative_batch, 1, -4.0, "2021-12-01", -40.0],
			],
		)
		self.assertEqual(
			fifo_slots.transferred_item_details[("002", item_code, "WH 1")],
			[[4.0, "2021-12-01", 40.0]],
		)

	def test_batchwise_valuation_negative_stock_later_voucher(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(
			"Test Stock Ageing Batchwise Negative Later Voucher",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"valuation_method": "FIFO",
			},
		).name

		batch_no = "SA-BATCHWISE-NEGATIVE-LATER-VOUCHER"
		if not frappe.db.exists("Batch", batch_no):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_no,
					"item": item_code,
				}
			).insert(ignore_permissions=True)

		frappe.db.set_value("Batch", batch_no, "use_batchwise_valuation", 1)

		sle = [
			frappe._dict(
				name=item_code,
				actual_qty=-10,
				qty_after_transaction=-10,
				stock_value_difference=-100,
				warehouse="WH 1",
				posting_date="2021-11-01",
				voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=batch_no,
				valuation_rate=10,
			),
			frappe._dict(
				name=item_code,
				actual_qty=6,
				qty_after_transaction=-4,
				stock_value_difference=60,
				warehouse="WH 1",
				posting_date="2021-11-10",
				voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False,
				has_batch_no=True,
				serial_no=None,
				batch_no=batch_no,
				valuation_rate=10,
			),
		]

		slots = FIFOSlots(self.filters, sle).generate()
		item_result = slots[item_code]

		self.assertEqual(item_result["qty_after_transaction"], item_result["total_qty"])
		self.assertEqual(item_result["total_qty"], -4.0)
		self.assertEqual(item_result["fifo_queue"], [[batch_no, 1, -4.0, "2021-11-10", -40.0]])

	def test_batchwise_valuation_stock_reconciliation_with_bundle(self):
		from frappe.utils import add_days, getdate, nowdate

		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_batch_from_bundle,
		)
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		suffix = frappe.generate_hash(length=8).upper()
		item_code = make_item(
			f"Test Stock Ageing Batch Reco {suffix}",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": f"SA-RECO-{suffix}-.###",
				"valuation_method": "FIFO",
			},
		).name
		warehouse = "_Test Warehouse - _TC"
		base_date = nowdate()

		opening_reco = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=12,
			rate=10,
			posting_date=add_days(base_date, -2),
			posting_time="10:00:00",
		)
		batch_no = get_batch_from_bundle(opening_reco.items[0].serial_and_batch_bundle)
		frappe.db.set_value("Batch", batch_no, "use_batchwise_valuation", 1)

		create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=5,
			rate=10,
			batch_no=batch_no,
			posting_date=add_days(base_date, -1),
			posting_time="10:00:00",
		)

		filters = frappe._dict(
			company="_Test Company",
			to_date=base_date,
			ranges=["30", "60", "90"],
			item_code=item_code,
		)
		slots = FIFOSlots(filters).generate()
		item_result = slots[item_code]

		self.assertEqual(item_result["qty_after_transaction"], item_result["total_qty"])
		self.assertEqual(item_result["total_qty"], 5.0)
		self.assertEqual(
			item_result["fifo_queue"], [[batch_no.upper(), 1, 5.0, getdate(add_days(base_date, -2)), 50.0]]
		)

	def test_legacy_batch_no_sle_with_streaming_cursor(self):
		"""SLEs carrying the legacy batch_no field must not trigger nested
		queries while entries stream through an unbuffered cursor."""
		from unittest.mock import patch

		from frappe.utils import add_days, nowdate

		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_batch_from_bundle,
		)
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		suffix = frappe.generate_hash(length=8).upper()
		item_code = make_item(
			f"Test Stock Ageing Legacy Batch {suffix}",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": f"SA-LEG-{suffix}-.###",
				"valuation_method": "FIFO",
			},
		).name
		warehouse = "_Test Warehouse - _TC"
		base_date = nowdate()

		reco = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=10,
			rate=10,
			posting_date=add_days(base_date, -2),
			posting_time="10:00:00",
		)
		batch_no = get_batch_from_bundle(reco.items[0].serial_and_batch_bundle)
		frappe.db.set_value("Batch", batch_no, "use_batchwise_valuation", 1)

		create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=5,
			rate=10,
			batch_no=batch_no,
			posting_date=add_days(base_date, -1),
			posting_time="10:00:00",
		)

		# mimic pre-bundle data where SLEs carry batch_no directly
		frappe.db.set_value(
			"Stock Ledger Entry",
			{"item_code": item_code},
			"batch_no",
			batch_no,
		)

		filters = frappe._dict(
			company="_Test Company",
			to_date=base_date,
			ranges=["30", "60", "90"],
			item_code=item_code,
		)
		fifo_slots = FIFOSlots(filters)

		# fetch row by row so the streaming result set is still active
		# while each stock ledger entry is processed
		with patch("frappe.database.database.SQL_ITERATOR_BATCH_SIZE", 1):
			slots = fifo_slots.generate()

		self.assertEqual(fifo_slots.batchwise_valuation_by_batch.get(batch_no), 1)
		self.assertEqual(slots[item_code]["total_qty"], 5.0)


def generate_item_and_item_wh_wise_slots(filters, sle):
	"Return results with and without 'show_warehouse_wise_stock'"
	item_wise_slots = FIFOSlots(filters, sle).generate()

	filters.show_warehouse_wise_stock = True
	item_wh_wise_slots = FIFOSlots(filters, sle).generate()
	filters.show_warehouse_wise_stock = False

	return item_wise_slots, item_wh_wise_slots
