import frappe
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import flt
from frappe.utils.deprecations import deprecated
from pypika import Order


class DeprecatedSerialNoValuation:
	@deprecated
	def calculate_stock_value_from_deprecarated_ledgers(self):
		serial_nos = list(
			filter(lambda x: x not in self.serial_no_incoming_rate and x, self.get_serial_nos())
		)

		actual_qty = flt(self.sle.actual_qty)

		stock_value_change = 0
		if actual_qty < 0:
			if not self.sle.is_cancelled:
				outgoing_value = self.get_incoming_value_for_serial_nos(serial_nos)
				stock_value_change = -1 * outgoing_value

		self.stock_value_change += stock_value_change

	@deprecated
	def get_incoming_value_for_serial_nos(self, serial_nos):
		# get rate from serial nos within same company
		all_serial_nos = frappe.get_all(
			"Serial No", fields=["purchase_rate", "name", "company"], filters={"name": ("in", serial_nos)}
		)

		incoming_values = 0.0
		for d in all_serial_nos:
			if d.company == self.sle.company:
				self.serial_no_incoming_rate[d.name] += flt(d.purchase_rate)
				incoming_values += flt(d.purchase_rate)

		# Get rate for serial nos which has been transferred to other company
		invalid_serial_nos = [d.name for d in all_serial_nos if d.company != self.sle.company]
		for serial_no in invalid_serial_nos:
			table = frappe.qb.DocType("Stock Ledger Entry")
			incoming_rate = (
				frappe.qb.from_(table)
				.select(table.incoming_rate)
				.where(
					(
						(table.serial_no == serial_no)
						| (table.serial_no.like(serial_no + "\n%"))
						| (table.serial_no.like("%\n" + serial_no))
						| (table.serial_no.like("%\n" + serial_no + "\n%"))
					)
					& (table.company == self.sle.company)
					& (table.serial_and_batch_bundle.isnull())
					& (table.actual_qty > 0)
					& (table.is_cancelled == 0)
				)
				.orderby(table.posting_date, order=Order.desc)
				.limit(1)
			).run()

			self.serial_no_incoming_rate[serial_no] += flt(incoming_rate[0][0]) if incoming_rate else 0
			incoming_values += self.serial_no_incoming_rate[serial_no]

		return incoming_values


class DeprecatedBatchNoValuation:
	@deprecated
	def calculate_avg_rate_from_deprecarated_ledgers(self):
		entries = self.get_sle_for_batches()
		for ledger in entries:
			self.stock_value_differece[ledger.batch_no] += flt(ledger.batch_value)
			self.available_qty[ledger.batch_no] += flt(ledger.batch_qty)

	@deprecated
	def get_sle_for_batches(self):
		if not self.batchwise_valuation_batches:
			return []

		sle = frappe.qb.DocType("Stock Ledger Entry")

		timestamp_condition = CombineDatetime(sle.posting_date, sle.posting_time) < CombineDatetime(
			self.sle.posting_date, self.sle.posting_time
		)
		if self.sle.creation:
			timestamp_condition |= (
				CombineDatetime(sle.posting_date, sle.posting_time)
				== CombineDatetime(self.sle.posting_date, self.sle.posting_time)
			) & (sle.creation < self.sle.creation)

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
			.where(timestamp_condition)
			.groupby(sle.batch_no)
		)

		if self.sle.name:
			query = query.where(sle.name != self.sle.name)

		return query.run(as_dict=True)

	@deprecated
	def calculate_avg_rate_for_non_batchwise_valuation(self):
		if not self.non_batchwise_valuation_batches:
			return

		self.non_batchwise_balance_value = 0.0
		self.non_batchwise_balance_qty = 0.0

		self.set_balance_value_for_non_batchwise_valuation_batches()

		for batch_no, ledger in self.batch_nos.items():
			if batch_no not in self.non_batchwise_valuation_batches:
				continue

			if not self.non_batchwise_balance_qty:
				continue

			self.batch_avg_rate[batch_no] = (
				self.non_batchwise_balance_value / self.non_batchwise_balance_qty
			)

			stock_value_change = self.batch_avg_rate[batch_no] * ledger.qty
			self.stock_value_change += stock_value_change

			frappe.db.set_value(
				"Serial and Batch Entry",
				ledger.name,
				{
					"stock_value_difference": stock_value_change,
					"incoming_rate": self.batch_avg_rate[batch_no],
				},
			)

	@deprecated
	def set_balance_value_for_non_batchwise_valuation_batches(self):
		self.set_balance_value_from_sl_entries()
		self.set_balance_value_from_bundle()

	@deprecated
	def set_balance_value_from_sl_entries(self) -> None:
		sle = frappe.qb.DocType("Stock Ledger Entry")
		batch = frappe.qb.DocType("Batch")

		timestamp_condition = CombineDatetime(sle.posting_date, sle.posting_time) < CombineDatetime(
			self.sle.posting_date, self.sle.posting_time
		)
		if self.sle.creation:
			timestamp_condition |= (
				CombineDatetime(sle.posting_date, sle.posting_time)
				== CombineDatetime(self.sle.posting_date, self.sle.posting_time)
			) & (sle.creation < self.sle.creation)

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
				& (batch.use_batchwise_valuation == 0)
				& (sle.is_cancelled == 0)
			)
			.where(timestamp_condition)
			.groupby(sle.batch_no)
		)

		if self.sle.name:
			query = query.where(sle.name != self.sle.name)

		for d in query.run(as_dict=True):
			self.non_batchwise_balance_value += flt(d.batch_value)
			self.non_batchwise_balance_qty += flt(d.batch_qty)
			self.available_qty[d.batch_no] += flt(d.batch_qty)

	@deprecated
	def set_balance_value_from_bundle(self) -> None:
		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		bundle_child = frappe.qb.DocType("Serial and Batch Entry")
		batch = frappe.qb.DocType("Batch")

		timestamp_condition = CombineDatetime(
			bundle.posting_date, bundle.posting_time
		) < CombineDatetime(self.sle.posting_date, self.sle.posting_time)

		if self.sle.creation:
			timestamp_condition |= (
				CombineDatetime(bundle.posting_date, bundle.posting_time)
				== CombineDatetime(self.sle.posting_date, self.sle.posting_time)
			) & (bundle.creation < self.sle.creation)

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
				& (batch.use_batchwise_valuation == 0)
				& (bundle.is_cancelled == 0)
				& (bundle.docstatus == 1)
				& (bundle.type_of_transaction.isin(["Inward", "Outward"]))
			)
			.where(timestamp_condition)
			.groupby(bundle_child.batch_no)
		)

		if self.sle.serial_and_batch_bundle:
			query = query.where(bundle.name != self.sle.serial_and_batch_bundle)

		for d in query.run(as_dict=True):
			self.non_batchwise_balance_value += flt(d.batch_value)
			self.non_batchwise_balance_qty += flt(d.batch_qty)
			self.available_qty[d.batch_no] += flt(d.batch_qty)
