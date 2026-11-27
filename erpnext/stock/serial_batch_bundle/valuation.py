from collections import defaultdict

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, create_batch, flt, getdate
from pypika import Order
from pypika.terms import ExistsCriterion

from erpnext.stock.serial_batch_bundle.bundle_entries import get_batch_nos, get_serial_nos
from erpnext.stock.serial_batch_bundle.legacy_valuation import (
	DeprecatedBatchNoValuation,
	DeprecatedSerialNoValuation,
)
from erpnext.stock.valuation import round_off_if_near_zero

SERIAL_NO_QUERY_BATCH_SIZE = 500


class SerialNoValuation(DeprecatedSerialNoValuation):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.calculate_stock_value_change()
		self.calculate_valuation_rate()

	def calculate_stock_value_change(self):
		if flt(self.sle.actual_qty) > 0:
			self.stock_value_change = frappe.get_cached_value(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle, "total_amount"
			)

		else:
			self.serial_no_incoming_rate = defaultdict(float)
			self.stock_value_change = 0.0
			self.old_serial_nos = []

			serial_nos = self.get_serial_nos()
			if not serial_nos:
				return

			result = self.get_serial_no_wise_incoming_rate(serial_nos)
			for serial_no in serial_nos:
				incoming_rate = result.get(serial_no)
				if incoming_rate is None:
					self.old_serial_nos.append(serial_no)
					continue

				self.stock_value_change += incoming_rate
				self.serial_no_incoming_rate[serial_no] += incoming_rate

			self.calculate_stock_value_from_deprecarated_ledgers()

	def get_serial_no_wise_incoming_rate(self, serial_nos):
		bundle_child = frappe.qb.DocType("Serial and Batch Entry")
		posted_before_condition = None
		if self.sle.posting_datetime:
			posted_before_condition = get_posted_before_sle_condition(self.sle, bundle_child)

		incoming_rates = frappe._dict()
		for serial_nos_batch in create_batch(serial_nos, SERIAL_NO_QUERY_BATCH_SIZE):
			for serial_no, warehouse, incoming_rate in self.get_inward_serial_no_rates(
				serial_nos_batch, bundle_child, posted_before_condition
			):
				if warehouse == self.sle.warehouse:
					incoming_rates.setdefault(serial_no, incoming_rate)

		return incoming_rates

	def get_inward_serial_no_rates(self, serial_nos, bundle_child, posted_before_condition):
		query = (
			frappe.qb.from_(bundle_child)
			.select(bundle_child.serial_no, bundle_child.warehouse, bundle_child.incoming_rate)
			.where(
				(bundle_child.serial_no.isin(serial_nos))
				& (bundle_child.item_code == self.sle.item_code)
				& (bundle_child.is_cancelled == 0)
				& (bundle_child.docstatus == 1)
				& (bundle_child.type_of_transaction == "Inward")
				& (bundle_child.qty > 0)
			)
			.orderby(bundle_child.posting_datetime, order=Order.desc)
			.orderby(bundle_child.creation, order=Order.desc)
		)

		if self.sle.voucher_no:
			query = query.where(bundle_child.voucher_no != self.sle.voucher_no)

		if posted_before_condition:
			query = query.where(posted_before_condition)

		return query.run()

	def get_serial_nos(self):
		if self.sle.get("serial_nos"):
			return self.sle.serial_nos

		return get_serial_nos(self.sle.serial_and_batch_bundle)

	def calculate_valuation_rate(self):
		if not hasattr(self, "wh_data"):
			return

		new_stock_qty = self.wh_data.qty_after_transaction + self.sle.actual_qty

		if new_stock_qty > 0:
			new_stock_value = (
				self.wh_data.qty_after_transaction * self.wh_data.valuation_rate
			) + self.stock_value_change
			if new_stock_value >= 0:
				# calculate new valuation rate only if stock value is positive
				# else it remains the same as that of previous entry
				self.wh_data.valuation_rate = new_stock_value / new_stock_qty

		if not self.wh_data.valuation_rate and self.sle.voucher_detail_no and not self.is_rejected_entry():
			allow_zero_rate = self.sle_self.check_if_allow_zero_valuation_rate(
				self.sle.voucher_type, self.sle.voucher_detail_no
			)
			if not allow_zero_rate:
				self.wh_data.valuation_rate = self.sle_self.get_fallback_rate(self.sle)

		self.wh_data.qty_after_transaction += self.sle.actual_qty
		self.wh_data.stock_value = flt(self.wh_data.qty_after_transaction) * flt(self.wh_data.valuation_rate)

	def is_rejected_entry(self):
		return is_rejected(self.sle.voucher_type, self.sle.voucher_detail_no, self.sle.warehouse)

	def get_incoming_rate(self):
		if not self.sle.actual_qty and self.sle.voucher_type == "Stock Reconciliation":
			return 0.0

		return abs(flt(self.stock_value_change) / flt(self.sle.actual_qty))

	def get_incoming_rate_of_serial_no(self, serial_no):
		return self.serial_no_incoming_rate.get(serial_no, 0.0)


