# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, parse_json

from erpnext.stock.doctype.serial_and_batch_bundle.csv_import import read_serial_batch_csv
from erpnext.stock.doctype.serial_and_batch_bundle.services.batch_stock import BundleBatchStock
from erpnext.stock.doctype.serial_and_batch_bundle.services.future_transactions import (
	BundleFutureTransactions,
)
from erpnext.stock.doctype.serial_and_batch_bundle.services.returns import BundleReturn
from erpnext.stock.doctype.serial_and_batch_bundle.services.validation import BundleValidation
from erpnext.stock.doctype.serial_and_batch_bundle.services.valuation import BundleValuation
from erpnext.stock.doctype.serial_and_batch_bundle.services.voucher_link import BundleVoucherLink
from erpnext.stock.serial_batch_bundle.bundle_entries import parse_serial_nos


class SerialandBatchBundle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.serial_and_batch_entry.serial_and_batch_entry import SerialandBatchEntry

		amended_from: DF.Link | None
		avg_rate: DF.Float
		company: DF.Link
		entries: DF.Table[SerialandBatchEntry]
		has_batch_no: DF.Check
		has_serial_no: DF.Check
		is_cancelled: DF.Check
		is_packed: DF.Check
		is_rejected: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		naming_series: DF.Literal["", "SABB-.########"]
		posting_datetime: DF.Datetime | None
		returned_against: DF.Data | None
		total_amount: DF.Float
		total_qty: DF.Float
		type_of_transaction: DF.Literal["", "Inward", "Outward", "Maintenance", "Asset Repair"]
		voucher_detail_no: DF.Data | None
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link
		warehouse: DF.Link | None
	# end: auto-generated types

	def autoname(self):
		if frappe.get_single_value(
			"Stock Settings", "set_serial_and_batch_bundle_naming_based_on_naming_series"
		):
			if not self.naming_series:
				frappe.throw(_("Naming Series is mandatory"))

			naming_series = self.naming_series
			if "#" not in naming_series:
				naming_series += ".#####"

			self.name = make_autoname(self.naming_series)
		else:
			try:
				self.name = frappe.generate_hash(length=20)
			except frappe.DuplicateEntryError:
				self.autoname()

	def validate(self):
		validation = BundleValidation(self)
		validation.validate_allow_to_set_serial_batch()
		if self.docstatus == 1 and self.voucher_detail_no:
			validation.validate_voucher_detail_no()

		self.reset_serial_batch_bundle()
		self.set_batch_no()
		validation.validate_serial_and_batch_no()
		validation.validate_duplicate_serial_and_batch_no()
		validation.validate_voucher_no()

		if self.type_of_transaction == "Maintenance":
			return

		validation.allow_existing_serial_nos()
		if self.docstatus == 1:
			if not self.flags.ignore_validate_serial_batch or frappe.in_test:
				validation.validate_serial_nos_duplicate()

			self.check_future_entries_exists()
		elif (
			self.has_serial_no
			and self.type_of_transaction == "Outward"
			and self.voucher_type != "Stock Reconciliation"
			and self.voucher_no
		):
			validation.validate_serial_no_status()

		self.set_is_outward()
		self.calculate_total_qty(save=False)
		self.set_warehouse()

		if self.voucher_type != "Stock Entry" or not self.voucher_no or self.docstatus == 1:
			self.set_incoming_rate()

		self.calculate_qty_and_amount()
		self.set_child_details()

	def before_submit(self):
		validation = BundleValidation(self)
		validation.validate_submitted_with_its_voucher()
		validation.validate_serial_and_batch_data()
		BundleReturn(self).validate_serial_and_batch_no_for_returned()
		self.validate_returned_batch_qty()
		self.set_child_details()
		BundleVoucherLink(self).set_source_document_no()

	def on_submit(self):
		validation = BundleValidation(self)
		validation.validate_docstatus()
		validation.validate_serial_nos_inventory()
		BundleBatchStock(self).validate_batch_quantity()

	def before_cancel(self):
		self.delink_serial_and_batch_bundle()

	def on_cancel(self):
		BundleValidation(self).validate_voucher_no_docstatus()
		BundleBatchStock(self).validate_batch_quantity()
		BundleVoucherLink(self).remove_source_document_no()

	def on_trash(self):
		BundleValidation(self).validate_voucher_no_docstatus()
		voucher_link = BundleVoucherLink(self)
		voucher_link.delink_reference_from_voucher()
		voucher_link.delink_reference_from_batch()

	def set_incoming_rate(self, parent=None, row=None, save=False, allow_negative_stock=False, prev_sle=None):
		if self.type_of_transaction not in ["Inward", "Outward"] or self.voucher_type in [
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
		]:
			return

		returns = BundleReturn(self)
		if return_against := returns.get_return_against(parent=parent):
			returns.set_valuation_rate_for_return_entry(return_against, row, save, prev_sle=prev_sle)
		elif self.type_of_transaction == "Outward":
			BundleValuation(self).set_incoming_rate_for_outward_transaction(
				row, save, allow_negative_stock=allow_negative_stock
			)
		else:
			BundleValuation(self).set_incoming_rate_for_inward_transaction(row, save, prev_sle=prev_sle)

	def set_serial_and_batch_values(self, parent, row, qty_field=None):
		BundleVoucherLink(self).set_serial_and_batch_values(parent, row, qty_field=qty_field)

	def delink_serial_and_batch_bundle(self):
		BundleVoucherLink(self).delink_serial_and_batch_bundle()

	def check_future_entries_exists(self, is_cancelled=False):
		BundleFutureTransactions(self).check_future_entries_exists(is_cancelled=is_cancelled)

	def validate_serial_no_status(self):
		BundleValidation(self).validate_serial_no_status()

	def validate_returned_batch_qty(self):
		BundleReturn(self).validate_returned_batch_qty()

	def validate_serial_and_batch_inventory(self):
		BundleBatchStock(self).validate_serial_and_batch_inventory()

	def validate_future_batch_quantity(self):
		BundleBatchStock(self).validate_future_batch_quantity()

	def reset_serial_batch_bundle(self):
		if self.is_new() and self.amended_from:
			for field in ["is_cancelled", "is_rejected"]:
				if self.get(field):
					self.set(field, 0)

			if self.voucher_detail_no:
				self.voucher_detail_no = None

	def set_batch_no(self):
		if self.has_serial_no and self.has_batch_no:
			serial_nos = [d.serial_no for d in self.entries if d.serial_no]
			has_no_batch = any(not d.batch_no for d in self.entries)
			if not has_no_batch:
				return

			serial_no_batch = frappe._dict(
				frappe.get_all(
					"Serial No",
					filters={"name": ("in", serial_nos)},
					fields=["name", "batch_no"],
					as_list=True,
				)
			)

			for row in self.entries:
				if not row.batch_no:
					row.batch_no = serial_no_batch.get(row.serial_no)

	def throw_error_message(self, message, exception=frappe.ValidationError):
		frappe.throw(message, exception, title=_("Error"))

	def calculate_total_qty(self, save=True):
		self.total_qty = 0.0
		for d in self.entries:
			d.qty = 1 if self.has_serial_no and abs(d.qty) > 1 else abs(d.qty) if d.qty else 0
			d.stock_value_difference = abs(d.stock_value_difference) if d.stock_value_difference else 0
			if self.type_of_transaction == "Outward":
				d.qty *= -1
				d.stock_value_difference *= -1

			self.total_qty += flt(d.qty)

		if save:
			self.db_set("total_qty", self.total_qty)

	def get_serial_nos(self):
		return [d.serial_no for d in self.entries if d.serial_no]

	def update_valuation_rate(self, valuation_rate=None, save=False):
		for row in self.entries:
			row.incoming_rate = valuation_rate
			row.stock_value_difference = flt(row.qty) * flt(valuation_rate)

			if save:
				row.db_set(
					{"incoming_rate": row.incoming_rate, "stock_value_difference": row.stock_value_difference}
				)

	def set_is_outward(self):
		for row in self.entries:
			if self.type_of_transaction == "Outward" and row.qty > 0:
				row.qty *= -1
			elif self.type_of_transaction == "Inward" and row.qty < 0:
				row.qty *= -1

			row.is_outward = 1 if self.type_of_transaction == "Outward" else 0

	@frappe.whitelist()
	def set_warehouse(self):
		for row in self.entries:
			if row.warehouse != self.warehouse:
				row.warehouse = self.warehouse

	def calculate_qty_and_amount(self, save=False):
		self.total_amount = 0.0
		self.total_qty = 0.0
		self.avg_rate = 0.0

		for row in self.entries:
			rate = flt(row.incoming_rate)
			row.stock_value_difference = flt(row.qty) * rate
			self.total_amount += flt(row.qty) * rate
			self.total_qty += flt(row.qty)

		if self.total_qty:
			self.avg_rate = flt(self.total_amount) / flt(self.total_qty)

		if save:
			self.db_set(
				{
					"total_qty": self.total_qty,
					"avg_rate": self.avg_rate,
					"total_amount": self.total_amount,
				}
			)

	@property
	def child_table(self):
		if self.voucher_type == "Job Card":
			return

		parent_child_map = {
			"Asset Capitalization": "Asset Capitalization Stock Item",
			"Asset Repair": "Asset Repair Consumed Item",
			"Quotation": "Packed Item",
			"Stock Entry": "Stock Entry Detail",
		}

		return (
			parent_child_map[self.voucher_type]
			if self.voucher_type in parent_child_map
			else f"{self.voucher_type} Item"
		)

	def set_child_details(self):
		for row in self.entries:
			for field in [
				"warehouse",
				"posting_datetime",
				"voucher_type",
				"voucher_no",
				"voucher_detail_no",
				"type_of_transaction",
				"item_code",
			]:
				if not row.get(field) or row.get(field) != self.get(field):
					row.set(field, self.get(field))

	@frappe.whitelist(methods=["POST"])
	def add_serial_batch(self, data: str | dict):
		from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import resolve_csv_entries

		self.check_permission("create" if self.is_new() else "write")
		if self.docstatus != 0:
			frappe.throw(_("Serial and batch entries can only be changed in a draft bundle"))

		if isinstance(data, str):
			data = parse_json(data)
		if not isinstance(data, dict):
			frappe.throw(_("Serial and batch input must be a dictionary"))

		if data.get("csv_file"):
			serial_nos, batch_nos = read_serial_batch_csv(data["csv_file"])
			entries = serial_nos or batch_nos
		else:
			entries = [{"serial_no": number, "qty": 1} for number in parse_serial_nos(data.get("serial_nos"))]

		if not entries:
			return

		self.set(
			"entries", resolve_csv_entries(entries, self.item_code, self.type_of_transaction, self.company)
		)
		self.save()
		return self.name


