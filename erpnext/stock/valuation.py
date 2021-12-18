from typing import Callable, List, NewType, Optional, Tuple

from frappe.utils import flt

FifoBin = NewType("FifoBin", List[float])

# Indexes of values inside FIFO bin 2-tuple
QTY = 0
RATE = 1


class FifoValuation:
	"""Valuation method where a queue of all the incoming stock is maintained.

	New stock is added at end of the queue.
	Qty consumption happens on First In First Out basis.

	Queue is implemented using "bins" of [qty, rate].

	ref: https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting
	"""

	def __init__(self, state: Optional[List[FifoBin]]):
		self.queue: List[FifoBin] = state if state is not None else []

	def get_state(self) -> List[FifoBin]:
		"""Get current state of queue."""
		return self.queue

	def get_total_stock_and_value(self) -> Tuple[float, float]:
		total_qty = 0.0
		total_value = 0.0

		for qty, rate in self.queue:
			total_qty += flt(qty)
			total_value += flt(qty) * flt(rate)

		return _round_off_if_near_zero(total_qty), _round_off_if_near_zero(total_value)

	def add_stock(self, qty: float, rate: float) -> List[FifoBin]:
		"""Update fifo queue with new stock and return queue.

			args:
				qty: new quantity to add
				rate: incoming rate of new quantity"""

		if not len(self.queue):
			self.queue.append([0, 0])

		# last row has the same rate, merge new bin.
		if self.queue[-1][RATE] == rate:
			self.queue[-1][QTY] += qty
		else:
			# Item has a positive balance qty, add new entry
			if self.queue[-1][QTY] > 0:
				self.queue.append([qty, rate])
			else:  # negative balance qty
				qty = self.queue[-1][QTY] + qty
				if qty > 0:  # new balance qty is positive
					self.queue[-1] = [qty, rate]
				else:  # new balance qty is still negative, maintain same rate
					self.queue[-1][QTY] = qty
		return self.get_state()

	def remove_stock(
		self, qty: float, rate: float, rate_generator: Callable[[], float]
	) -> List[FifoBin]:
		"""Remove stock from the queue and return queue.

		args:
			qty: quantity to remove
			rate: outgoing rate
			rate_generator: function to be called if queue is not found and rate is required.
		"""

		while qty:
			if not len(self.queue):
				# rely on rate generator.
				self.queue.append([0, rate_generator()])

			index = None
			if rate > 0:
				# Find the entry where rate matched with outgoing rate
				for idx, fifo_bin in enumerate(self.queue):
					if fifo_bin[RATE] == rate:
						index = idx
						break

				# If no entry found with outgoing rate, collapse stack
				if index is None:  # nosemgrep
					new_stock_value = sum(d[QTY] * d[RATE] for d in self.queue) - qty * rate
					new_stock_qty = sum(d[QTY] for d in self.queue) - qty
					self.queue = [[new_stock_qty, new_stock_value / new_stock_qty if new_stock_qty > 0 else rate]]
					break
			else:
				index = 0

			# select first bin or the bin with same rate
			fifo_bin = self.queue[index]
			if qty >= fifo_bin[QTY]:
				# consume current bin
				qty = _round_off_if_near_zero(qty - fifo_bin[QTY])
				self.queue.pop(index)
				if not self.queue and qty:
					# stock finished, qty still remains to be withdrawn
					# negative stock, keep in as a negative bin
					self.queue.append([-qty, rate or fifo_bin[RATE]])
					break

			else:
				# qty found in current bin consume it and exit
				fifo_bin[QTY] = fifo_bin[QTY] - qty
				qty = 0

		return self.get_state()


def _round_off_if_near_zero(number: float, precision: int = 6) -> float:
	"""Rounds off the number to zero only if number is close to zero for decimal
	specified in precision. Precision defaults to 6.
	"""
	if flt(number) < (1.0 / (10 ** precision)):
		return 0

	return flt(number)
