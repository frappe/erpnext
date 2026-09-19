import datetime
import json
from collections import defaultdict

import frappe
from frappe.query_builder.functions import Locate, Sum
from frappe.utils import flt, nowtime
from pypika import Order
from pypika.functions import Coalesce, Concat
from pypika.terms import ExistsCriterion

from erpnext.deprecation_dumpster import deprecated


@frappe.request_cache
@deprecated
def has_legacy_batch_ledgers(item_code: str, warehouse: str) -> bool:
	"""`False` when no Stock Ledger Entry of the item and warehouse uses the
	denormalized `batch_no` field.

	Batches are tracked through the Serial and Batch Bundle since v15, so this is
	`False` for most of the item and warehouse combinations and the expensive
	aggregates (`FOR UPDATE`) below can be skipped without reading the ledger. The
	probe is an index only scan on the `batch_no, item_code, warehouse` index,
	`is_cancelled` is intentionally left out of it to keep it so, an item with only
	cancelled legacy ledgers simply falls back to the aggregate.

	Cached for the request, nothing creates a legacy ledger midway.
	"""

	sle = frappe.qb.DocType("Stock Ledger Entry")

	return bool(
		frappe.qb.from_(sle)
		.select(sle.batch_no)
		.where(
			sle.batch_no.isnotnull()
			& (sle.batch_no != "")
			& (sle.item_code == item_code)
			& (sle.warehouse == warehouse)
		)
		.limit(1)
		.run()
	)


