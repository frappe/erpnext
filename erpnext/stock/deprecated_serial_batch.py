import datetime
import json
from collections import defaultdict

import frappe
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import flt, nowtime
from pypika import Order
from pypika.functions import Coalesce

from erpnext.deprecation_dumpster import deprecated


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

		for serial_no in serial_nos:
			sn_details = frappe.db.get_value("Serial No", serial_no, ["purchase_rate", "company"], as_dict=1)
			if sn_details and sn_details.purchase_rate and sn_details.company == self.sle.company:
				self.serial_no_incoming_rate[serial_no] += flt(sn_details.purchase_rate)
				incoming_values += self.serial_no_incoming_rate[serial_no]
				continue

			table = frappe.qb.DocType("Stock Ledger Entry")
			stock_ledgers = (
				frappe.qb.from_(table)
				.select(table.incoming_rate, table.actual_qty, table.stock_value_difference)
				.where(
					(
						(table.serial_no == serial_no)
						| (table.serial_no.like(serial_no + "\n%"))
						| (table.serial_no.like("%\n" + serial_no))
						| (table.serial_no.like("%\n" + serial_no + "\n%"))
					)
					& (table.company == self.sle.company)
					& (table.warehouse == self.sle.warehouse)
					& (table.serial_and_batch_bundle.isnull())
					& (table.actual_qty > 0)
					& (table.is_cancelled == 0)
					& table.posting_datetime
					<= posting_datetime
				)
				.orderby(table.posting_datetime, order=Order.desc)
				.limit(1)
			).run(as_dict=1)

			for sle in stock_ledgers:
				self.serial_no_incoming_rate[serial_no] += flt(sle.incoming_rate)
				incoming_values += self.serial_no_incoming_rate[serial_no]

		return incoming_values


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
			self.total_qty[ledger.batch_no] += flt(ledger.batch_qty)

	@deprecated(
		"erpnext.stock.serial_batch_bundle.BatchNoValuation.get_sle_for_batches",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def get_sle_for_batches(self):
		from erpnext.stock.utils import get_combine_datetime

		if not self.batchwise_valuation_batches:
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

		for batch_no, ledger in self.batch_nos.items():
			if batch_no not in self.non_batchwise_valuation_batches:
				continue

			if not self.non_batchwise_balance_qty:
				continue

			if not self.non_batchwise_balance_qty.get(batch_no):
				self.batch_avg_rate[batch_no] = 0.0
				self.stock_value_differece[batch_no] = 0.0
			else:
				self.batch_avg_rate[batch_no] = (
					self.non_batchwise_balance_value[batch_no] / self.non_batchwise_balance_qty[batch_no]
				)
				self.stock_value_differece[batch_no] = self.non_batchwise_balance_value

			stock_value_change = self.batch_avg_rate[batch_no] * ledger.qty
			self.stock_value_change += stock_value_change

			self.non_batchwise_balance_value[batch_no] -= stock_value_change
			self.non_batchwise_balance_qty[batch_no] -= ledger.qty

			frappe.db.set_value(
				"Serial and Batch Entry",
				ledger.name,
				{
					"stock_value_difference": stock_value_change,
					"incoming_rate": self.batch_avg_rate[batch_no],
				},
			)

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

		batch_data = query.run(as_dict=True)
		for d in batch_data:
			self.available_qty[d.batch_no] += flt(d.batch_qty)
			self.total_qty[d.batch_no] += flt(d.batch_qty)

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

		timestamp_condition = bundle.posting_datetime < posting_datetime

		if self.sle.creation:
			timestamp_condition |= (bundle.posting_datetime == posting_datetime) & (
				bundle.creation < self.sle.creation
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

		batch_data = query.run(as_dict=True)
		for d in batch_data:
			self.available_qty[d.batch_no] += flt(d.batch_qty)
			self.total_qty[d.batch_no] += flt(d.batch_qty)

		if not self.last_sle:
			return

		for batch_no in self.available_qty:
			self.non_batchwise_balance_value[batch_no] = flt(self.last_sle.stock_value)
			self.non_batchwise_balance_qty[batch_no] = flt(self.last_sle.qty_after_transaction)
