# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Settling the differences the Stock Valuation Comparison report finds, without reposting.

A repost rewrites the ledger from a difference onwards, closed fiscal years included. Where those
are filed and cannot change, an Adjustment Entry sets the stock right from a date instead: the
ledger before the date keeps its values, and from the date on, stock and accounts are what
erpnext.stock.expected_valuation says they should be.

An Adjustment Entry is a Stock Reconciliation with purpose "Adjustment Entry". Its rows are the
stock each item-warehouse should hold on the date: the serial nos at their own rates, the batches
valued batch-wise at theirs, and the stock valued in the pool layer by layer, with the batches or
serial nos in the pool spread over the layers. On submit, every item-warehouse is reset:

1. Primed: a batch valued batch-wise holds a value of its own that only leaves with its qty, so a
   batch holding value with no qty, or less than none, is brought up to one unit first. A batch
   or serial no short of stock is brought up to none.
2. Counted out: every serial no and batch on hand, and whatever qty no serial no or batch holds.
   With nothing left, the ledger writes off whatever value it held, right or wrong.
3. Counted in: the rows.

Every entry of the reset carries is_adjustment_entry, which reports use to show the reset as the
net change it is (see net_adjustment_entries). A later repost through the date values the count
out at whatever the ledger then holds, so the reset keeps setting the stock to its rows.

