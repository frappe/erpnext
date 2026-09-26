# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""What every Stock Ledger Entry of an item in a warehouse should be worth.

The ledger of one item in one warehouse is replayed from its first entry with a
small, self-contained set of valuation rules, and each entry gets the stock value
difference, valuation rate and stock value it should carry. None of the code in
stock_ledger.py or in the Serial and Batch Bundle valuation is used, so where the
two disagree, either one of them has a bug or the ledger was never reposted.

How stock is held
-----------------
The stock of an item in a warehouse lives in up to three places:

* the pool: stock that is not valued lot by lot, i.e. plain stock and batches
  without "Use Batch-wise Valuation". It follows the item's valuation method:
  a moving average, or a FIFO / LIFO queue of [qty, rate] layers.
* batch lots: one per batch with "Use Batch-wise Valuation". Each keeps its own
  qty and value, and stock leaves a batch at the batch's own average rate.
* serial lots: every serial no on hand, which leaves at the rate it was received
  at in this warehouse. A serial no inside a batch is still valued as a serial.

How an entry is valued
----------------------
* Inward stock brings its rate with it, so incoming rates are taken as given.
* Outward stock is valued from what is on hand: the pool at its average or its
  oldest (FIFO) / newest (LIFO) layers, a batch at its average, a serial at its
  receipt rate.
* A FIFO purchase return first takes the layer carrying the rate of the receipt
  it returns. A moving average return leaves at the current average, and a LIFO
  return from the top of the stack, as the stock ledger does.
* A Stock Reconciliation without serial / batch nos sets the qty and the rate.
  With them, it is an issue of the counted-out lots and a receipt of the counted-in ones.
* Once the warehouse holds no stock, whatever value is left over is written off.
  A lot that runs out takes its leftover value with it.
* Stock going out with nothing on hand to price it uses the warehouse's average
  or last rate. If the warehouse never had a rate, the ledger's own rate is taken,
  as there is nothing to check it against.
* Like the ledger, the stock value is rounded to the currency precision after
  every entry, and a reconciled rate is rounded before it is applied.
* Standard Cost items are carried at the standard rate on the posting date.

Known limits: the incoming rate of a transfer, repack or manufacture is not
checked against its source here; replay always starts at the first entry.
"""

from dataclasses import dataclass, field

import frappe
from frappe.utils import cint, create_batch, flt

from erpnext.controllers.sales_and_purchase_return import get_return_against_item_fields
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.utils import get_valuation_method

# Why an entry got the value it did; shown next to the expected values.
BASIS_INCOMING_RATE = "Incoming rate"
BASIS_MOVING_AVERAGE = "Moving average"
BASIS_FIFO = "FIFO queue"
BASIS_LIFO = "LIFO stack"
BASIS_PURCHASE_RETURN = "Rate of the returned receipt"
BASIS_BATCH_AVERAGE = "Batch average"
BASIS_SERIAL_RATE = "Serial no receipt rate"
BASIS_RECONCILED = "Reconciled qty and rate"
BASIS_WRITE_OFF = "Write-off of leftover value"
BASIS_STANDARD_COST = "Standard cost"
BASIS_NO_STOCK = "No stock on hand (fallback rate)"

RETURNABLE_PURCHASE_DOCTYPES = ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt")

LEDGER_FIELDS = (
	"name",
	"posting_date",
	"posting_time",
	"posting_datetime",
	"creation",
	"company",
	"item_code",
	"warehouse",
	"voucher_type",
	"voucher_no",
	"voucher_detail_no",
	"actual_qty",
	"incoming_rate",
	"outgoing_rate",
	"qty_after_transaction",
	"valuation_rate",
	"stock_value",
	"stock_value_difference",
	"serial_no",
	"batch_no",
	"serial_and_batch_bundle",
	"is_adjustment_entry",
)


@dataclass
class ExpectedValues:
	"""What one Stock Ledger Entry should carry, and why."""

	qty_after_transaction: float
	stock_value_difference: float
	stock_value: float
	valuation_rate: float
	basis: str


@dataclass
class LotMovement:
	"""A part of an entry's qty, moved in or out of the pool, a batch, or as a serial."""

	qty: float
	rate: float = 0.0
	batch_no: str | None = None
	serial_no: str | None = None


