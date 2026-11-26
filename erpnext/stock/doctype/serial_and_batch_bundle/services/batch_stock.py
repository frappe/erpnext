import frappe
from frappe import _, bold
from frappe.query_builder.functions import Sum
from frappe.utils import flt, format_datetime, get_datetime

from erpnext.stock.serial_batch_bundle.availability.batches import (
	get_auto_batch_nos,
	get_available_batches_qty,
)
from erpnext.stock.serial_batch_identity import SerialBatchIdentity


class BatchNegativeStockError(frappe.ValidationError):
	pass


class BundleBatchStock:
	def __init__(self, doc):
		self.doc = doc

	def validate_serial_and_batch_inventory(self):
		self.doc.check_future_entries_exists(is_cancelled=True)
		self.validate_batch_inventory()

	def validate_batch_inventory(self):
		if not self.doc.has_batch_no:
			return

		batches = [d.batch_no for d in self.doc.entries if d.batch_no]
		if not batches:
			return

		available_batches = get_auto_batch_nos(
			frappe._dict(
				{
					"item_code": self.doc.item_code,
					"warehouse": self.doc.warehouse,
					"batch_no": batches,
					"consider_negative_batches": True,
				}
			)
		)

		if not available_batches:
			return

		available_batches = get_available_batches_qty(available_batches)
		for batch_no in batches:
			if batch_no in available_batches and available_batches[batch_no] < 0:
				if flt(available_batches.get(batch_no)) < 0:
					self.validate_negative_batch(batch_no, available_batches[batch_no])

				batch_number = SerialBatchIdentity("Batch").get_label(batch_no)
				self.doc.throw_error_message(
					_("Batch {0} is not available in the selected warehouse {1}").format(
						bold(batch_number), self.doc.warehouse
					)
				)

	def validate_batch_quantity(self):
		# a reconciliation checks its outward bundles once its inward ones are posted
		if self.doc.type_of_transaction != "Outward" or self.doc.voucher_type == "Stock Reconciliation":
			return

		self.validate_future_batch_quantity()

	def validate_future_batch_quantity(self):
		if not self.doc.has_batch_no:
			return

		batch_wise_available_qty = self.get_batchwise_available_qty()
		precision = frappe.get_precision("Serial and Batch Entry", "qty")

		for d in self.doc.entries:
			available_qty = batch_wise_available_qty.get(d.batch_no, 0)
			if flt(available_qty, precision) < 0:
				self.throw_negative_batch(d.batch_no, available_qty, precision)

	def validate_negative_batch(self, batch_no, available_qty):
		if available_qty < 0 and not self.is_stock_reco_for_valuation_adjustment(available_qty):
			frappe.throw(
				_("Batch No {0} of Item {1} has negative stock of quantity {2} in the warehouse {3}").format(
					bold(SerialBatchIdentity("Batch").get_label(batch_no)),
					bold(self.doc.item_code),
					bold(available_qty),
					self.doc.warehouse,
				),
				BatchNegativeStockError,
			)

	def is_stock_reco_for_valuation_adjustment(self, available_qty):
		if (
			self.doc.voucher_type == "Stock Reconciliation"
			and self.doc.type_of_transaction == "Outward"
			and self.doc.voucher_detail_no
			and (
				abs(frappe.db.get_value("Stock Reconciliation Item", self.doc.voucher_detail_no, "qty"))
				== abs(available_qty)
			)
		):
			return True

		return False

	def throw_negative_batch(self, batch_no, available_qty, precision, posting_datetime=None):
		from erpnext.stock.stock_ledger import NegativeStockError

		if allow_negative_stock_for_batch(batch_no):
			return

		date_msg = ""
		if posting_datetime:
			date_msg = " " + _("as of {0}").format(format_datetime(posting_datetime))

		msg = _(
			"The Batch {0} of item {1} has negative stock in the warehouse {2}{3}. "
			"Please add a stock quantity of {4} to proceed with this entry. "
			"If it is not possible to make an adjustment entry, please enable 'Allow Negative Stock for Batch' in the batch {0} or in the Stock Settings to proceed. "
			"However, enabling this setting may lead to negative stock in the system. "
			"So please ensure the stock levels are adjusted as soon as possible to maintain the correct valuation rate."
		).format(
			bold(SerialBatchIdentity("Batch").get_label(batch_no)),
			bold(self.doc.item_code),
			bold(self.doc.warehouse),
			date_msg,
			bold(abs(flt(available_qty, precision))),
		)

		frappe.throw(
			msg,
			title=_("Negative Stock Error"),
			exc=NegativeStockError,
		)

	def get_batchwise_available_qty(self):
		posting_datetime = get_datetime(self.doc.posting_datetime) if self.doc.posting_datetime else None
		available_qty = self.get_batchwise_qty_before(posting_datetime)

		batchwise_entries = self.get_available_qty_from_sabb(posting_datetime)
		batchwise_entries.extend(self.get_available_qty_from_stock_ledger(posting_datetime))
		batchwise_entries = sorted(
			batchwise_entries,
			key=lambda x: (get_datetime(x.get("posting_datetime")), get_datetime(x.get("creation"))),
		)

		precision = frappe.get_precision("Serial and Batch Entry", "qty")
		for row in batchwise_entries:
			available_qty[row.batch_no] = flt(available_qty.get(row.batch_no)) + flt(row.qty)
			if flt(available_qty[row.batch_no], precision) < 0:
				self.throw_negative_batch(
					row.batch_no, available_qty[row.batch_no], precision, row.posting_datetime
				)

		return available_qty

	def get_batchwise_qty_before(self, posting_datetime):
		available_qty = frappe._dict()
		if not posting_datetime:
			return available_qty

		sle_query, sle = self.get_batch_query_from_stock_ledger()
		sabb_query, child = self.get_batch_query_from_sabb()
		queries = [
			sle_query.select(sle.actual_qty.as_("qty")).where(sle.posting_datetime < posting_datetime),
			sabb_query.select(child.qty).where(child.posting_datetime < posting_datetime),
		]
		for query in queries:
			batch_qty = (
				frappe.qb.from_(query)
				.select(query.batch_no, Sum(query.qty).as_("qty"))
				.groupby(query.batch_no)
			)
			for row in batch_qty.run(as_dict=True):
				available_qty[row.batch_no] = flt(available_qty.get(row.batch_no)) + flt(row.qty)

		return available_qty

	def get_available_qty_from_stock_ledger(self, posting_datetime=None):
		query, sle = self.get_batch_query_from_stock_ledger()
		query = query.select(sle.actual_qty.as_("qty"), sle.posting_datetime, sle.creation)
		if posting_datetime:
			query = query.where(sle.posting_datetime >= posting_datetime)

		return query.run(as_dict=True)

	def get_available_qty_from_sabb(self, posting_datetime=None):
		query, child = self.get_batch_query_from_sabb()
		query = query.select(child.qty, child.posting_datetime, child.creation)
		if posting_datetime:
			query = query.where(child.posting_datetime >= posting_datetime)

		return query.run(as_dict=True)

	def get_batch_query_from_stock_ledger(self):
		batches = [d.batch_no for d in self.doc.entries if d.batch_no]
		sle = frappe.qb.DocType("Stock Ledger Entry")

		query = (
			frappe.qb.from_(sle)
			.select(sle.batch_no)
			.where(
				(sle.item_code == self.doc.item_code)
				& (sle.warehouse == self.doc.warehouse)
				& (sle.is_cancelled == 0)
				& (sle.batch_no.isin(batches))
				& (sle.docstatus == 1)
				& (sle.serial_and_batch_bundle.isnull())
				& (sle.batch_no.isnotnull())
			)
			.for_update()
		)

		return query, sle

	def get_batch_query_from_sabb(self):
		batches = [d.batch_no for d in self.doc.entries if d.batch_no]
		child = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(child)
			.select(child.batch_no)
			.where(
				(child.item_code == self.doc.item_code)
				& (child.warehouse == self.doc.warehouse)
				& (child.is_cancelled == 0)
				& (child.batch_no.isin(batches))
				& (child.docstatus == 1)
				& (child.type_of_transaction.isin(["Inward", "Outward"]))
				& (child.voucher_type != "Pick List")
			)
			.for_update()
		)

		return query, child


def allow_negative_stock_for_batch(batch_no):
	"""Return whether negative stock is allowed for the given batch.

	The batch-level setting takes priority: if `allow_negative_stock_for_batch`
	is enabled on the Batch, negative stock is allowed regardless of Stock Settings.
	Otherwise, fall back to the `allow_negative_stock_for_batch` Stock Setting.
	"""
	if batch_no and frappe.db.get_value("Batch", batch_no, "allow_negative_stock_for_batch"):
		return True

	return bool(frappe.db.get_single_value("Stock Settings", "allow_negative_stock_for_batch"))