As the ledger after an Adjustment Entry no longer follows from the ledger before it, no stock
transaction may be posted or cancelled before an Adjustment Entry of the same item and warehouse,
or of the same serial nos or batches.
"""

from collections import defaultdict
from dataclasses import dataclass, field

import frappe
from frappe import _, bold
from frappe.query_builder.functions import Sum
from frappe.utils import create_batch, flt, format_datetime, get_datetime, get_link_to_form, getdate
from pypika.terms import ExistsCriterion

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.expected_valuation import ADJUSTMENT_ENTRY, QueuePool, iterate_expected_stock_at
from erpnext.stock.stock_ledger import make_sl_entries
from erpnext.stock.utils import get_combine_datetime

QTY_NOISE = 1e-9


class BackdatedEntryBeforeAdjustmentError(frappe.ValidationError):
	pass


@dataclass
class AdjustmentRow:
	"""One row of an Adjustment Entry: stock counted in at a rate, as a batch, serial nos, or
	stock without either."""

	qty: float
	valuation_rate: float
	batch_no: str | None = None
	serial_nos: list[str] = field(default_factory=list)

	@property
	def key(self) -> tuple:
		return (self.batch_no or None, tuple(sorted(self.serial_nos)), flt(self.qty, 6))


@dataclass
class AdjustmentPlan:
	"""The stock one item-warehouse should hold on the date of the Adjustment Entry."""

	item_code: str
	warehouse: str
	ledger_qty: float = 0.0
	ledger_value: float = 0.0
	rows: list[AdjustmentRow] = field(default_factory=list)
	# why the item-warehouse is not adjusted, when it is not
	reason: str | None = None

	@property
	def qty(self) -> float:
		return sum(row.qty for row in self.rows)

	@property
	def value(self) -> float:
		return sum(row.qty * row.valuation_rate for row in self.rows)


@dataclass
class LedgerLots:
	"""The serial nos and batches the ledger holds in a warehouse, and their values."""

	batch_qty: dict[str, float] = field(default_factory=lambda: defaultdict(float))
	batch_value: dict[str, float] = field(default_factory=lambda: defaultdict(float))
	serial_qty: dict[str, float] = field(default_factory=lambda: defaultdict(float))


def get_adjustment_plans(
	item_warehouses: list[tuple[str, str]], posting_datetime, exclude_voucher_no: str | None = None
) -> dict[tuple[str, str], AdjustmentPlan]:
	"""The stock each item-warehouse should hold at `posting_datetime`. An item-warehouse with no
	stock ledger entries by then is left out."""
	plans = {}

	for item_code, warehouse, stock, last_entry, details in iterate_expected_stock_at(
		item_warehouses, posting_datetime, exclude_voucher_no
	):
		plan = AdjustmentPlan(
			item_code=item_code,
			warehouse=warehouse,
			ledger_qty=flt(last_entry.qty_after_transaction),
			ledger_value=flt(last_entry.stock_value),
		)

		if (
			abs(plan.ledger_qty - stock.qty) < details.qty_tolerance
			and abs(plan.ledger_value - stock.carried_value) < details.value_tolerance
		):
			plan.reason = _("Its stock qty and value are already right on this date.")
		else:
			set_adjustment_rows(plan, stock, details, posting_datetime, exclude_voucher_no)

		plans[(item_code, warehouse)] = plan

	return plans


def set_adjustment_rows(plan: AdjustmentPlan, stock, details, posting_datetime, exclude_voucher_no) -> None:
	if stock.serials_issued_before_receipt or any(
		lot.qty < -details.qty_tolerance for lot in stock.batch_lots.values()
	):
		plan.reason = _("Some of its serial nos or batches should be short of stock on this date.")
		return

	layers = get_pool_layers(stock, details, posting_datetime)
	if any(qty < 0 for qty, _rate in layers):
		plan.reason = _("Its stock should be negative on this date, which cannot be counted in.")
		return

	precision = details.currency_precision
	serial_nos_by_rate = defaultdict(list)
	for serial_no, rate in stock.serial_rates.items():
		serial_nos_by_rate[flt(rate, precision)].append(serial_no)

	for rate, serial_nos in sorted(serial_nos_by_rate.items()):
		plan.rows.append(
			AdjustmentRow(qty=len(serial_nos), valuation_rate=rate, serial_nos=sorted(serial_nos))
		)

	for batch_no, lot in sorted(stock.batch_lots.items()):
		if lot.qty >= details.qty_tolerance:
			plan.rows.append(
				AdjustmentRow(
					qty=lot.qty, valuation_rate=flt(lot.value / lot.qty, precision), batch_no=batch_no
				)
			)

	pooled_lots = get_pooled_lots(plan, details, posting_datetime, exclude_voucher_no)
	is_serial = values_serial_nos_in_pool(details.data.items[plan.item_code], details)
	plan.rows.extend(spread_over_layers(layers, pooled_lots, details, is_serial))

	if not plan.rows:
		# nothing should be on hand: the reset only counts out
		plan.rows.append(AdjustmentRow(qty=0, valuation_rate=0))


def get_pool_layers(stock, details, posting_datetime) -> list[tuple[float, float]]:
	"""The [qty, rate] layers the pool should hold, oldest first: counted in in this order, they
	give a FIFO queue or a LIFO stack back as it should be. A moving average pool is one layer."""
	precision = details.currency_precision
	pool = stock.pool

	if isinstance(pool, QueuePool):
		layers = [(qty, flt(rate, precision)) for qty, rate in pool.layers]
	else:
		layers = [(pool.qty, flt(pool.rate, precision))]

	return [(qty, rate) for qty, rate in layers if abs(qty) >= details.qty_tolerance]


def get_pooled_lots(plan: AdjustmentPlan, details, posting_datetime, exclude_voucher_no) -> list[list]:
	"""The [batch or serial no, qty] on hand in the ledger that are valued in the pool, oldest first,
	which the pool's stock is counted back in as."""
	item = details.data.items[plan.item_code]
	if not item.has_serial_no and not item.has_batch_no:
		return []

	lots = get_ledger_lots(plan.item_code, plan.warehouse, posting_datetime, exclude_voucher_no)
	if values_serial_nos_in_pool(item, details):
		return [[serial_no, 1.0] for serial_no, qty in lots.serial_qty.items() if qty > 0]

	if item.has_serial_no:
		# serial nos are valued on their own: stock in the pool has none
		return []

	return [
		[batch_no, qty]
		for batch_no, qty in lots.batch_qty.items()
		if qty >= details.qty_tolerance and not details.is_valued_batch_wise(batch_no)
	]


def values_serial_nos_in_pool(item, details) -> bool:
	"""Whether the item's serial nos are valued with the rest of its stock rather than one by one:
	without serial no wise valuation."""
	return bool(item.has_serial_no and details.values_everything_in_pool)


def spread_over_layers(layers, pooled_lots: list[list], details, is_serial: bool) -> list[AdjustmentRow]:
	"""Rows that count the pool's layers in, as its batches or serial nos while there are any, and
	as stock without either for the rest."""
	rows = []

	for layer_qty, rate in layers:
		serial_nos = []
		while layer_qty >= details.qty_tolerance and pooled_lots:
			lot = pooled_lots[0]
			qty = min(layer_qty, lot[1])
			if is_serial:
				serial_nos.append(lot[0])
			else:
				rows.append(AdjustmentRow(qty=qty, valuation_rate=rate, batch_no=lot[0]))

			layer_qty -= qty
			lot[1] -= qty
			if lot[1] < details.qty_tolerance:
				pooled_lots.pop(0)

		if serial_nos:
			rows.append(AdjustmentRow(qty=len(serial_nos), valuation_rate=rate, serial_nos=serial_nos))

		if layer_qty >= details.qty_tolerance:
			rows.append(AdjustmentRow(qty=layer_qty, valuation_rate=rate))

	return rows


