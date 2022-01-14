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
		"Reference: Case 1 in stock_ageing_fifo_logic.md"
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=30, qty_after_transaction=30,
				posting_date="2021-12-01", voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20, qty_after_transaction=50,
				posting_date="2021-12-02", voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10), qty_after_transaction=40,
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
		"Reference: Case 3 in stock_ageing_fifo_logic.md"
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=(-30), qty_after_transaction=(-30),
				posting_date="2021-12-01", voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20, qty_after_transaction=(-10),
				posting_date="2021-12-02", voucher_type="Stock Entry",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=20, qty_after_transaction=10,
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=10, qty_after_transaction=20,
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

	def test_stock_reconciliation(self):
		sle = [
			frappe._dict(
				name="Flask Item",
				actual_qty=30, qty_after_transaction=30,
				posting_date="2021-12-01", voucher_type="Stock Entry",
				voucher_no="001",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=0, qty_after_transaction=50,
				posting_date="2021-12-02", voucher_type="Stock Reconciliation",
				voucher_no="002",
				has_serial_no=False, serial_no=None
			),
			frappe._dict(
				name="Flask Item",
				actual_qty=(-10), qty_after_transaction=40,
				posting_date="2021-12-03", voucher_type="Stock Entry",
				voucher_no="003",
				has_serial_no=False, serial_no=None
			)
		]

		slots = FIFOSlots(self.filters, sle).generate()

		result = slots["Flask Item"]
		queue = result["fifo_queue"]

		self.assertEqual(result["qty_after_transaction"], result["total_qty"])
		self.assertEqual(queue[0][0], 20.0)
		self.assertEqual(queue[1][0], 20.0)