class BatchNoValuation(DeprecatedBatchNoValuation):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.total_qty = defaultdict(float)
		self.stock_queue = []
		self.batch_nos = self.get_batch_nos()
		self.prepare_batches()
		self.calculate_avg_rate()
		self.calculate_valuation_rate()

	def calculate_avg_rate(self):
		if flt(self.sle.actual_qty) > 0:
			self.stock_value_change = frappe.get_cached_value(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle, "total_amount"
			)
		else:
			self.stock_value_change = 0.0
			self.batch_avg_rate = defaultdict(float)
			self.available_qty = defaultdict(float)
			self.stock_value_differece = defaultdict(float)

			self.seed_from_stock_closing_balance()

			for ledger in self.get_batch_stock_before_date():
				self.stock_value_differece[ledger.batch_no] += flt(ledger.incoming_rate)
				self.available_qty[ledger.batch_no] += flt(ledger.qty)

			self.calculate_avg_rate_from_deprecarated_ledgers()
			self.calculate_avg_rate_for_non_batchwise_valuation()
			self.set_stock_value_difference()

	def seed_from_stock_closing_balance(self):
		self.stock_closing_from_datetime = None
		closing_entry = self.get_closing_entry_for_seeding()
		if not closing_entry:
			return

		from erpnext.stock.utils import get_combine_datetime

		self.stock_closing_from_datetime = get_combine_datetime(
			add_days(closing_entry.to_date, 1), "00:00:00"
		)

		for row in self.get_stock_closing_balance_entries(closing_entry.name):
			self.stock_value_differece[row.batch_no] += flt(row.stock_value_difference)
			self.available_qty[row.batch_no] += flt(row.actual_qty)

	def get_closing_entry_for_seeding(self):
		from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
			get_closing_entry_for_closed_period,
		)

		if not self.batchwise_valuation_batches or not self.sle.posting_date:
			return None

		company = self.sle.company or frappe.get_cached_value("Warehouse", self.sle.warehouse, "company")
		closing_entry = get_closing_entry_for_closed_period(company)
		if not closing_entry or getdate(self.sle.posting_date) <= getdate(closing_entry.to_date):
			return None

		return closing_entry

	def get_stock_closing_balance_entries(self, closing_entry):
		table = frappe.qb.DocType("Stock Closing Balance")

		return (
			frappe.qb.from_(table)
			.select(table.batch_no, table.actual_qty, table.stock_value_difference)
			.where(
				(table.stock_closing_entry == closing_entry)
				& (table.item_code == self.sle.item_code)
				& (table.warehouse == self.sle.warehouse)
				& table.batch_no.isin(self.batchwise_valuation_batches)
				& (table.inventory_dimension_key.isnull() | (table.inventory_dimension_key == ""))
			)
		).run(as_dict=True)

	def get_batch_stock_before_date(self) -> list[dict]:
		# Get batch wise stock value difference from Serial and Batch Bundle considering time condition
		if not self.batchwise_valuation_batches:
			return []

		child = frappe.qb.DocType("Serial and Batch Entry")

		timestamp_condition = ""
		if self.sle.posting_datetime:
			timestamp_condition = get_posted_before_sle_condition(self.sle, child)

		conditions = (
			(child.item_code == self.sle.item_code)
			& (child.warehouse == self.sle.warehouse)
			& (child.batch_no.isin(self.batchwise_valuation_batches))
			& (child.docstatus == 1)
			& (child.is_cancelled == 0)
			& (child.type_of_transaction.isin(["Inward", "Outward"]))
		)

		# Important to exclude the current voucher detail no / voucher no to calculate the correct stock value difference
		if self.sle.voucher_detail_no:
			conditions &= child.voucher_detail_no != self.sle.voucher_detail_no
		elif self.sle.voucher_no:
			conditions &= child.voucher_no != self.sle.voucher_no

		conditions &= child.voucher_type != "Pick List"
		if timestamp_condition:
			conditions &= timestamp_condition

		if self.stock_closing_from_datetime:
			conditions &= child.posting_datetime >= self.stock_closing_from_datetime

		query = (
			frappe.qb.from_(child)
			.select(
				child.batch_no,
				Sum(child.stock_value_difference).as_("incoming_rate"),
				Sum(child.qty).as_("qty"),
			)
			.where(conditions)
			.groupby(child.batch_no)
		)
		if frappe.db.db_type != "postgres":
			query = query.for_update()

		return query.run(as_dict=True)

	def prepare_batches(self):
		from erpnext.stock.utils import get_valuation_method

		self.batches = self.batch_nos
		if isinstance(self.batch_nos, dict):
			self.batches = list(self.batch_nos.keys())

		self.batchwise_valuation_batches = []
		self.non_batchwise_valuation_batches = []

		if batchwise_batches := self.sle.get("batchwise_valuation_batches"):
			self.batchwise_valuation_batches = list(batchwise_batches)
			self.non_batchwise_valuation_batches = list(set(self.batches) - set(batchwise_batches))
			return

		if get_valuation_method(
			self.sle.item_code, self.sle.company
		) == "Moving Average" and frappe.get_single_value("Stock Settings", "do_not_use_batchwise_valuation"):
			self.non_batchwise_valuation_batches = self.batches
			return

		batches = frappe.get_all(
			"Batch", filters={"name": ("in", self.batches), "use_batchwise_valuation": 1}, fields=["name"]
		)

		for batch in batches:
			self.batchwise_valuation_batches.append(batch.name)

		self.non_batchwise_valuation_batches = list(set(self.batches) - set(self.batchwise_valuation_batches))

	def get_batch_nos(self) -> list:
		if self.sle.get("batch_nos"):
			return self.sle.batch_nos

		return get_batch_nos(self.sle.serial_and_batch_bundle)

	def set_stock_value_difference(self):
		for batch_no, ledger in self.batch_nos.items():
			if batch_no in self.non_batchwise_valuation_batches:
				continue

			if not self.available_qty[batch_no]:
				continue

			self.batch_avg_rate[batch_no] = (
				self.stock_value_differece[batch_no] / self.available_qty[batch_no]
			)

			# New Stock Value Difference
			stock_value_change = self.batch_avg_rate[batch_no] * ledger.qty
			self.stock_value_change += stock_value_change

	def calculate_valuation_rate(self):
		if not hasattr(self, "wh_data"):
			return

		self.wh_data.stock_value = round_off_if_near_zero(self.wh_data.stock_value + self.stock_value_change)

		self.wh_data.qty_after_transaction += self.sle.actual_qty
		if self.wh_data.qty_after_transaction:
			self.wh_data.valuation_rate = self.wh_data.stock_value / self.wh_data.qty_after_transaction

	def get_incoming_rate(self):
		if not self.sle.actual_qty:
			self.sle.actual_qty = self.get_actual_qty()

		if not self.sle.actual_qty:
			return 0.0

		return abs(flt(self.stock_value_change) / flt(self.sle.actual_qty))

	def get_actual_qty(self):
		total_qty = 0.0
		for batch_no in self.available_qty:
			total_qty += self.available_qty[batch_no]

		return total_qty


