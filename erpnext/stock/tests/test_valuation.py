import unittest

from erpnext.stock.valuation import FifoValuation, _round_off_if_near_zero


def rate_generator():
	return 0.0

class TestFifoValuation(unittest.TestCase):

	def setUp(self):
		self.queue = FifoValuation([])

	def tearDown(self):
		qty, value = self.queue.get_total_stock_and_value()
		self.assertTotalQty(qty)
		self.assertTotalValue(value)

	def assertTotalQty(self, qty):
		self.assertEqual(sum(q for q, _ in self.queue), qty, msg=f"queue: {self.queue}")

	def assertTotalValue(self, value):
		self.assertEqual(sum(q * r for q, r in self.queue), value, msg=f"queue: {self.queue}")

	def test_simple_addition(self):
		self.queue.add_stock(1, 10)
		self.assertTotalQty(1)

	def test_simple_removal(self):
		self.queue.add_stock(1, 10)
		self.queue.remove_stock(1, 0, rate_generator)
		self.assertTotalQty(0)

	def test_merge_new_stock(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(1, 10)
		self.assertEqual(self.queue, [[2, 10]])

	def test_adding_negative_stock_keeps_rate(self):
		self.queue = FifoValuation([[-5.0, 100]])
		self.queue.add_stock(1, 10)
		self.assertEqual(self.queue, [[-4, 100]])

	def test_adding_negative_stock_updates_rate(self):
		self.queue = FifoValuation([[-5.0, 100]])
		self.queue.add_stock(6, 10)
		self.assertEqual(self.queue, [[1, 10]])


	def test_negative_stock(self):
		self.queue.remove_stock(1, 5, rate_generator)
		self.assertEqual(self.queue, [[-1, 5]])

		# XXX
		self.queue.remove_stock(1, 10, rate_generator)
		self.assertTotalQty(-2)

		self.queue.add_stock(2, 10)
		self.assertTotalQty(0)
		self.assertTotalValue(0)

	def test_removing_specified_rate(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(1, 20)

		self.queue.remove_stock(1, 20, rate_generator)
		self.assertEqual(self.queue, [[1, 10]])


	def test_remove_multiple_bins(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(2, 20)
		self.queue.add_stock(1, 20)
		self.queue.add_stock(5, 20)

		self.queue.remove_stock(4, 0, rate_generator)
		self.assertEqual(self.queue, [[5, 20]])


	def test_remove_multiple_bins_with_rate(self):
		self.queue.add_stock(1, 10)
		self.queue.add_stock(2, 20)
		self.queue.add_stock(1, 20)
		self.queue.add_stock(5, 20)

		self.queue.remove_stock(3, 20, rate_generator)
		self.assertEqual(self.queue, [[1, 10], [5, 20]])

	def test_collapsing_of_queue(self):
		self.queue.add_stock(1, 1)
		self.queue.add_stock(1, 2)
		self.queue.add_stock(1, 3)
		self.queue.add_stock(1, 4)

		self.assertTotalValue(10)

		self.queue.remove_stock(3, 1, rate_generator)
		# XXX
		self.assertEqual(self.queue, [[1, 7]])

	def test_rounding_off(self):
		self.queue.add_stock(1.0, 1.0)
		self.queue.remove_stock(1.0 - 1e-9, 0.0, rate_generator)
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
		self.queue.remove_stock(1, 0, rate_generator)
		self.queue.remove_stock(1, 0, rate_generator)
		self.queue.remove_stock(1, 0, rate_generator)
		self.queue.add_stock(5, 17)
		self.queue.add_stock(8, 11)