class MovingAveragePool:
	"""Untracked stock valued at one running average rate."""

	def __init__(self):
		self.qty = 0.0
		self.rate = 0.0

	@property
	def value(self) -> float:
		return self.qty * self.rate

	def receive(self, qty: float, rate: float) -> None:
		new_qty = self.qty + qty

		if self.qty <= 0 and new_qty >= 0:
			# stock was nil or short: the receipt sets the rate afresh
			self.rate = rate
		elif new_qty > 0:
			self.rate = (self.value + qty * rate) / new_qty
		elif not self.rate:
			# still short after the receipt: keep the rate unless there is none yet
			self.rate = rate

		self.qty = new_qty

	def issue(self, qty: float, preferred_rate: float | None = None) -> float:
		"""Take qty out at the average rate and return the value taken out."""
		self.qty -= qty
		return qty * self.rate

	def set_balance(self, qty: float, rate: float) -> None:
		self.qty = qty
		self.rate = rate

	def clear(self) -> None:
		self.qty = 0.0

	@property
	def last_rate(self) -> float:
		return self.rate


class QueuePool:
	"""Untracked stock kept as [qty, rate] layers, consumed FIFO or LIFO."""

	def __init__(self, last_in_first_out: bool = False):
		self.last_in_first_out = last_in_first_out
		self.layers: list[list[float]] = []
		self.last_rate = 0.0

	@property
	def qty(self) -> float:
		return sum(qty for qty, _rate in self.layers)

	@property
	def value(self) -> float:
		return sum(qty * rate for qty, rate in self.layers)

	def receive(self, qty: float, rate: float) -> None:
		self.last_rate = rate or self.last_rate

		if self.layers and self.layers[-1][0] <= 0:
			# the queue is short: the receipt first makes up the shortfall
			balance = self.layers[-1][0] + qty
			self.layers[-1] = [balance, rate] if balance > 0 else [balance, self.layers[-1][1]]
		elif self.layers and self.layers[-1][1] == rate:
			self.layers[-1][0] += qty
		else:
			self.layers.append([qty, rate])

	def issue(self, qty: float, preferred_rate: float | None = None) -> float:
		"""Take qty out layer by layer and return the value taken out.

		For FIFO, a layer carrying `preferred_rate` is taken first. If the queue runs
		dry, the rest goes negative at the last rate consumed.
		"""
		value_before = self.value

		while qty > 0:
			if not self.layers:
				self.layers.append([0.0, preferred_rate if preferred_rate is not None else self.last_rate])

			index = self.get_layer_to_consume(preferred_rate)
			layer_qty, layer_rate = self.layers[index]
			self.last_rate = layer_rate or self.last_rate

			if layer_qty > qty:
				self.layers[index][0] = layer_qty - qty
				qty = 0
				continue

			self.layers.pop(index)
			qty = qty - layer_qty
			if not self.layers and qty > 0:
				self.layers.append([-qty, preferred_rate or layer_rate])
				qty = 0

		return value_before - self.value

	def get_layer_to_consume(self, preferred_rate: float | None) -> int:
		if self.last_in_first_out:
			return -1

		if preferred_rate is not None:
			for index, (_qty, rate) in enumerate(self.layers):
				if rate == preferred_rate:
					return index

		return 0

	def set_balance(self, qty: float, rate: float) -> None:
		self.layers = [[qty, rate]]
		self.last_rate = rate or self.last_rate

	def clear(self) -> None:
		self.layers = []


@dataclass
class BatchLot:
	qty: float = 0.0
	value: float = 0.0

	@property
	def average_rate(self) -> float:
		return self.value / self.qty if self.qty else 0.0