def get_ledger_lots(item_code: str, warehouse: str, posting_datetime, exclude_voucher_no=None) -> LedgerLots:
	"""The qty of every serial no and batch in the warehouse, and the value of every batch, as the
	ledger holds them at `posting_datetime`, in the order they were first received: from the bundles,
	and from the serial and batch nos of entries made before bundles."""
	bundle = frappe.qb.DocType("Serial and Batch Bundle")
	entry = frappe.qb.DocType("Serial and Batch Entry")
	ledger = frappe.qb.DocType("Stock Ledger Entry")
	cutoff = get_datetime(posting_datetime)

	bundle_entries = (
		frappe.qb.from_(bundle)
		.inner_join(entry)
		.on(entry.parent == bundle.name)
		.select(entry.serial_no, entry.batch_no, entry.qty, entry.stock_value_difference)
		.where(
			(bundle.item_code == item_code)
			& (bundle.warehouse == warehouse)
			& (bundle.docstatus == 1)
			& (bundle.is_cancelled == 0)
			& (bundle.posting_datetime <= cutoff)
		)
		.orderby(bundle.posting_datetime)
		.orderby(bundle.creation)
	)
	legacy_entries = (
		frappe.qb.from_(ledger)
		.select(ledger.serial_no, ledger.batch_no, ledger.actual_qty, ledger.stock_value_difference)
		.where(
			(ledger.item_code == item_code)
			& (ledger.warehouse == warehouse)
			& (ledger.is_cancelled == 0)
			& (ledger.posting_datetime <= cutoff)
			& (ledger.serial_and_batch_bundle.isnull() | (ledger.serial_and_batch_bundle == ""))
			& ((ledger.batch_no.isnotnull() & (ledger.batch_no != "")) | ledger.serial_no.isnotnull())
		)
	)
	if exclude_voucher_no:
		bundle_entries = bundle_entries.where(bundle.voucher_no != exclude_voucher_no)
		legacy_entries = legacy_entries.where(ledger.voucher_no != exclude_voucher_no)

	lots = LedgerLots()
	for row in bundle_entries.run(as_dict=True):
		if row.serial_no:
			lots.serial_qty[row.serial_no] += flt(row.qty)
		if row.batch_no:
			lots.batch_qty[row.batch_no] += flt(row.qty)
			lots.batch_value[row.batch_no] += flt(row.stock_value_difference)

	for row in legacy_entries.run(as_dict=True):
		for serial_no in get_serial_nos(row.serial_no or ""):
			lots.serial_qty[serial_no] += 1 if flt(row.actual_qty) > 0 else -1
		if row.batch_no:
			lots.batch_qty[row.batch_no] += flt(row.actual_qty)
			lots.batch_value[row.batch_no] += flt(row.stock_value_difference)

	return lots


def make_adjustment_entry(
	company: str,
	item_warehouses: list[tuple[str, str]],
	posting_date,
	posting_time,
	expense_account: str | None = None,
	cost_center: str | None = None,
):
	"""A draft Adjustment Entry for the item-warehouses that can be adjusted, and the plans of all
	of them, which say why the others are not."""
	plans = get_adjustment_plans(item_warehouses, get_combine_datetime(posting_date, posting_time))

	doc = frappe.new_doc("Stock Reconciliation")
	doc.update(
		{
			"purpose": ADJUSTMENT_ENTRY,
			"company": company,
			"posting_date": posting_date,
			"posting_time": posting_time,
			"set_posting_time": 1,
			"expense_account": expense_account or get_stock_adjustment_account(company),
			"cost_center": cost_center or frappe.get_cached_value("Company", company, "cost_center"),
		}
	)

	for plan in plans.values():
		if not plan.reason:
			for row in plan.rows:
				doc.append("items", make_item_row(plan, row))

	if doc.items:
		doc.insert()

	return doc, plans


def get_stock_adjustment_account(company: str) -> str | None:
	return frappe.get_cached_value("Company", company, "stock_adjustment_account") or frappe.db.get_value(
		"Account", {"account_type": "Stock Adjustment", "company": company, "is_group": 0}, "name"
	)


def make_item_row(plan: AdjustmentPlan, row: AdjustmentRow) -> dict:
	return {
		"item_code": plan.item_code,
		"warehouse": plan.warehouse,
		"qty": row.qty,
		"valuation_rate": row.valuation_rate,
		"allow_zero_valuation_rate": 0 if row.valuation_rate else 1,
		"batch_no": row.batch_no,
		"serial_no": "\n".join(row.serial_nos),
		"use_serial_batch_fields": 1 if row.batch_no or row.serial_nos else 0,
	}


