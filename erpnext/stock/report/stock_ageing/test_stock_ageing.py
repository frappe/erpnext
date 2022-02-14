# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots
from erpnext.tests.utils import ERPNextTestCase


class TestStockAgeing(ERPNextTestCase):
	def setUp(self) -> None:
		self.filters = frappe._dict(
			company="_Test Company",
			to_date="2021-12-10"
		)

	def test_normal_inward_outward_queue(self):
		"Reference: Case 1 in stock_ageing_fifo_logic.md (same wh)"
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=30, qty_after_transaction=30,
				warehouse="WH 1",
				posting_date="2021-12-01", voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20, qty_after_transaction=50,
				warehouse="WH 1",
				posting_date="2021-12-02", voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10), qty_after_transaction=40,
				warehouse="WH 1",
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			)
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
				actual_qty=(-30), qty_after_transaction=(-30),
				warehouse="WH 1",
				posting_date="2021-12-01", voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20, qty_after_transaction=(-10),
				warehouse="WH 1",
				posting_date="2021-12-02", voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20, qty_after_transaction=10,
				warehouse="WH 1",
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=10, qty_after_transaction=20,
				warehouse="WH 1",
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="004",
				has_serial_no=False, serial_no=None
			)
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
				actual_qty=30, qty_after_transaction=30,
				warehouse="WH 1",
				posting_date="2021-12-01", voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=0, qty_after_transaction=50,
				warehouse="WH 1",
				posting_date="2021-12-02", voucher_type="Stock Reconciliation",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10), qty_after_transaction=40,
				warehouse="WH 1",
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			)
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
				actual_qty=0, qty_after_transaction=1000,
				warehouse="WH 1",
				posting_date="2021-12-01", voucher_type="Stock Reconciliation",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=0, qty_after_transaction=400,
				warehouse="WH 1",
				posting_date="2021-12-02", voucher_type="Stock Reconciliation",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10), qty_after_transaction=390,
				warehouse="WH 1",
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			)
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
				actual_qty=0, qty_after_transaction=1000,
				warehouse="WH 1",
				posting_date="2021-12-01", voucher_type="Stock Reconciliation",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=0, qty_after_transaction=400,
				warehouse="WH 2",
				posting_date="2021-12-02", voucher_type="Stock Reconciliation",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10), qty_after_transaction=990,
				warehouse="WH 1",
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="004",
				has_serial_no=False, serial_no=None
			)
		]

		item_wise_slots, item_wh_wise_slots = generate_item_and_item_wh_wise_slots(
			filters=self.filters,sle=sle
		)

		# test without 'show_warehouse_wise_stock'
		item_result = item_wise_slots["Flask Item"]
		queue = item_result["fifo_queue"]

		self.assertEqual(item_result["qty_after_transaction"], item_result["total_qty"])
		self.assertEqual(item_result["total_qty"], 1390.0)
		self.assertEqual(queue[0][0], 990.0)
		self.assertEqual(queue[1][0], 400.0)

		# test with 'show_warehouse_wise_stock' checked
		item_wh_balances = [item_wh_wise_slots.get(i).get("qty_after_transaction") for i in item_wh_wise_slots]
		self.assertEqual(sum(item_wh_balances), item_result["qty_after_transaction"])

def generate_item_and_item_wh_wise_slots(filters, sle):
	"Return results with and without 'show_warehouse_wise_stock'"
	item_wise_slots = FIFOSlots(filters, sle).generate()

	filters.show_warehouse_wise_stock = True
	item_wh_wise_slots = FIFOSlots(filters, sle).generate()
	filters.show_warehouse_wise_stock = False

	return item_wise_slots, item_wh_wise_slots