@dataclass
class ItemWarehouseStock:
	"""The expected stock of one item in one warehouse, entry by entry."""

	valuation_method: str
	pool: MovingAveragePool | QueuePool = None
	batch_lots: dict[str, BatchLot] = field(default_factory=dict)
	serial_rates: dict[str, float] = field(default_factory=dict)
	serials_issued_before_receipt: dict[str, float] = field(default_factory=dict)
	last_valuation_rate: float = 0.0
	# the balance value as the ledger carries it: rounded after every entry
	carried_value: float = 0.0
	# the rate the ledger gave the entry being valued, for when nothing else is known
	ledger_rate_of_entry: float = 0.0

	def __post_init__(self):
		if self.pool is None:
			if self.valuation_method in ("FIFO", "LIFO"):
				self.pool = QueuePool(last_in_first_out=self.valuation_method == "LIFO")
			else:
				self.pool = MovingAveragePool()

	@property
	def qty(self) -> float:
		return (
			self.pool.qty
			+ sum(lot.qty for lot in self.batch_lots.values())
			+ len(self.serial_rates)
			- len(self.serials_issued_before_receipt)
		)

	@property
	def value(self) -> float:
		return (
			self.pool.value
			+ sum(lot.value for lot in self.batch_lots.values())
			+ sum(self.serial_rates.values())
			- sum(self.serials_issued_before_receipt.values())
		)

	@property
	def pool_basis(self) -> str:
		return {"FIFO": BASIS_FIFO, "LIFO": BASIS_LIFO}.get(self.valuation_method, BASIS_MOVING_AVERAGE)

	def get_rate_to_fall_back_on(self) -> float:
		"""The rate for stock going out of an empty lot: the warehouse's current average,
		else the last rate it was valued at."""
		if self.qty > 0 and self.value > 0:
			return self.value / self.qty

		return self.last_valuation_rate or self.pool.last_rate or self.ledger_rate_of_entry

	def receive_into_pool(self, qty: float, rate: float) -> None:
		self.pool.receive(qty, rate)

	def issue_from_pool(self, qty: float, preferred_rate: float | None = None) -> None:
		if not self.pool.qty > 0 and not self.pool.last_rate:
			self.pool.receive(0.0, preferred_rate or self.get_rate_to_fall_back_on())

		self.pool.issue(qty, preferred_rate)

	def receive_into_batch(self, batch_no: str, qty: float, rate: float) -> None:
		lot = self.batch_lots.setdefault(batch_no, BatchLot())
		lot.qty += qty
		lot.value += qty * rate

	def issue_from_batch(self, batch_no: str, qty: float) -> bool:
		"""Take qty out of the batch at its average rate, and say whether the batch
		had stock of its own to price it."""
		lot = self.batch_lots.setdefault(batch_no, BatchLot())
		has_stock = lot.qty > 0
		rate = lot.average_rate if has_stock else self.get_rate_to_fall_back_on()

		lot.qty -= qty
		lot.value -= qty * rate
		if abs(lot.qty) < 1e-9:
			# a spent batch takes its leftover value with it
			del self.batch_lots[batch_no]

		return has_stock

	def receive_serial(self, serial_no: str, rate: float) -> None:
		if serial_no in self.serials_issued_before_receipt:
			# the receipt makes up for the serial no that went out before it came in
			self.serials_issued_before_receipt.pop(serial_no)
			return

		self.serial_rates[serial_no] = rate

	def issue_serial(self, serial_no: str) -> bool:
		"""Take the serial no out at its receipt rate, and say whether it was on hand.

		A serial no that was never received here goes out at the fallback rate, and is
		held as a shortfall until it is received.
		"""
		if serial_no in self.serial_rates:
			self.serial_rates.pop(serial_no)
			return True

		self.serials_issued_before_receipt[serial_no] = self.get_rate_to_fall_back_on()
		return False

	def set_reconciled_balance(self, qty: float, rate: float) -> None:
		self.pool.set_balance(qty, rate)

	def write_off_leftover_value(self) -> None:
		"""With no stock left in the warehouse, no value should be left either."""
		self.pool.clear()
		self.batch_lots = {batch_no: lot for batch_no, lot in self.batch_lots.items() if abs(lot.qty) >= 1e-9}