class AdjustmentEntry:
	"""Validating, posting and cancelling a Stock Reconciliation with purpose Adjustment Entry."""

	def __init__(self, doc):
		self.doc = doc
		self.posting_datetime = get_combine_datetime(doc.posting_date, doc.posting_time)

	def get_rows_by_item_warehouse(self) -> dict[tuple[str, str], list]:
		rows = defaultdict(list)
		for row in self.doc.items:
			rows[(row.item_code, row.warehouse)].append(row)

		return rows

	def get_plans(self) -> dict[tuple[str, str], AdjustmentPlan]:
		if self.doc.flags.adjustment_plans is None:
			self.doc.flags.adjustment_plans = get_adjustment_plans(
				list(self.get_rows_by_item_warehouse()),
				self.posting_datetime,
				exclude_voucher_no=self.doc.name,
			)

		return self.doc.flags.adjustment_plans

	def validate(self) -> None:
		"""Every item-warehouse must be counted in as the stock it should hold on the date, in full,
		or it would be left half reset."""
		for (item_code, warehouse), rows in self.get_rows_by_item_warehouse().items():
			plan = self.get_plans().get((item_code, warehouse))
			if not plan or plan.reason:
				frappe.throw(
					_("Item {0} in Warehouse {1} cannot be adjusted on {2}: {3}").format(
						bold(item_code),
						bold(warehouse),
						format_datetime(self.posting_datetime),
						plan.reason if plan else _("It has no stock transactions by then."),
					),
					title=_("Adjustment Entry"),
				)

			given = sorted(
				(
					AdjustmentRow(
						qty=flt(row.qty),
						valuation_rate=flt(row.valuation_rate),
						batch_no=row.batch_no,
						serial_nos=get_serial_nos(row.serial_no or ""),
					)
					for row in rows
				),
				key=lambda row: (row.key, row.valuation_rate),
			)
			needed = sorted(plan.rows, key=lambda row: (row.key, row.valuation_rate))
			rate_precision = rows[0].precision("valuation_rate")

			if len(given) != len(needed) or any(
				a.key != b.key
				or flt(a.valuation_rate, rate_precision) != flt(b.valuation_rate, rate_precision)
				for a, b in zip(given, needed, strict=True)
			):
				frappe.throw(
					_(
						"The rows of Item {0} in Warehouse {1} are not the stock it should hold on this date. Make the Adjustment Entry again from the Stock Valuation Comparison report."
					).format(bold(item_code), bold(warehouse)),
					title=_("Adjustment Entry"),
				)

			self.set_row_amounts(plan, rows)

		self.doc.difference_amount = flt(
			sum(flt(row.amount_difference) for row in self.doc.items), self.doc.precision("difference_amount")
		)

	def set_row_amounts(self, plan: AdjustmentPlan, rows) -> None:
		"""The first row of an item-warehouse shows what the ledger held, which the reset counts out."""
		for index, row in enumerate(rows):
			row.amount = flt(flt(row.qty) * flt(row.valuation_rate), row.precision("amount"))
			row.current_qty = plan.ledger_qty if index == 0 else 0
			row.current_amount = flt(plan.ledger_value, row.precision("current_amount")) if index == 0 else 0
			row.current_valuation_rate = (
				flt(plan.ledger_value / plan.ledger_qty, row.precision("current_valuation_rate"))
				if index == 0 and plan.ledger_qty
				else 0
			)
			row.quantity_difference = flt(row.qty) - flt(row.current_qty)
			row.amount_difference = flt(row.amount) - flt(row.current_amount)

	def post(self) -> None:
		from erpnext.stock.serial_batch_bundle import update_batch_qty

		for (item_code, warehouse), rows in self.get_rows_by_item_warehouse().items():
			self.reset(item_code, warehouse, rows)
			self.validate_result(item_code, warehouse, rows)

		# once for the whole voucher, as it adds up every batch of all of its bundles
		update_batch_qty(self.doc.doctype, self.doc.name, self.doc.docstatus)

	def reset(self, item_code: str, warehouse: str, rows) -> None:
		lots = get_ledger_lots(item_code, warehouse, self.posting_datetime, self.doc.name)
		item = frappe.get_cached_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=True)
		ledger_qty = flt(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"item_code": item_code,
					"warehouse": warehouse,
					"is_cancelled": 0,
					"posting_datetime": ("<=", self.posting_datetime),
					"voucher_no": ("!=", self.doc.name),
				},
				"qty_after_transaction",
				order_by="posting_datetime desc, creation desc",
			)
		)
		first_row = rows[0]

		# 1. primed, so that every serial no and batch can be counted out
		primed = self.get_lots_to_prime(item_code, lots)
		if primed:
			# a batch is counted out at the average of its entries other than those of the count-out's
			# row, which must include the priming, so it has a row of its own
			self.post_entry(first_row, sum(primed.values()), lots=primed, rate=0, row_suffix="-primed")

		on_hand = {lot: qty + primed.get(lot, 0) for lot, qty in self.get_lots_on_hand(item, lots).items()}
		on_hand = {lot: qty for lot, qty in on_hand.items() if qty >= QTY_NOISE}

		# 2. counted out, with whatever qty no serial no or batch holds
		without_lot = ledger_qty + sum(primed.values()) - sum(on_hand.values())
		if without_lot <= -QTY_NOISE:
			self.post_entry(first_row, -without_lot, rate=0)
		if on_hand:
			self.post_entry(first_row, -sum(on_hand.values()), lots=on_hand)
		if without_lot >= QTY_NOISE:
			self.post_entry(first_row, -without_lot)

		# 3. counted in
		for row in rows:
			if flt(row.qty):
				lots_of_row = (
					{serial_no: 1.0 for serial_no in get_serial_nos(row.serial_no)}
					if row.serial_no
					else ({row.batch_no: flt(row.qty)} if row.batch_no else None)
				)
				self.post_entry(
					row, flt(row.qty), lots=lots_of_row, rate=flt(row.valuation_rate), counts_in_row=True
				)

	def get_lots_on_hand(self, item, lots: LedgerLots) -> dict:
		if item.has_serial_no:
			return dict(lots.serial_qty)

		if item.has_batch_no:
			return dict(lots.batch_qty)

		return {}

	def get_lots_to_prime(self, item_code: str, lots: LedgerLots) -> dict:
		"""The qty that brings every serial no and batch short of stock up to none, and every batch
		valued batch-wise that holds a value of its own without stock up to one unit, which then
		leaves with that value."""
		primed = {}
		for serial_no, qty in lots.serial_qty.items():
			if qty <= -QTY_NOISE:
				primed[serial_no] = -qty

		batch_wise = set(
			frappe.get_all(
				"Batch",
				filters={"name": ("in", list(lots.batch_qty) or [""]), "use_batchwise_valuation": 1},
				pluck="name",
			)
		)
		if (
			frappe.get_single_value("Stock Settings", "do_not_use_batchwise_valuation")
			and (
				frappe.get_cached_value("Item", item_code, "valuation_method")
				or frappe.get_cached_value("Company", self.doc.company, "valuation_method")
			)
			== "Moving Average"
		):
			batch_wise = set()

		for batch_no, qty in lots.batch_qty.items():
			holds_value = abs(flt(lots.batch_value[batch_no], 2)) > 0
			if batch_no in batch_wise and qty < QTY_NOISE and (holds_value or qty <= -QTY_NOISE):
				primed[batch_no] = 1 - qty
			elif qty <= -QTY_NOISE:
				primed[batch_no] = -qty

		return primed

	def post_entry(
		self,
		row,
		qty: float,
		lots: dict | None = None,
		rate: float | None = None,
		counts_in_row=False,
		row_suffix="",
	) -> None:
		"""Post one entry of the reset: inward for a positive qty, outward for a negative one."""
		sle = frappe._dict(
			{
				"doctype": "Stock Ledger Entry",
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time,
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"voucher_detail_no": row.name + row_suffix,
				"actual_qty": qty,
				"company": self.doc.company,
				"stock_uom": frappe.get_cached_value("Item", row.item_code, "stock_uom"),
				"is_cancelled": 0,
				"is_adjustment_entry": 1,
			}
		)
		if qty > 0:
			sle.incoming_rate = flt(rate)

		if lots:
			sle.serial_and_batch_bundle = self.make_bundle(row, qty, lots, rate, sle.voucher_detail_no)
			if counts_in_row:
				row.db_set("serial_and_batch_bundle", sle.serial_and_batch_bundle, update_modified=False)

		# each entry is valued on the ones before it, so they are posted one by one
		make_sl_entries([sle], allow_negative_stock=True)

	def make_bundle(self, row, qty: float, lots: dict, rate: float | None, voucher_detail_no) -> str:
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		has_serial_no = frappe.get_cached_value("Item", row.item_code, "has_serial_no")
		bundle = SerialBatchCreation(
			{
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"company": self.doc.company,
				"posting_datetime": self.posting_datetime,
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"voucher_detail_no": voucher_detail_no,
				"type_of_transaction": "Inward" if qty > 0 else "Outward",
				"qty": qty,
				"incoming_rate": flt(rate),
				"serial_nos": list(lots) if has_serial_no else None,
				"batches": None if has_serial_no else frappe._dict(lots),
				"do_not_submit": True,
			}
		).make_serial_and_batch_bundle()

		return bundle.name

	def validate_result(self, item_code: str, warehouse: str, rows) -> None:
		"""After the reset, the ledger must hold what the rows count in."""
		balance = (
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_type": self.doc.doctype,
					"voucher_no": self.doc.name,
					"item_code": item_code,
					"warehouse": warehouse,
					"is_cancelled": 0,
				},
				["qty_after_transaction", "stock_value"],
				order_by="posting_datetime desc, creation desc",
				as_dict=True,
			)
			or frappe._dict()
		)

		qty = sum(flt(row.qty) for row in rows)
		value = sum(flt(row.amount) for row in rows)
		allowance = 0.01 * (len(rows) + 1)

		if (
			abs(flt(balance.qty_after_transaction) - qty) > 1e-6
			or abs(flt(balance.stock_value) - value) > allowance
		):
			frappe.throw(
				_(
					"After the adjustment, Item {0} in Warehouse {1} would hold a qty of {2} worth {3}, instead of {4} worth {5}."
				).format(
					bold(item_code),
					bold(warehouse),
					flt(balance.qty_after_transaction),
					flt(balance.stock_value),
					qty,
					value,
				),
				title=_("Adjustment Entry"),
			)

	def cancel(self) -> None:
		"""Reverse every entry of the reset, the last one first."""
		entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": self.doc.doctype, "voucher_no": self.doc.name, "is_cancelled": 0},
			fields=[
				"item_code",
				"warehouse",
				"posting_date",
				"posting_time",
				"voucher_detail_no",
				"actual_qty",
				"incoming_rate",
				"outgoing_rate",
				"serial_and_batch_bundle",
				"stock_uom",
			],
			order_by="posting_datetime asc, creation asc",
		)

		sl_entries = [
			frappe._dict(
				entry,
				doctype="Stock Ledger Entry",
				voucher_type=self.doc.doctype,
				voucher_no=self.doc.name,
				company=self.doc.company,
				is_cancelled=1,
				is_adjustment_entry=1,
			)
			for entry in entries
		]
		sl_entries.reverse()

		if sl_entries:
			self.doc.make_sl_entries(sl_entries, allow_negative_stock=True)

	def set_difference_amount_from_ledger(self) -> None:
		"""After a repost, the difference is what the reset's entries carry."""
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		difference = (
			frappe.qb.from_(ledger)
			.select(Sum(ledger.stock_value_difference))
			.where(
				(ledger.voucher_type == self.doc.doctype)
				& (ledger.voucher_no == self.doc.name)
				& (ledger.is_cancelled == 0)
			)
		).run()[0][0]
		self.doc.db_set(
			"difference_amount",
			flt(difference, self.doc.precision("difference_amount")),
			update_modified=False,
		)