class DeprecatedSerialNoValuation:
	@deprecated(
		"erpnext.stock.serial_batch_bundle.SerialNoValuation.calculate_stock_value_from_deprecarated_ledgers",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def calculate_stock_value_from_deprecarated_ledgers(self):
		serial_nos = []
		if hasattr(self, "old_serial_nos"):
			serial_nos = self.old_serial_nos

		if not serial_nos:
			return

		stock_value_change = 0
		if not self.sle.is_cancelled:
			stock_value_change = self.get_incoming_value_for_serial_nos(serial_nos)

		self.stock_value_change += flt(stock_value_change)

	@deprecated(
		"erpnext.stock.serial_batch_bundle.SerialNoValuation.get_incoming_value_for_serial_nos",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def get_incoming_value_for_serial_nos(self, serial_nos):
		from erpnext.stock.utils import get_combine_datetime

		# get rate from serial nos within same company
		incoming_values = 0.0
		posting_datetime = self.sle.posting_datetime

		if not posting_datetime and self.sle.posting_date:
			posting_datetime = get_combine_datetime(self.sle.posting_date, self.sle.posting_time)

		do_not_fetch_rate = frappe.db.get_single_value(
			"Stock Reposting Settings", "do_not_fetch_incoming_rate_from_serial_no"
		)

		for serial_no in serial_nos:
			sn_details = frappe.db.get_value("Serial No", serial_no, ["purchase_rate", "company"], as_dict=1)
			if (
				sn_details
				and sn_details.purchase_rate
				and sn_details.company == self.sle.company
				and (not frappe.flags.through_repost_item_valuation or not do_not_fetch_rate)
			):
				self.serial_no_incoming_rate[serial_no] += flt(sn_details.purchase_rate)
				incoming_values += self.serial_no_incoming_rate[serial_no]
				continue

			for sle in self.get_last_inward_sle_for_serial_no(serial_no, posting_datetime):
				self.serial_no_incoming_rate[serial_no] += flt(sle.incoming_rate)
				incoming_values += self.serial_no_incoming_rate[serial_no]

		return incoming_values

	def get_last_inward_sle_for_serial_no(self, serial_no, posting_datetime):
		table = frappe.qb.DocType("Stock Ledger Entry")

		query = (
			frappe.qb.from_(table)
			.select(table.incoming_rate, table.actual_qty, table.stock_value_difference)
			.where(
				(table.item_code == self.sle.item_code)
				& (table.company == self.sle.company)
				& (table.warehouse == self.sle.warehouse)
				& (table.posting_datetime <= posting_datetime)
				& (table.is_cancelled == 0)
				& (table.actual_qty > 0)
				& (table.serial_and_batch_bundle.isnull())
				& (Locate(serial_no, table.serial_no) > 0)
				& (Locate(f"\n{serial_no}\n", Concat("\n", table.serial_no, "\n")) > 0)
			)
			.orderby(table.posting_datetime, order=Order.desc)
			.orderby(table.creation, order=Order.desc)
			.limit(1)
		)

		if frappe.db.db_type == "mariadb":
			query = query.force_index("item_code_warehouse_posting_datetime_creation_index")

		return query.run(as_dict=1)


class DeprecatedBatchNoValuation:
	@deprecated(
		"erpnext.stock.serial_batch_bundle.BatchNoValuation.calculate_avg_rate_from_deprecarated_ledgers",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def calculate_avg_rate_from_deprecarated_ledgers(self):
		entries = self.get_sle_for_batches()
		for ledger in entries:
			self.stock_value_differece[ledger.batch_no] += flt(ledger.batch_value)
			self.available_qty[ledger.batch_no] += flt(ledger.batch_qty)

	@deprecated(
		"erpnext.stock.serial_batch_bundle.BatchNoValuation.get_sle_for_batches",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def get_sle_for_batches(self):
		from erpnext.stock.utils import get_combine_datetime

		if not self.batchwise_valuation_batches or not has_legacy_batch_ledgers(
			self.sle.item_code, self.sle.warehouse
		):
			return []

		sle = frappe.qb.DocType("Stock Ledger Entry")

		timestamp_condition = None
		if self.sle.posting_datetime:
			posting_datetime = self.sle.posting_datetime
			if not self.sle.creation:
				posting_datetime = posting_datetime + datetime.timedelta(milliseconds=1)

			timestamp_condition = sle.posting_datetime < posting_datetime

			if self.sle.creation:
				timestamp_condition |= (sle.posting_datetime == posting_datetime) & (
					sle.creation < self.sle.creation
				)

		query = (
			frappe.qb.from_(sle)
			.select(
				sle.batch_no,
				Sum(sle.stock_value_difference).as_("batch_value"),
				Sum(sle.actual_qty).as_("batch_qty"),
			)
			.where(
				(sle.item_code == self.sle.item_code)
				& (sle.warehouse == self.sle.warehouse)
				& (sle.batch_no.isin(self.batchwise_valuation_batches))
				& (sle.batch_no.isnotnull())
				& (sle.is_cancelled == 0)
			)
			.for_update()
			.groupby(sle.batch_no)
		)

		if timestamp_condition:
			query = query.where(timestamp_condition)

		if self.sle.name:
			query = query.where(sle.name != self.sle.name)

		if getattr(self, "stock_closing_from_datetime", None):
			query = query.where(sle.posting_datetime >= self.stock_closing_from_datetime)

		return query.run(as_dict=True)

	@deprecated(
		"erpnext.stock.serial_batch_bundle.BatchNoValuation.calculate_avg_rate_for_non_batchwise_valuation",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def calculate_avg_rate_for_non_batchwise_valuation(self):
		if not self.non_batchwise_valuation_batches:
			return

		self.non_batchwise_balance_value = defaultdict(float)
		self.non_batchwise_balance_qty = defaultdict(float)

		self.set_balance_value_for_non_batchwise_valuation_batches()

		fallback_rate = self.get_pooled_fallback_rate()

		for batch_no, ledger in self.batch_nos.items():
			if batch_no not in self.non_batchwise_valuation_batches:
				continue

			self.batch_avg_rate[batch_no] = self.get_non_batchwise_avg_rate(batch_no, fallback_rate)
			self.stock_value_differece[batch_no] = flt(self.non_batchwise_balance_value.get(batch_no))

			stock_value_change = self.batch_avg_rate[batch_no] * ledger.qty
			self.stock_value_change += stock_value_change

			# ledger.qty is negative for outward entries, so adding drains the pool
			self.non_batchwise_balance_value[batch_no] += stock_value_change
			self.non_batchwise_balance_qty[batch_no] += ledger.qty

			# on the legacy batch_no field path the ledger is the Stock Ledger Entry itself,
			# so there is no Serial and Batch Entry row to write the rate back to
			if not self.sle.get("serial_and_batch_bundle") or not ledger.get("name"):
				continue

			frappe.db.set_value(
				"Serial and Batch Entry",
				ledger.name,
				{
					"stock_value_difference": stock_value_change,
					# every reader of incoming_rate takes abs(), keep the stored value in step
					"incoming_rate": abs(self.batch_avg_rate[batch_no]),
				},
			)

	def get_non_batchwise_avg_rate(self, batch_no, fallback_rate):
		balance_qty = flt(self.non_batchwise_balance_qty.get(batch_no))
		balance_value = flt(self.non_batchwise_balance_value.get(batch_no))

		# The value and the qty of a batch are summed independently over its whole history
		# and the two can drift apart: outward entries posted before batch level valuation
		# existed were priced at the pooled warehouse rate, and a Stock Reconciliation posts
		# value with no matching qty. A drained or a negative pool would otherwise yield a
		# negative or an exploding rate, which is read back as abs() by the callers and
		# silently overdraws the warehouse stock value.
		if balance_qty > 0 and balance_value > 0:
			return balance_value / balance_qty

		return fallback_rate

	def get_pooled_fallback_rate(self):
		"""Moving average rate of the stock that is not valued batch wise.

		`last_sle` carries the balance of the whole warehouse, so the batches that are
		valued batch wise have to be netted off before it can price the ones that are not.
		"""
		last_sle = self.last_sle or frappe._dict()

		total_qty = flt(last_sle.qty_after_transaction)
		total_value = flt(last_sle.stock_value)

		qty, value = total_qty, total_value
		for batch_no in self.batchwise_valuation_batches:
			qty -= flt(self.available_qty.get(batch_no))
			value -= flt(self.stock_value_differece.get(batch_no))

		if qty > 0 and value > 0:
			return value / qty

		# The batchwise batches can account for more than the warehouse holds when the
		# legacy ledger is itself inconsistent, which is what an overdrawn history leaves
		# behind. The plain warehouse rate is then the best basis left.
		if total_qty > 0 and total_value > 0:
			return total_value / total_qty

		return 0.0

	@deprecated(
		"erpnext.stock.serial_batch_bundle.BatchNoValuation.set_balance_value_for_non_batchwise_valuation_batches",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def set_balance_value_for_non_batchwise_valuation_batches(self):
		if hasattr(self, "prev_sle"):
			self.last_sle = self.prev_sle
		else:
			self.last_sle = self.get_last_sle_for_non_batch()

		if self.last_sle and self.last_sle.stock_queue:
			self.stock_queue = self.last_sle.stock_queue
			if isinstance(self.stock_queue, str):
				self.stock_queue = json.loads(self.stock_queue) or []

		self.set_balance_value_from_sl_entries()
		self.set_balance_value_from_bundle()

	@deprecated(
		"erpnext.stock.serial_batch_bundle.BatchNoValuation.set_balance_value_from_sl_entries",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def set_balance_value_from_sl_entries(self) -> None:
		from erpnext.stock.utils import get_combine_datetime

		if not has_legacy_batch_ledgers(self.sle.item_code, self.sle.warehouse):
			return

		sle = frappe.qb.DocType("Stock Ledger Entry")
		batch = frappe.qb.DocType("Batch")

		posting_datetime = self.sle.posting_datetime

		if not posting_datetime and self.sle.posting_date:
			posting_datetime = get_combine_datetime(self.sle.posting_date, self.sle.posting_time)

		if not self.sle.creation:
			posting_datetime = posting_datetime + datetime.timedelta(milliseconds=1)

		timestamp_condition = sle.posting_datetime < posting_datetime

		if self.sle.creation:
			timestamp_condition |= (sle.posting_datetime == posting_datetime) & (
				sle.creation < self.sle.creation
			)

		query = (
			frappe.qb.from_(sle)
			.inner_join(batch)
			.on(sle.batch_no == batch.name)
			.select(
				sle.batch_no,
				Sum(sle.actual_qty).as_("batch_qty"),
				Sum(sle.stock_value_difference).as_("batch_value"),
			)
			.where(
				(sle.item_code == self.sle.item_code)
				& (sle.warehouse == self.sle.warehouse)
				& (sle.batch_no.isnotnull())
				& (sle.is_cancelled == 0)
				& (sle.batch_no.isin(self.non_batchwise_valuation_batches))
			)
			.for_update()
			.where(timestamp_condition)
			.groupby(sle.batch_no)
		)

		if self.sle.name:
			query = query.where(sle.name != self.sle.name)

		# Moving Average items with no Use Batch wise Valuation but want to use batch wise valuation
		moving_avg_item_non_batch_value = self.use_batch_pool_for_moving_average()
		if moving_avg_item_non_batch_value:
			query = query.where(batch.use_batchwise_valuation == 0)

		batch_data = query.run(as_dict=True)
		for d in batch_data:
			self.available_qty[d.batch_no] += flt(d.batch_qty)
			if moving_avg_item_non_batch_value:
				self.non_batchwise_balance_qty[d.batch_no] += flt(d.batch_qty)
				self.non_batchwise_balance_value[d.batch_no] += flt(d.batch_value)

		if moving_avg_item_non_batch_value:
			return

		for d in batch_data:
			if self.available_qty.get(d.batch_no):
				self.non_batchwise_balance_value[d.batch_no] += flt(self.last_sle.stock_value)
				self.non_batchwise_balance_qty[d.batch_no] += flt(self.last_sle.qty_after_transaction)

	def get_last_sle_for_non_batch(self):
		from erpnext.stock.utils import get_combine_datetime

		sle = frappe.qb.DocType("Stock Ledger Entry")

		posting_datetime = self.sle.posting_datetime
		if not posting_datetime and self.sle.posting_date:
			posting_datetime = get_combine_datetime(self.sle.posting_date, self.sle.posting_time)

		if not self.sle.creation:
			posting_datetime = posting_datetime + datetime.timedelta(milliseconds=1)

		timestamp_condition = sle.posting_datetime < posting_datetime

		if self.sle.creation:
			timestamp_condition |= (sle.posting_datetime == posting_datetime) & (
				sle.creation < self.sle.creation
			)

		query = (
			frappe.qb.from_(sle)
			.select(
				sle.stock_value,
				sle.qty_after_transaction,
				sle.stock_queue,
			)
			.where(
				(sle.item_code == self.sle.item_code)
				& (sle.warehouse == self.sle.warehouse)
				& (sle.is_cancelled == 0)
			)
			.where(timestamp_condition)
			.orderby(sle.posting_datetime, order=Order.desc)
			.orderby(sle.creation, order=Order.desc)
			.for_update()
			.limit(1)
		)

		if self.sle.name:
			query = query.where(sle.name != self.sle.name)

		if self.sle.serial_and_batch_bundle:
			query = query.where(Coalesce(sle.serial_and_batch_bundle, "") != self.sle.serial_and_batch_bundle)

		data = query.run(as_dict=True)

		return data[0] if data else frappe._dict()

	@deprecated(
		"erpnext.stock.serial_batch_bundle.BatchNoValuation.set_balance_value_from_bundle",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def set_balance_value_from_bundle(self) -> None:
		from erpnext.stock.utils import get_combine_datetime

		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		bundle_child = frappe.qb.DocType("Serial and Batch Entry")
		batch = frappe.qb.DocType("Batch")

		posting_datetime = self.sle.posting_datetime
		if not posting_datetime and self.sle.posting_date:
			posting_datetime = get_combine_datetime(self.sle.posting_date, self.sle.posting_time)

		sle_creation = self.sle.creation
		if not sle_creation and self.sle.get("serial_and_batch_bundle"):
			sle_creation = frappe.db.get_value(
				"Stock Ledger Entry",
				{"serial_and_batch_bundle": self.sle.serial_and_batch_bundle, "is_cancelled": 0},
				"creation",
			)

		if not sle_creation:
			# the current entry is not in the ledger yet, so it sorts after everything posted
			# at the same instant; nudge the boundary to take them in, the same way
			# set_balance_value_from_sl_entries does, otherwise the two halves of one bundle
			# are summed as of two different points in time
			posting_datetime = posting_datetime + datetime.timedelta(milliseconds=1)

		timestamp_condition = bundle.posting_datetime < posting_datetime

		if sle_creation:
			sle_table = frappe.qb.DocType("Stock Ledger Entry")

			# bundle creation and SLE creation are different timelines (a bundle can be
			# created much before its SLE), so break the tie on the creation of the
			# bundle's own SLE, exactly like BatchNoValuation.get_batch_stock_before_date
			timestamp_condition |= (bundle.posting_datetime == posting_datetime) & ExistsCriterion(
				frappe.qb.from_(sle_table)
				.select(sle_table.name)
				.where(
					(sle_table.serial_and_batch_bundle == bundle.name)
					& (sle_table.is_cancelled == 0)
					& (sle_table.creation < sle_creation)
				)
			)

		query = (
			frappe.qb.from_(bundle)
			.inner_join(bundle_child)
			.on(bundle.name == bundle_child.parent)
			.inner_join(batch)
			.on(bundle_child.batch_no == batch.name)
			.select(
				bundle_child.batch_no,
				Sum(bundle_child.qty).as_("batch_qty"),
				Sum(bundle_child.stock_value_difference).as_("batch_value"),
			)
			.where(
				(bundle.item_code == self.sle.item_code)
				& (bundle.warehouse == self.sle.warehouse)
				& (bundle_child.batch_no.isnotnull())
				& (bundle.is_cancelled == 0)
				& (bundle.docstatus == 1)
				& (bundle.type_of_transaction.isin(["Inward", "Outward"]))
				& (bundle_child.batch_no.isin(self.non_batchwise_valuation_batches))
			)
			.for_update()
			.where(timestamp_condition)
			.groupby(bundle_child.batch_no)
		)

		if self.sle.serial_and_batch_bundle:
			query = query.where(bundle.name != self.sle.serial_and_batch_bundle)

		query = query.where(bundle.voucher_type != "Pick List")

		# Moving Average items with no Use Batch wise Valuation but want to use batch wise valuation
		moving_avg_item_non_batch_value = self.use_batch_pool_for_moving_average()
		if moving_avg_item_non_batch_value:
			query = query.where(batch.use_batchwise_valuation == 0)

		batch_data = query.run(as_dict=True)
		for d in batch_data:
			self.available_qty[d.batch_no] += flt(d.batch_qty)
			if moving_avg_item_non_batch_value:
				self.non_batchwise_balance_qty[d.batch_no] += flt(d.batch_qty)
				self.non_batchwise_balance_value[d.batch_no] += flt(d.batch_value)

		if moving_avg_item_non_batch_value:
			return

		if not self.last_sle:
			return

		for batch_no in self.available_qty:
			self.non_batchwise_balance_value[batch_no] = flt(self.last_sle.stock_value)
			self.non_batchwise_balance_qty[batch_no] = flt(self.last_sle.qty_after_transaction)

	def get_valuation_method(self, item_code):
		from erpnext.stock.utils import get_valuation_method

		return get_valuation_method(item_code, self.sle.company)

	def use_batch_pool_for_moving_average(self):
		if not hasattr(self, "_use_batch_pool_for_moving_average"):
			self._use_batch_pool_for_moving_average = self.get_valuation_method(
				self.sle.item_code
			) == "Moving Average" and not frappe.get_single_value(
				"Stock Settings", "do_not_use_batchwise_valuation"
			)

		return self._use_batch_pool_for_moving_average