def get_expected_valuation(item_code: str, warehouse: str) -> list[tuple[frappe._dict, ExpectedValues]]:
	"""Replay the whole ledger of the item in the warehouse.

	Returns every active Stock Ledger Entry in posting order, each with the values
	it should carry.
	"""
	ledger_entries = get_ledger_entries(item_code, warehouse)
	if not ledger_entries:
		return []

	company = ledger_entries[0].company
	valuation_method = get_valuation_method(item_code, company)
	details = ValuationDetails(item_code, warehouse, valuation_method, ledger_entries)
	stock = ItemWarehouseStock(valuation_method)

	result = []
	for entry in ledger_entries:
		result.append((entry, value_ledger_entry(stock, entry, details)))

	return result


def value_ledger_entry(stock: ItemWarehouseStock, entry, details: "ValuationDetails") -> ExpectedValues:
	"""Apply one entry to the expected stock and return what it should carry."""
	if details.valuation_method == "Standard Cost":
		return value_at_standard_cost(stock, entry, details)

	carried_value_before = stock.carried_value
	value_before = stock.value
	stock.ledger_rate_of_entry = get_ledger_rate(entry)

	if details.is_reconciled_balance(entry):
		reconciled_qty, reconciled_rate = details.get_reconciled_balance(entry)
		stock.set_reconciled_balance(reconciled_qty, reconciled_rate)
		basis = BASIS_RECONCILED
	elif entry.is_adjustment_entry and not flt(entry.actual_qty):
		basis = BASIS_WRITE_OFF
	elif flt(entry.actual_qty) > 0:
		basis = receive_stock(stock, entry, details)
	elif flt(entry.actual_qty) < 0:
		basis = issue_stock(stock, entry, details)
	else:
		basis = BASIS_INCOMING_RATE

	if abs(stock.qty) < details.qty_tolerance:
		if abs(stock.carried_value + stock.value - value_before) >= details.value_tolerance:
			basis = f"{basis}, {BASIS_WRITE_OFF}" if basis != BASIS_WRITE_OFF else basis
		stock.write_off_leftover_value()
		stock.carried_value = 0.0
	elif basis == BASIS_RECONCILED or details.is_valued_as_a_whole(entry):
		stock.carried_value = flt(stock.value, details.currency_precision)
	else:
		stock.carried_value = flt(
			stock.carried_value + stock.value - value_before, details.currency_precision
		)

	return make_expected_values(stock, carried_value_before, basis)


def get_ledger_rate(entry) -> float:
	if not flt(entry.actual_qty):
		return 0.0

	return abs(flt(entry.stock_value_difference) / flt(entry.actual_qty))


def receive_stock(stock: ItemWarehouseStock, entry, details: "ValuationDetails") -> str:
	for movement in details.get_lot_movements(entry):
		if movement.serial_no:
			stock.receive_serial(movement.serial_no, movement.rate)
		elif movement.batch_no and details.is_valued_batch_wise(movement.batch_no):
			stock.receive_into_batch(movement.batch_no, movement.qty, movement.rate)
		else:
			stock.receive_into_pool(movement.qty, movement.rate)

	return BASIS_INCOMING_RATE


def issue_stock(stock: ItemWarehouseStock, entry, details: "ValuationDetails") -> str:
	"""Take the entry's stock out of wherever it is held, and say how it was priced."""
	bases = []

	for movement in details.get_lot_movements(entry):
		if movement.serial_no:
			was_on_hand = stock.issue_serial(movement.serial_no)
			bases.append(BASIS_SERIAL_RATE if was_on_hand else BASIS_NO_STOCK)
		elif movement.batch_no and details.is_valued_batch_wise(movement.batch_no):
			had_stock = stock.issue_from_batch(movement.batch_no, movement.qty)
			bases.append(BASIS_BATCH_AVERAGE if had_stock else BASIS_NO_STOCK)
		else:
			return_rate = details.get_purchase_return_rate(entry)
			had_stock = stock.pool.qty > 0
			stock.issue_from_pool(movement.qty, preferred_rate=return_rate)

			if return_rate is not None:
				bases.append(BASIS_PURCHASE_RETURN)
			else:
				bases.append(stock.pool_basis if had_stock else BASIS_NO_STOCK)

	return ", ".join(dict.fromkeys(bases))