def is_adjustment_voucher(voucher_type: str | None, voucher_no: str | None) -> bool:
	return bool(
		voucher_type == "Stock Reconciliation"
		and voucher_no
		and frappe.get_cached_value("Stock Reconciliation", voucher_no, "purpose") == ADJUSTMENT_ENTRY
	)


class AdjustmentNetting:
	"""Shows the reset of each Adjustment Entry to a report as the net change it is.

	An Adjustment Entry counts the whole stock of an item-warehouse out and back in, which, entry
	by entry, reads as that much stock going out and coming in, and as stock received afresh on its
	date. A report that totals what went in and out, or ages stock, reads the entries through this
	instead.

	What it needs is read when it is made, so make it before opening a streaming cursor over the
	entries: nothing is queried while they are read.
	"""

	def __init__(self, by_lot: bool = False):
		self.vouchers = set(
			frappe.get_all(
				"Stock Reconciliation", filters={"purpose": ADJUSTMENT_ENTRY, "docstatus": 1}, pluck="name"
			)
		)
		self.lot_changes = get_adjustment_lot_changes(self.vouchers) if by_lot and self.vouchers else {}

	def is_adjustment(self, entry) -> bool:
		return bool(
			entry.get("is_adjustment_entry")
			and entry.get("voucher_type") == "Stock Reconciliation"
			and entry.get("voucher_no") in self.vouchers
		)

	def net(self, entries, key_fields: tuple[str, ...] = ("item_code", "warehouse")):
		"""The entries, with those of one Adjustment Entry and the same `key_fields` merged into one:
		the sum of their qty and value, and the balance after the last of them. The merged entry keeps
		is_adjustment_entry, so it reads as a change, not as a reconciled balance.

		`entries` must be in posting order, in which the entries of a reset follow each other."""
		merged = None
		merged_key = None

		for entry in entries:
			key = None
			if self.is_adjustment(entry):
				key = (entry.voucher_no, *(entry.get(fieldname) for fieldname in key_fields))

			if merged is not None and key == merged_key:
				for fieldname in ("actual_qty", "stock_value_difference"):
					if fieldname in entry:
						merged[fieldname] = flt(merged.get(fieldname)) + flt(entry.get(fieldname))
				for fieldname in ("qty_after_transaction", "stock_value", "valuation_rate"):
					if fieldname in entry:
						merged[fieldname] = entry.get(fieldname)
				continue

			if merged is not None:
				yield merged
				merged = merged_key = None

			if key is None:
				yield entry
			else:
				merged, merged_key = frappe._dict(entry), key

		if merged is not None:
			yield merged

	def net_by_lot(self, entries, item_field: str = "item_code"):
		"""Like net, but for a report that follows serial and batch nos: the reset becomes one entry
		per batch whose qty changed, one for the serial nos that left and one for those that came, and
		one for the qty no serial or batch no holds, each without a bundle. A serial or batch no the
		reset counts back in as it was counted out is left out, so it keeps its age."""
		for entry in self.net(entries, key_fields=(item_field, "warehouse")):
			changes = (
				self.lot_changes.get((entry.voucher_no, entry.get(item_field), entry.warehouse))
				if self.is_adjustment(entry)
				else None
			)
			if changes:
				yield from split_by_lot(entry, changes)
			else:
				yield entry