def on_doctype_update():
	if frappe.db.db_type == "postgres":
		# Bundle-direct lookups (get_ledgers_from_serial_batch_bundle, get_picked_*) always filter
		# `is_cancelled = 0` and scope by voucher_no or item_code+warehouse -- none of which the parent
		# bundle is otherwise indexed on (only voucher_type/voucher_detail_no are). Partial indexes keep
		# only the active bundles. Postgres-only (`where` is a no-op on MariaDB, and MariaDB's optimizer
		# ignores partial predicates anyway).
		frappe.db.add_index(
			"Serial and Batch Bundle",
			["voucher_no"],
			index_name="sabb_active_voucher",
			where="is_cancelled = 0",
		)
		frappe.db.add_index(
			"Serial and Batch Bundle",
			["item_code", "warehouse"],
			index_name="sabb_active_item_wh",
			where="is_cancelled = 0",
		)
		return

	frappe.db.add_index("Serial and Batch Bundle", ["voucher_no", "voucher_type"])


def combine_datetime(date, time=None):
	from erpnext.stock.utils import get_combine_datetime

	return get_combine_datetime(date, time)


# Kept importable from here for other apps and for whitelisted method paths
from erpnext.stock.doctype.serial_and_batch_bundle.api import (
	add_serial_batch_ledgers,
	create_serial_batch_no_ledgers,
	get_auto_data,
	get_serial_batch_ledgers,
	get_serial_batch_numbers,
	get_serial_batch_scan,
	get_type_of_transaction,
	is_duplicate_serial_no,
	item_query,
)
from erpnext.stock.doctype.serial_and_batch_bundle.csv_import import download_blank_csv_template
from erpnext.stock.doctype.serial_and_batch_bundle.services.batch_stock import BatchNegativeStockError
from erpnext.stock.doctype.serial_and_batch_bundle.services.future_transactions import (
	SerialNoExistsInFutureTransactionError,
	get_stock_reco_details,
)
from erpnext.stock.doctype.serial_and_batch_bundle.services.validation import (
	SerialNoDuplicateError,
	SerialNoWarehouseError,
)
from erpnext.stock.serial_batch_bundle.availability.batches import get_auto_batch_nos, get_batch_qty_for_stock
from erpnext.stock.serial_batch_bundle.availability.reservations import (
	get_reserved_serial_nos_for_pos,
	get_reserved_serial_nos_for_sre,
)
from erpnext.stock.serial_batch_bundle.availability.serial_nos import (
	get_available_serial_nos,
	get_serial_nos_based_on_posting_date,
)
from erpnext.stock.serial_batch_bundle.bundle_entries import get_voucher_wise_serial_batch_from_bundle