def value_at_standard_cost(stock: ItemWarehouseStock, entry, details: "ValuationDetails") -> ExpectedValues:
	from erpnext.stock.doctype.item_standard_cost.item_standard_cost import get_item_standard_rate

	carried_value_before = stock.carried_value
	rate = flt(get_item_standard_rate(entry.item_code, entry.company, entry.posting_date))

	if details.is_reconciled_balance(entry):
		qty, _rate = details.get_reconciled_balance(entry)
	else:
		qty = stock.pool.qty + flt(entry.actual_qty)

	stock.pool.set_balance(qty, rate)
	stock.carried_value = flt(stock.value, details.currency_precision)

	return make_expected_values(stock, carried_value_before, BASIS_STANDARD_COST)


def make_expected_values(
	stock: ItemWarehouseStock, carried_value_before: float, basis: str
) -> ExpectedValues:
	qty = stock.qty

	if qty:
		stock.last_valuation_rate = stock.carried_value / qty

	return ExpectedValues(
		qty_after_transaction=qty,
		stock_value_difference=stock.carried_value - carried_value_before,
		stock_value=stock.carried_value,
		valuation_rate=stock.last_valuation_rate,
		basis=basis,
	)


class ValuationDetails:
	"""Everything the replay needs beyond the ledger entries themselves, read in bulk
	up front: bundle rows, batch valuation flags, reconciled balances and return rates."""

	def __init__(self, item_code: str, warehouse: str, valuation_method: str, ledger_entries: list):
		self.item_code = item_code
		self.warehouse = warehouse
		self.valuation_method = valuation_method
		float_precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 3
		currency_precision = (
			cint(frappe.db.get_single_value("System Settings", "currency_precision")) or float_precision
		)
		self.currency_precision = currency_precision
		self.qty_tolerance = 1.0 / 10**float_precision
		self.value_tolerance = 1.0 / 10**currency_precision

		self.bundle_rows = get_bundle_rows(
			[entry.serial_and_batch_bundle for entry in ledger_entries if entry.serial_and_batch_bundle]
		)
		self.batch_wise_valued_batches = get_batch_wise_valued_batches(
			self.get_batches(ledger_entries), valuation_method
		)
		self.reconciled_balances = get_reconciled_balances(ledger_entries)
		self.dimension_fields = get_inventory_dimension_fields()
		self.purchase_return_rates = {}

	def get_batches(self, ledger_entries) -> set[str]:
		batches = {entry.batch_no for entry in ledger_entries if entry.batch_no}
		for rows in self.bundle_rows.values():
			batches.update(row.batch_no for row in rows if row.batch_no)

		return batches

	def is_valued_batch_wise(self, batch_no: str) -> bool:
		return batch_no in self.batch_wise_valued_batches

	def is_reconciled_balance(self, entry) -> bool:
		"""A Stock Reconciliation that sets the qty and rate outright, rather than moving lots."""
		return (
			entry.voucher_type == "Stock Reconciliation"
			and not entry.is_adjustment_entry
			and not entry.serial_and_batch_bundle
			and not entry.batch_no
			and not entry.serial_no
			and not any(entry.get(fieldname) for fieldname in self.dimension_fields)
		)

	def get_reconciled_balance(self, entry) -> tuple[float, float]:
		reconciled = self.reconciled_balances.get(entry.voucher_detail_no)
		if reconciled:
			return flt(reconciled.qty), flt(reconciled.valuation_rate, self.currency_precision)

		return flt(entry.qty_after_transaction), flt(entry.valuation_rate)

	def is_valued_as_a_whole(self, entry) -> bool:
		"""Whether the ledger works the entry's balance out afresh as qty x rate, which it does
		for a moving average entry without serial / batch nos. Every other entry adds its change
		to the balance carried from the entry before."""
		return (
			self.valuation_method == "Moving Average"
			and not entry.serial_and_batch_bundle
			and not entry.serial_no
			and not (entry.batch_no and self.is_valued_batch_wise(entry.batch_no))
		)

	def get_lot_movements(self, entry) -> list[LotMovement]:
		"""Split the entry's qty into what it moves in the pool, per batch and per serial no."""
		qty = abs(flt(entry.actual_qty))

		if entry.serial_and_batch_bundle and self.bundle_rows.get(entry.serial_and_batch_bundle):
			return [
				LotMovement(
					qty=abs(flt(row.qty)),
					rate=flt(row.incoming_rate),
					batch_no=row.batch_no,
					serial_no=row.serial_no,
				)
				for row in self.bundle_rows[entry.serial_and_batch_bundle]
			]

		# entries made before Serial and Batch Bundles carry their serial / batch nos inline
		if entry.serial_no:
			serial_nos = get_serial_nos(entry.serial_no)
			rate = flt(entry.incoming_rate)
			return [LotMovement(qty=1, rate=rate, serial_no=serial_no) for serial_no in serial_nos]

		return [LotMovement(qty=qty, rate=flt(entry.incoming_rate), batch_no=entry.batch_no)]

	def get_purchase_return_rate(self, entry) -> float | None:
		"""For a FIFO purchase return, the rate of the receipt row it returns. None when the
		entry is not one, or the receipt cannot be found."""
		if self.valuation_method != "FIFO" or entry.voucher_type not in RETURNABLE_PURCHASE_DOCTYPES:
			return None

		if entry.name not in self.purchase_return_rates:
			self.purchase_return_rates[entry.name] = get_rate_of_returned_receipt(entry)

		return self.purchase_return_rates[entry.name]