def get_adjustment_lot_changes(vouchers: set[str]) -> dict[tuple[str, str, str], dict]:
	"""The net qty and value each Adjustment Entry moved per serial no and per batch, by item and
	warehouse."""
	bundle = frappe.qb.DocType("Serial and Batch Bundle")
	entry = frappe.qb.DocType("Serial and Batch Entry")

	changes = {}
	for vouchers_to_read in create_batch(list(vouchers), 1000):
		for row in (
			frappe.qb.from_(bundle)
			.inner_join(entry)
			.on(entry.parent == bundle.name)
			.select(
				bundle.voucher_no,
				bundle.item_code,
				bundle.warehouse,
				entry.serial_no,
				entry.batch_no,
				entry.qty,
				entry.stock_value_difference,
			)
			.where(
				(bundle.voucher_type == "Stock Reconciliation")
				& bundle.voucher_no.isin(vouchers_to_read)
				& (bundle.docstatus == 1)
				& (bundle.is_cancelled == 0)
			)
		).run(as_dict=True):
			lots = changes.setdefault(
				(row.voucher_no, row.item_code, row.warehouse), {"serial_no": {}, "batch_no": {}}
			)
			fieldname = "serial_no" if row.serial_no else "batch_no"
			lot = lots[fieldname].setdefault(row.serial_no or row.batch_no, [0.0, 0.0])
			lot[0] += flt(row.qty)
			lot[1] += flt(row.stock_value_difference)

	return changes


