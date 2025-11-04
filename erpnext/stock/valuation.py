from abc import ABC, abstractmethod, abstractproperty
from collections.abc import Callable
from typing import NewType

from frappe.utils import flt

StockBin = NewType("StockBin", list[float])  # [[qty, rate], ...]

# Indexes of values inside FIFO bin 2-tuple
QTY = 0
RATE = 1


class BinWiseValuation(ABC):
	@abstractmethod
	def add_stock(self, qty: float, rate: float) -> None:
		pass

	@abstractmethod
	def remove_stock(
		self,
		qty: float,
		outgoing_rate: float = 0.0,
		rate_generator: Callable[[], float] | None = None,
		is_return_purchase_entry: bool = False,
	) -> list[StockBin]:
		pass

	@abstractproperty
	def state(self) -> list[StockBin]:
		pass

	def get_total_stock_and_value(self) -> tuple[float, float]:
		total_qty = 0.0
		total_value = 0.0

		for qty, rate in self.state:
			total_qty += flt(qty)
			total_value += flt(qty) * flt(rate)

		return round_off_if_near_zero(total_qty), round_off_if_near_zero(total_value)

	def __repr__(self):
		return str(self.state)

	def __iter__(self):
		return iter(self.state)

	def __eq__(self, other):
		if isinstance(other, list):
			return self.state == other
		return type(self) == type(other) and self.state == other.state


class FIFOValuation(BinWiseValuation):
	"""Valuation method where a queue of all the incoming stock is maintained.

	New stock is added at end of the queue.
	Qty consumption happens on First In First Out basis.

	Queue is implemented using "bins" of [qty, rate].

	ref: https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting
	"""

	# specifying the attributes to save resources
	# ref: https://docs.python.org/3/reference/datamodel.html#slots
	__slots__ = ["queue"]

	def __init__(self, state: list[StockBin] | None):
		self.queue: list[StockBin] = state if state is not None else []

	@property
	def state(self) -> list[StockBin]:
		"""Get current state of queue."""
		return self.queue

	def add_stock(self, qty: float, rate: float) -> None:
		"""Update fifo queue with new stock.

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

	def remove_stock(
		self,
		qty: float,
		outgoing_rate: float = 0.0,
		rate_generator: Callable[[], float] | None = None,
		is_return_purchase_entry: bool = False,
	) -> list[StockBin]:
		"""Remove stock from the queue and return popped bins.

		args:
		        qty: quantity to remove
		        rate: outgoing rate
		        rate_generator: function to be called if queue is not found and rate is required.
		"""
		if not rate_generator:
			rate_generator = lambda: 0.0  # noqa

		consumed_bins = []
		while qty:
			if not len(self.queue):
				# rely on rate generator.
				self.queue.append([0, rate_generator()])

			index = None
			if outgoing_rate > 0 or is_return_purchase_entry:
				# Find the entry where rate matched with outgoing rate
				for idx, fifo_bin in enumerate(self.queue):
					if fifo_bin[RATE] == outgoing_rate:
						index = idx
						break

				# If no entry found with outgoing rate, consume as per FIFO
				if index is None:  # nosemgrep
					index = 0
			else:
				index = 0

			# select first bin or the bin with same rate
			fifo_bin = self.queue[index]
			if qty >= fifo_bin[QTY]:
				# consume current bin
				qty = round_off_if_near_zero(qty - fifo_bin[QTY])
				to_consume = self.queue.pop(index)
				consumed_bins.append(list(to_consume))

				if not self.queue and qty:
					# stock finished, qty still remains to be withdrawn
					# negative stock, keep in as a negative bin
					self.queue.append([-qty, outgoing_rate or fifo_bin[RATE]])
					consumed_bins.append([qty, outgoing_rate or fifo_bin[RATE]])
					break
			else:
				# qty found in current bin consume it and exit
				fifo_bin[QTY] = round_off_if_near_zero(fifo_bin[QTY] - qty)
				consumed_bins.append([qty, fifo_bin[RATE]])
				qty = 0

		return consumed_bins


class LIFOValuation(BinWiseValuation):
	"""Valuation method where a *stack* of all the incoming stock is maintained.

	New stock is added at top of the stack.
	Qty consumption happens on Last In First Out basis.

	Stack is implemented using "bins" of [qty, rate].

	ref: https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting
	Implementation detail: appends and pops both at end of list.
	"""

	# specifying the attributes to save resources
	# ref: https://docs.python.org/3/reference/datamodel.html#slots
	__slots__ = ["stack"]

	def __init__(self, state: list[StockBin] | None):
		self.stack: list[StockBin] = state if state is not None else []

	@property
	def state(self) -> list[StockBin]:
		"""Get current state of stack."""
		return self.stack

	def add_stock(self, qty: float, rate: float) -> None:
		"""Update lifo stack with new stock.

		args:
		        qty: new quantity to add
		        rate: incoming rate of new quantity.

		Behaviour of this is same as FIFO valuation.
		"""
		if not len(self.stack):
			self.stack.append([0, 0])

		# last row has the same rate, merge new bin.
		if self.stack[-1][RATE] == rate:
			self.stack[-1][QTY] += qty
		else:
			# Item has a positive balance qty, add new entry
			if self.stack[-1][QTY] > 0:
				self.stack.append([qty, rate])
			else:  # negative balance qty
				qty = self.stack[-1][QTY] + qty
				if qty > 0:  # new balance qty is positive
					self.stack[-1] = [qty, rate]
				else:  # new balance qty is still negative, maintain same rate
					self.stack[-1][QTY] = qty

	def remove_stock(
		self,
		qty: float,
		outgoing_rate: float = 0.0,
		rate_generator: Callable[[], float] | None = None,
		is_return_purchase_entry: bool = False,
	) -> list[StockBin]:
		"""Remove stock from the stack and return popped bins.

		args:
		        qty: quantity to remove
		        rate: outgoing rate - ignored. Kept for backwards compatibility.
		        rate_generator: function to be called if stack is not found and rate is required.
		"""
		if not rate_generator:
			rate_generator = lambda: 0.0  # noqa

		consumed_bins = []
		while qty:
			if not len(self.stack):
				# rely on rate generator.
				self.stack.append([0, rate_generator()])

			# start at the end.
			index = -1

			stock_bin = self.stack[index]
			if qty >= stock_bin[QTY]:
				# consume current bin
				qty = round_off_if_near_zero(qty - stock_bin[QTY])
				to_consume = self.stack.pop(index)
				consumed_bins.append(list(to_consume))

				if not self.stack and qty:
					# stock finished, qty still remains to be withdrawn
					# negative stock, keep in as a negative bin
					self.stack.append([-qty, outgoing_rate or stock_bin[RATE]])
					consumed_bins.append([qty, outgoing_rate or stock_bin[RATE]])
					break
			else:
				# qty found in current bin consume it and exit
				stock_bin[QTY] = round_off_if_near_zero(stock_bin[QTY] - qty)
				consumed_bins.append([qty, stock_bin[RATE]])
				qty = 0

		return consumed_bins


def round_off_if_near_zero(number: float, precision: int = 7) -> float:
	"""Rounds off the number to zero only if number is close to zero for decimal
	specified in precision. Precision defaults to 7.
	"""
	if abs(0.0 - flt(number)) < (1.0 / (10**precision)):
		return 0.0

	return flt(number)