def get_posted_before_sle_condition(sle, bundle_child):
	"""Bundle entries posted before the SLE; on the same posting datetime, those whose own SLE was created earlier."""
	sle_creation = sle.creation if sle.get("name") else None
	if not sle.get("name") and sle.get("serial_and_batch_bundle"):
		sle_creation = frappe.db.get_value(
			"Stock Ledger Entry",
			{"serial_and_batch_bundle": sle.serial_and_batch_bundle, "is_cancelled": 0},
			"creation",
		)

	sle_table = frappe.qb.DocType("Stock Ledger Entry")
	bundle_sle_exists = (sle_table.serial_and_batch_bundle == bundle_child.parent) & (
		sle_table.is_cancelled == 0
	)
	if sle_creation:
		bundle_sle_exists &= sle_table.creation < sle_creation

	tie_condition = ExistsCriterion(
		frappe.qb.from_(sle_table).select(sle_table.name).where(bundle_sle_exists)
	)

	return (bundle_child.posting_datetime < sle.posting_datetime) | (
		(bundle_child.posting_datetime == sle.posting_datetime) & tie_condition
	)


def is_rejected(voucher_type, voucher_detail_no, warehouse):
	if voucher_type in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
		return warehouse == frappe.get_cached_value(
			voucher_type + " Item", voucher_detail_no, "rejected_warehouse"
		)

	return False