def split_by_lot(entry, changes: dict):
	"""The net change of a reset as entries per serial and batch no, without bundles."""

	def lot_entry(qty, value, **lot):
		return frappe._dict(
			entry,
			actual_qty=qty,
			stock_value_difference=value,
			serial_and_batch_bundle=None,
			serial_no=lot.get("serial_no"),
			batch_no=lot.get("batch_no"),
		)

	lot_qty = lot_value = 0.0
	for leaving in (True, False):
		moved = {
			serial_no: change
			for serial_no, change in changes["serial_no"].items()
			if abs(change[0]) >= QTY_NOISE and (change[0] < 0) == leaving
		}
		if moved:
			qty = sum(change[0] for change in moved.values())
			value = sum(change[1] for change in moved.values())
			lot_qty += qty
			lot_value += value
			yield lot_entry(qty, value, serial_no="\n".join(sorted(moved)))

	for batch_no, (qty, value) in sorted(changes["batch_no"].items()):
		if abs(qty) >= QTY_NOISE:
			lot_qty += qty
			lot_value += value
			yield lot_entry(qty, value, batch_no=batch_no)

	if abs(flt(entry.actual_qty) - lot_qty) >= QTY_NOISE:
		yield lot_entry(flt(entry.actual_qty) - lot_qty, flt(entry.stock_value_difference) - lot_value)


