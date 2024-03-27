import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from hypothesis import given
from hypothesis import strategies as st

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.valuation import FIFOValuation, LIFOValuation, round_off_if_near_zero

qty_gen = st.floats(min_value=-1e6, max_value=1e6)
value_gen = st.floats(min_value=1, max_value=1e6)
stock_queue_generator = st.lists(st.tuples(qty_gen, value_gen), min_size=10)


class TestFIFOValuation(unittest.TestCase):
	def setUp(self):
		self.queue = FIFOValuation([])

	def tearDown(self):
		qty, value = self.queue.get_total_stock_and_value()
		self.assertTotalQty(qty)
		self.assertTotalValue(value)

	def assertTotalQty(self, qty):
		self.assertAlmostEqual(sum(q for q, _ in self.queue), qty, msg=f"queue: {self.queue}", places=4)

	def assertTotalValue(self, value):
		self.assertAlmostEqual(sum(q * r for q, r in self.queue), value, msg=f"queue: {self.queue}", places=2)

	def test_simple_addition(self):
		self.queue.add_stock(1, 10)
		self.assertTotalQty(1)

	def test_simple_removal(self):
		self.queue.add_stock(1, 10)
		self.queue.remove_stock(1)
		self.assertTotalQty(0)

	def test_merge_new_stock(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(1, 10)
		self.assertEqual(self.queue, [[2, 10]])

	def test_adding_negative_stock_keeps_rate(self):
		self.queue = FIFOValuation([[-5.0, 100]])
		self.queue.add_stock(1, 10)
		self.assertEqual(self.queue, [[-4, 100]])

	def test_adding_negative_stock_updates_rate(self):
		self.queue = FIFOValuation([[-5.0, 100]])
		self.queue.add_stock(6, 10)
		self.assertEqual(self.queue, [[1, 10]])

	def test_negative_stock(self):
		self.queue.remove_stock(1, 5)
		self.assertEqual(self.queue, [[-1, 5]])

		self.queue.remove_stock(1)
		self.assertTotalQty(-2)
		self.assertEqual(self.queue, [[-2, 5]])

		self.queue.add_stock(2, 10)
		self.assertTotalQty(0)
		self.assertTotalValue(0)

	def test_removing_specified_rate(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(1, 20)

		self.queue.remove_stock(1, 20)
		self.assertEqual(self.queue, [[1, 10]])

	def test_remove_multiple_bins(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(2, 20)
		self.queue.add_stock(1, 20)
		self.queue.add_stock(5, 20)

		self.queue.remove_stock(4)
		self.assertEqual(self.queue, [[5, 20]])

	def test_remove_multiple_bins_with_rate(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(2, 20)
		self.queue.add_stock(1, 20)
		self.queue.add_stock(5, 20)

		self.queue.remove_stock(3, 20)
		self.assertEqual(self.queue, [[1, 10], [5, 20]])

	def test_queue_with_unknown_rate(self):
		self.queue.add_stock(1, 1)
		self.queue.add_stock(1, 2)
		self.queue.add_stock(1, 3)
		self.queue.add_stock(1, 4)

		self.assertTotalValue(10)

		self.queue.remove_stock(3, 1)
		self.assertEqual(self.queue, [[1, 4]])

	def test_rounding_off(self):
		self.queue.add_stock(1.0, 1.0)
		self.queue.remove_stock(1.0 - 1e-9)
		self.assertTotalQty(0)

	def test_rounding_off_near_zero(self):
		self.assertEqual(round_off_if_near_zero(0), 0)
		self.assertEqual(round_off_if_near_zero(1), 1)
		self.assertEqual(round_off_if_near_zero(-1), -1)
		self.assertEqual(round_off_if_near_zero(-1e-8), 0)
		self.assertEqual(round_off_if_near_zero(1e-8), 0)

	def test_totals(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(2, 13)
		self.queue.add_stock(1, 17)
		self.queue.remove_stock(1)
		self.queue.remove_stock(1)
		self.queue.remove_stock(1)
		self.queue.add_stock(5, 17)
		self.queue.add_stock(8, 11)

	@given(stock_queue_generator)
	def test_fifo_qty_hypothesis(self, stock_queue):
		self.queue = FIFOValuation([])
		total_qty = 0

		for qty, rate in stock_queue:
			if round_off_if_near_zero(qty) == 0:
				continue
			if qty > 0:
				self.queue.add_stock(qty, rate)
				total_qty += qty
			else:
				qty = abs(qty)
				consumed = self.queue.remove_stock(qty)
				self.assertAlmostEqual(
					qty, sum(q for q, _ in consumed), msg=f"incorrect consumption {consumed}"
				)
				total_qty -= qty
			self.assertTotalQty(total_qty)

	@given(stock_queue_generator)
	def test_fifo_qty_value_nonneg_hypothesis(self, stock_queue):
		self.queue = FIFOValuation([])
		total_qty = 0.0
		total_value = 0.0

		for qty, rate in stock_queue:
			# don't allow negative stock
			if round_off_if_near_zero(qty) == 0 or total_qty + qty < 0 or abs(qty) < 0.1:
				continue
			if qty > 0:
				self.queue.add_stock(qty, rate)
				total_qty += qty
				total_value += qty * rate
			else:
				qty = abs(qty)
				consumed = self.queue.remove_stock(qty)
				self.assertAlmostEqual(
					qty, sum(q for q, _ in consumed), msg=f"incorrect consumption {consumed}"
				)
				total_qty -= qty
				total_value -= sum(q * r for q, r in consumed)
			self.assertTotalQty(total_qty)
			self.assertTotalValue(total_value)

	@given(stock_queue_generator, st.floats(min_value=0.1, max_value=1e6))
	def test_fifo_qty_value_nonneg_hypothesis_with_outgoing_rate(self, stock_queue, outgoing_rate):
		self.queue = FIFOValuation([])
		total_qty = 0.0
		total_value = 0.0

		for qty, rate in stock_queue:
			# don't allow negative stock
			if round_off_if_near_zero(qty) == 0 or total_qty + qty < 0 or abs(qty) < 0.1:
				continue
			if qty > 0:
				self.queue.add_stock(qty, rate)
				total_qty += qty
				total_value += qty * rate
			else:
				qty = abs(qty)
				consumed = self.queue.remove_stock(qty, outgoing_rate)
				self.assertAlmostEqual(
					qty, sum(q for q, _ in consumed), msg=f"incorrect consumption {consumed}"
				)
				total_qty -= qty
				total_value -= sum(q * r for q, r in consumed)
			self.assertTotalQty(total_qty)
			self.assertTotalValue(total_value)


class TestLIFOValuation(unittest.TestCase):
	def setUp(self):
		self.stack = LIFOValuation([])

	def tearDown(self):
		qty, value = self.stack.get_total_stock_and_value()
		self.assertTotalQty(qty)
		self.assertTotalValue(value)

	def assertTotalQty(self, qty):
		self.assertAlmostEqual(sum(q for q, _ in self.stack), qty, msg=f"stack: {self.stack}", places=4)

	def assertTotalValue(self, value):
		self.assertAlmostEqual(sum(q * r for q, r in self.stack), value, msg=f"stack: {self.stack}", places=2)

	def test_simple_addition(self):
		self.stack.add_stock(1, 10)
		self.assertTotalQty(1)

	def test_merge_new_stock(self):
		self.stack.add_stock(1, 10)
		self.stack.add_stock(1, 10)
		self.assertEqual(self.stack, [[2, 10]])

	def test_simple_removal(self):
		self.stack.add_stock(1, 10)
		self.stack.remove_stock(1)
		self.assertTotalQty(0)

	def test_adding_negative_stock_keeps_rate(self):
		self.stack = LIFOValuation([[-5.0, 100]])
		self.stack.add_stock(1, 10)
		self.assertEqual(self.stack, [[-4, 100]])

	def test_adding_negative_stock_updates_rate(self):
		self.stack = LIFOValuation([[-5.0, 100]])
		self.stack.add_stock(6, 10)
		self.assertEqual(self.stack, [[1, 10]])

	def test_rounding_off(self):
		self.stack.add_stock(1.0, 1.0)
		self.stack.remove_stock(1.0 - 1e-9)
		self.assertTotalQty(0)

	def test_lifo_consumption(self):
		self.stack.add_stock(10, 10)
		self.stack.add_stock(10, 20)
		consumed = self.stack.remove_stock(15)
		self.assertEqual(consumed, [[10, 20], [5, 10]])
		self.assertTotalQty(5)

	def test_lifo_consumption_going_negative(self):
		self.stack.add_stock(10, 10)
		self.stack.add_stock(10, 20)
		consumed = self.stack.remove_stock(25)
		self.assertEqual(consumed, [[10, 20], [10, 10], [5, 10]])
		self.assertTotalQty(-5)

	def test_lifo_consumption_multiple(self):
		self.stack.add_stock(1, 1)
		self.stack.add_stock(2, 2)
		consumed = self.stack.remove_stock(1)
		self.assertEqual(consumed, [[1, 2]])

		self.stack.add_stock(3, 3)
		consumed = self.stack.remove_stock(4)
		self.assertEqual(consumed, [[3, 3], [1, 2]])

		self.stack.add_stock(4, 4)
		consumed = self.stack.remove_stock(5)
		self.assertEqual(consumed, [[4, 4], [1, 1]])

		self.stack.add_stock(5, 5)
		consumed = self.stack.remove_stock(5)
		self.assertEqual(consumed, [[5, 5]])

	@given(stock_queue_generator)
	def test_lifo_qty_hypothesis(self, stock_stack):
		self.stack = LIFOValuation([])
		total_qty = 0

		for qty, rate in stock_stack:
			if round_off_if_near_zero(qty) == 0:
				continue
			if qty > 0:
				self.stack.add_stock(qty, rate)
				total_qty += qty
			else:
				qty = abs(qty)
				consumed = self.stack.remove_stock(qty)
				self.assertAlmostEqual(
					qty, sum(q for q, _ in consumed), msg=f"incorrect consumption {consumed}"
				)
				total_qty -= qty
			self.assertTotalQty(total_qty)

	@given(stock_queue_generator)
	def test_lifo_qty_value_nonneg_hypothesis(self, stock_stack):
		self.stack = LIFOValuation([])
		total_qty = 0.0
		total_value = 0.0

		for qty, rate in stock_stack:
			# don't allow negative stock
			if round_off_if_near_zero(qty) == 0 or total_qty + qty < 0 or abs(qty) < 0.1:
				continue
			if qty > 0:
				self.stack.add_stock(qty, rate)
				total_qty += qty
				total_value += qty * rate
			else:
				qty = abs(qty)
				consumed = self.stack.remove_stock(qty)
				self.assertAlmostEqual(
					qty, sum(q for q, _ in consumed), msg=f"incorrect consumption {consumed}"
				)
				total_qty -= qty
				total_value -= sum(q * r for q, r in consumed)
			self.assertTotalQty(total_qty)
			self.assertTotalValue(total_value)


class TestLIFOValuationSLE(FrappeTestCase):
	ITEM_CODE = "_Test LIFO item"
	WAREHOUSE = "_Test Warehouse - _TC"

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		make_item(cls.ITEM_CODE, {"valuation_method": "LIFO"})

	def _make_stock_entry(self, qty, rate=None):
		kwargs = {
			"item_code": self.ITEM_CODE,
			"from_warehouse" if qty < 0 else "to_warehouse": self.WAREHOUSE,
			"rate": rate,
			"qty": abs(qty),
		}
		return make_stock_entry(**kwargs)

	def assertStockQueue(self, se, expected_queue):
		sle_name = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": se.name, "is_cancelled": 0, "voucher_type": "Stock Entry"}
		)
		sle = frappe.get_doc("Stock Ledger Entry", sle_name)

		stock_queue = json.loads(sle.stock_queue)

		total_qty, total_value = LIFOValuation(stock_queue).get_total_stock_and_value()
		self.assertEqual(sle.qty_after_transaction, total_qty)
		self.assertEqual(sle.stock_value, total_value)

		if total_qty > 0:
			self.assertEqual(stock_queue, expected_queue)

	def test_lifo_values(self):
		in1 = self._make_stock_entry(1, 1)
		self.assertStockQueue(in1, [[1, 1]])

		in2 = self._make_stock_entry(2, 2)
		self.assertStockQueue(in2, [[1, 1], [2, 2]])

		out1 = self._make_stock_entry(-1)
		self.assertStockQueue(out1, [[1, 1], [1, 2]])

		in3 = self._make_stock_entry(3, 3)
		self.assertStockQueue(in3, [[1, 1], [1, 2], [3, 3]])

		out2 = self._make_stock_entry(-4)
		self.assertStockQueue(out2, [[1, 1]])

		in4 = self._make_stock_entry(4, 4)
		self.assertStockQueue(in4, [[1, 1], [4, 4]])

		out3 = self._make_stock_entry(-5)
		self.assertStockQueue(out3, [])

		in5 = self._make_stock_entry(5, 5)
		self.assertStockQueue(in5, [[5, 5]])

		out5 = self._make_stock_entry(-5)
		self.assertStockQueue(out5, [])