def get_ledger_entries(item_code: str, warehouse: str) -> list[frappe._dict]:
	fields = list(LEDGER_FIELDS) + get_inventory_dimension_fields()

	return frappe.get_all(
		"Stock Ledger Entry",
		filters={"item_code": item_code, "warehouse": warehouse, "is_cancelled": 0},
		fields=fields,
		order_by="posting_datetime asc, creation asc",
	)


def get_bundle_rows(bundles: list[str]) -> dict[str, list[frappe._dict]]:
	rows_by_bundle = {}
	if not bundles:
		return rows_by_bundle

	for rows in create_batch(bundles, 1000):
		for row in frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": ("in", rows)},
			fields=["parent", "serial_no", "batch_no", "qty", "incoming_rate"],
			order_by="idx asc",
		):
			rows_by_bundle.setdefault(row.parent, []).append(row)

	return rows_by_bundle


def get_batch_wise_valued_batches(batches: set[str], valuation_method: str) -> set[str]:
	if not batches:
		return set()

	if valuation_method == "Moving Average" and frappe.db.get_single_value(
		"Stock Settings", "do_not_use_batchwise_valuation"
	):
		return set()

	return set(
		frappe.get_all(
			"Batch",
			filters={"name": ("in", list(batches)), "use_batchwise_valuation": 1},
			pluck="name",
		)
	)


def get_reconciled_balances(ledger_entries) -> dict[str, frappe._dict]:
	rows = [
		entry.voucher_detail_no
		for entry in ledger_entries
		if entry.voucher_type == "Stock Reconciliation" and entry.voucher_detail_no
	]
	if not rows:
		return {}

	return {
		row.name: row
		for row in frappe.get_all(
			"Stock Reconciliation Item",
			filters={"name": ("in", rows)},
			fields=["name", "qty", "valuation_rate"],
		)
	}


def get_rate_of_returned_receipt(entry) -> float | None:
	voucher = frappe.db.get_value(
		entry.voucher_type, entry.voucher_no, ["is_return", "return_against"], as_dict=True
	)
	if not voucher or not voucher.is_return or not voucher.return_against:
		return None

	filters = {
		"voucher_type": entry.voucher_type,
		"voucher_no": voucher.return_against,
		"item_code": entry.item_code,
		"warehouse": entry.warehouse,
		"is_cancelled": 0,
		"actual_qty": (">", 0),
	}

	if entry.voucher_detail_no:
		returned_row = frappe.db.get_value(
			f"{entry.voucher_type} Item",
			entry.voucher_detail_no,
			get_return_against_item_fields(entry.voucher_type),
		)
		if returned_row:
			filters["voucher_detail_no"] = returned_row

	rate = frappe.db.get_value("Stock Ledger Entry", filters, "incoming_rate")
	return flt(rate) if rate is not None else None


def get_inventory_dimension_fields() -> list[str]:
	from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

	return [dimension.get("fieldname") for dimension in get_inventory_dimensions()]