def validate_no_later_adjustment_entry(sle) -> None:
	"""No stock transaction may be posted or cancelled before an Adjustment Entry of its item and
	warehouse, or of its serial nos or batches: the ledger after the adjustment would no longer
	follow from the ledger before it."""
	if not frappe.db.exists("Stock Reconciliation", {"purpose": ADJUSTMENT_ENTRY, "docstatus": 1}):
		return

	# driven from the few Adjustment Entries, through the (purpose, posting_date) index,
	# to their own ledger entries, rather than from all the later ledger entries of the item
	reconciliation = frappe.qb.DocType("Stock Reconciliation")
	ledger = frappe.qb.DocType("Stock Ledger Entry")

	of_item = ledger.warehouse == sle.warehouse
	serial_nos, batch_nos = get_serial_and_batch_nos(sle)
	if serial_nos or batch_nos:
		entry = frappe.qb.DocType("Serial and Batch Entry")
		lot = entry.serial_no.isin(serial_nos) if serial_nos else entry.batch_no.isin(batch_nos)
		if serial_nos and batch_nos:
			lot = lot | entry.batch_no.isin(batch_nos)
		of_item = of_item | ExistsCriterion(
			frappe.qb.from_(entry)
			.select(entry.name)
			.where((entry.parent == ledger.serial_and_batch_bundle) & lot)
		)

	adjustment = (
		frappe.qb.from_(reconciliation)
		.inner_join(ledger)
		.on((ledger.voucher_no == reconciliation.name) & (ledger.voucher_type == "Stock Reconciliation"))
		.select(ledger.voucher_no, ledger.posting_datetime)
		.where(
			(reconciliation.purpose == ADJUSTMENT_ENTRY)
			& (reconciliation.docstatus == 1)
			& (reconciliation.posting_date >= getdate(sle.posting_date))
			& (reconciliation.name != sle.voucher_no)
			& (ledger.is_cancelled == 0)
			& (ledger.item_code == sle.item_code)
			& (ledger.posting_datetime > get_datetime(sle.posting_datetime))
			& of_item
		)
		.orderby(ledger.posting_datetime, order=frappe.qb.desc)
		.limit(1)
	).run(as_dict=True)

	if adjustment:
		frappe.throw(
			_(
				"Item {0} in Warehouse {1} was adjusted by {2} on {3}, so no stock transaction dated before it can be posted or cancelled. Post it on or after that date, or cancel the Adjustment Entry first."
			).format(
				bold(sle.item_code),
				bold(sle.warehouse),
				get_link_to_form("Stock Reconciliation", adjustment[0].voucher_no),
				format_datetime(adjustment[0].posting_datetime),
			),
			title=_("Backdated Entry Before Adjustment Entry"),
			exc=BackdatedEntryBeforeAdjustmentError,
		)


def get_serial_and_batch_nos(sle) -> tuple[list[str], list[str]]:
	serial_nos, batch_nos = set(), set()
	if sle.serial_and_batch_bundle:
		for entry in frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": sle.serial_and_batch_bundle},
			fields=["serial_no", "batch_no"],
		):
			if entry.serial_no:
				serial_nos.add(entry.serial_no)
			if entry.batch_no:
				batch_nos.add(entry.batch_no)

	if sle.serial_no:
		serial_nos.update(get_serial_nos(sle.serial_no))
	if sle.batch_no:
		batch_nos.add(sle.batch_no)

	return sorted(serial_nos), sorted(batch_nos)


def get_adjusted_until(item_warehouses: list[tuple[str, str]], to_date=None) -> dict[tuple[str, str], dict]:
	"""The latest Adjustment Entry of each item-warehouse, up to `to_date`."""
	if not item_warehouses:
		return {}

	ledger = frappe.qb.DocType("Stock Ledger Entry")
	reconciliation = frappe.qb.DocType("Stock Reconciliation")

	query = (
		frappe.qb.from_(ledger)
		.inner_join(reconciliation)
		.on(reconciliation.name == ledger.voucher_no)
		.select(ledger.item_code, ledger.warehouse, ledger.voucher_no, ledger.posting_datetime)
		.where(
			(ledger.voucher_type == "Stock Reconciliation")
			& (reconciliation.purpose == ADJUSTMENT_ENTRY)
			& (ledger.is_cancelled == 0)
			& ledger.item_code.isin(list({item_code for item_code, _warehouse in item_warehouses}))
		)
		.orderby(ledger.posting_datetime)
	)
	if to_date:
		query = query.where(ledger.posting_date <= to_date)

	adjusted_until = {}
	for row in query.run(as_dict=True):
		adjusted_until[(row.item_code, row.warehouse)] = row

	return adjusted_until
