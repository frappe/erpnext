import unittest

from hypothesis import given
from hypothesis import strategies as st

from erpnext.stock.valuation import FIFOValuation, _round_off_if_near_zero

qty_gen = st.floats(min_value=-1e6, max_value=1e6)
value_gen = st.floats(min_value=1, max_value=1e6)
stock_queue_generator = st.lists(st.tuples(qty_gen, value_gen), min_size=10)


class TestFifoValuation(unittest.TestCase):

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

		# XXX
		self.queue.remove_stock(1, 10)
		self.assertTotalQty(-2)

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

	def test_collapsing_of_queue(self):
		self.queue.add_stock(1, 1)
		self.queue.add_stock(1, 2)
		self.queue.add_stock(1, 3)
		self.queue.add_stock(1, 4)

		self.assertTotalValue(10)

		self.queue.remove_stock(3, 1)
		# XXX
		self.assertEqual(self.queue, [[1, 7]])

	def test_rounding_off(self):
		self.queue.add_stock(1.0, 1.0)
		self.queue.remove_stock(1.0 - 1e-9)
		self.assertTotalQty(0)

	def test_rounding_off_near_zero(self):
		self.assertEqual(_round_off_if_near_zero(0), 0)
		self.assertEqual(_round_off_if_near_zero(1), 1)
		self.assertEqual(_round_off_if_near_zero(-1), -1)
		self.assertEqual(_round_off_if_near_zero(-1e-8), 0)
		self.assertEqual(_round_off_if_near_zero(1e-8), 0)

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
			if qty == 0:
				continue
			if qty > 0:
				self.queue.add_stock(qty, rate)
				total_qty += qty
			else:
				qty = abs(qty)
				consumed = self.queue.remove_stock(qty)
				self.assertAlmostEqual(qty, sum(q for q, _ in consumed), msg=f"incorrect consumption {consumed}")
				total_qty -= qty
			self.assertTotalQty(total_qty)

	@given(stock_queue_generator)
	def test_fifo_qty_value_nonneg_hypothesis(self, stock_queue):
		self.queue = FIFOValuation([])
		total_qty = 0.0
		total_value = 0.0

		for qty, rate in stock_queue:
			# don't allow negative stock
			if qty == 0 or total_qty + qty < 0 or abs(qty) < 0.1:
				continue
			if qty > 0:
				self.queue.add_stock(qty, rate)
				total_qty += qty
				total_value += qty * rate
			else:
				qty = abs(qty)
				consumed = self.queue.remove_stock(qty)
				self.assertAlmostEqual(qty, sum(q for q, _ in consumed), msg=f"incorrect consumption {consumed}")
				total_qty -= qty
				total_value -= sum(q * r for q, r in consumed)
			self.assertTotalQty(total_qty)
			self.assertTotalValue(total_value)
