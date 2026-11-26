import frappe
from frappe import _
from frappe.utils import get_link_to_form

from erpnext.stock.serial_batch_bundle import get_batches_from_bundle
from erpnext.stock.serial_batch_bundle import get_serial_nos as get_serial_nos_from_bundle
from erpnext.stock.serial_batch_bundle.bundle_entries import parse_serial_nos
from erpnext.stock.serial_batch_identity import SerialBatchIdentity


class SerialNoExistsInFutureTransactionError(frappe.ValidationError):
	pass


class BundleFutureTransactions:
	def __init__(self, doc):
		self.doc = doc

	def check_future_entries_exists(self, is_cancelled=False):
		from erpnext.stock.valuation_adjustment import is_adjustment_voucher

		if self.doc.flags and self.doc.flags.via_landed_cost_voucher:
			return

		# an Adjustment Entry counts out and back in the same serial and batch nos, so what moves
		# them later is untouched by it, and backdated entries before it are blocked
		if is_adjustment_voucher(self.doc.voucher_type, self.doc.voucher_no):
			return

		serial_nos = []
		batches = []

		if self.doc.voucher_type == "Stock Reconciliation":
			serial_nos, batches = self.get_serial_nos_for_validate(is_cancelled=is_cancelled)
		else:
			batches = [d.batch_no for d in self.doc.entries if d.batch_no]

		if (
			self.doc.voucher_type != "Stock Reconciliation"
			and not self.doc.flags.ignore_validate_serial_batch
			and self.doc.has_serial_no
		):
			serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]

		if self.doc.has_batch_no and not self.doc.has_serial_no and not batches:
			return

		child = frappe.qb.DocType("Serial and Batch Entry")

		timestamp_condition = child.posting_datetime > self.doc.posting_datetime

		future_entries = (
			frappe.qb.from_(child)
			.select(
				child.serial_no,
				child.batch_no,
				child.voucher_type,
				child.voucher_no,
			)
			.distinct()
			.where(
				(child.parent != self.doc.name)
				& (child.item_code == self.doc.item_code)
				& (child.docstatus == 1)
				& (child.is_cancelled == 0)
				& (child.type_of_transaction.isin(["Inward", "Outward"]))
			)
			.where(timestamp_condition)
		)

		if self.doc.has_batch_no and not self.doc.has_serial_no:
			future_entries = future_entries.where(child.voucher_type == "Stock Reconciliation")

		if serial_nos:
			future_reconciliation_entries = self.get_future_reconciliation_entries(future_entries)
			future_entries = future_entries.where(child.serial_no.isin(serial_nos)).run(as_dict=True)
			future_entries.extend(future_reconciliation_entries)
		elif self.doc.has_serial_no:
			future_entries = self.get_future_reconciliation_entries(future_entries)
		elif batches:
			future_entries = future_entries.where(
				(child.batch_no.isin(batches)) & (child.warehouse == self.doc.warehouse)
			).run(as_dict=True)
		else:
			future_entries = future_entries.run(as_dict=True)

		if future_entries:
			if self.doc.has_serial_no:
				title = _("Serial No Exists In Future Transaction(s)")
			else:
				title = _("Batches Exists In Future Transaction(s)")

			msg = _(
				"Since the stock reconciliation exists for future dates, cancel it first. For Serial/Batch, if you want to make a backdated transaction, avoid using stock reconciliation. For more details about the transaction, please refer to the list below."
			)

			msg += "<br><br><ul>"

			for d in future_entries:
				if self.doc.has_serial_no:
					number = SerialBatchIdentity("Serial No").get_label(d.serial_no)
				else:
					number = SerialBatchIdentity("Batch").get_label(d.batch_no)
				link = get_link_to_form(d.voucher_type, d.voucher_no)
				msg += "<li>" + _("{0} in {1}").format(number, link) + "</li>"
			msg += "</li></ul>"

			frappe.throw(msg, title=title, exc=SerialNoExistsInFutureTransactionError)

	def get_future_reconciliation_entries(self, future_entries):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		bundles = (
			frappe.qb.from_(sle)
			.select(sle.serial_and_batch_bundle)
			.where(
				(sle.item_code == self.doc.item_code)
				& (sle.warehouse == self.doc.warehouse)
				& (sle.posting_datetime > self.doc.posting_datetime)
				& (sle.voucher_type == "Stock Reconciliation")
				& (sle.is_cancelled == 0)
				& (sle.serial_and_batch_bundle.isnotnull())
			)
			.run(pluck=True)
		)
		if not bundles:
			return []

		child = frappe.qb.DocType("Serial and Batch Entry")
		return future_entries.where(
			(child.parent.isin(bundles))
			& (child.warehouse == self.doc.warehouse)
			& (child.voucher_type == "Stock Reconciliation")
		).run(as_dict=True)

	def get_serial_nos_for_validate(self, is_cancelled=False):
		serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]
		batches = [d.batch_no for d in self.doc.entries if d.batch_no]

		skip_serial_nos, skip_batches = self.get_skip_serial_nos_for_stock_reconciliation(
			is_cancelled=is_cancelled
		)

		serial_nos = list(set(sorted(serial_nos)) - set(sorted(skip_serial_nos)))
		batch_nos = list(set(sorted(batches)) - set(sorted(skip_batches)))

		return serial_nos, batch_nos

	def get_skip_serial_nos_for_stock_reconciliation(self, is_cancelled=False):
		data = get_stock_reco_details(self.doc.voucher_detail_no)

		if not data:
			return [], []

		current_serial_nos = set()
		serial_nos = set()
		current_batches = set()
		batches = set()

		if data.current_serial_no:
			identity = SerialBatchIdentity("Serial No")
			current_serial_nos = {
				row.name
				for row in identity.get_records(
					data.item_code, parse_serial_nos(data.current_serial_no), ["name"]
				)
			}
			serial_nos = {
				row.name
				for row in identity.get_records(data.item_code, parse_serial_nos(data.serial_no), ["name"])
			}
			return list(serial_nos.intersection(current_serial_nos)), []

		elif data.batch_no and data.current_qty == data.qty:
			if (
				self.doc.has_serial_no
				and data.current_serial_and_batch_bundle
				and data.serial_and_batch_bundle
			):
				current_serial_nos = set(get_serial_nos_from_bundle(data.current_serial_and_batch_bundle))
				serial_nos = set(get_serial_nos_from_bundle(data.serial_and_batch_bundle))

			return list(serial_nos.intersection(current_serial_nos)), [data.batch_no]

		elif data.current_serial_and_batch_bundle:
			if self.doc.has_serial_no:
				current_serial_nos = set(get_serial_nos_from_bundle(data.current_serial_and_batch_bundle))
			else:
				current_batches = set(get_batches_from_bundle(data.current_serial_and_batch_bundle))

			if is_cancelled:
				return list(current_serial_nos), list(current_batches)

			if self.doc.has_serial_no:
				serial_nos = (
					set(get_serial_nos_from_bundle(data.serial_and_batch_bundle))
					if data.serial_and_batch_bundle
					else set([])
				)
			elif self.doc.has_batch_no and data.serial_and_batch_bundle:
				batches = set(get_batches_from_bundle(data.serial_and_batch_bundle))

			return list(serial_nos.intersection(current_serial_nos)), list(
				batches.intersection(current_batches)
			)

		return [], []


@frappe.request_cache
def get_stock_reco_details(voucher_detail_no):
	return frappe.db.get_value(
		"Stock Reconciliation Item",
		voucher_detail_no,
		[
			"item_code",
			"current_serial_no",
			"serial_no",
			"serial_and_batch_bundle",
			"current_serial_and_batch_bundle",
			"batch_no",
			"qty",
			"current_qty",
		],
		as_dict=True,
	)
