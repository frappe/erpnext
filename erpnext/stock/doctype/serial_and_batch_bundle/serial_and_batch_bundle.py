# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import collections
import json
from collections import defaultdict

import frappe
import frappe.query_builder
from frappe import _, bold
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.query_builder.functions import Abs, Coalesce, Sum
from frappe.utils import (
	cint,
	escape_html,
	flt,
	format_datetime,
	get_datetime,
	get_link_to_form,
	getdate,
	parse_json,
)

from erpnext.buying.doctype.buying_settings.buying_settings import (
	is_material_from_in_transit_warehouse,
	is_rejected_material_valued,
)

# Re-exported for other apps and whitelisted paths that still use this module
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
from erpnext.stock.doctype.serial_and_batch_bundle.csv_import import (
	download_blank_csv_template,
	read_serial_batch_csv,
)
from erpnext.stock.serial_batch_bundle import (
	BatchNoValuation,
	SerialNoValuation,
	get_batches_from_bundle,
)
from erpnext.stock.serial_batch_bundle import get_serial_nos as get_serial_nos_from_bundle
from erpnext.stock.serial_batch_bundle.availability.batches import (
	get_auto_batch_nos,
	get_available_batches_qty,
	get_batch_qty_for_stock,
)
from erpnext.stock.serial_batch_bundle.availability.reservations import (
	get_reserved_serial_nos_for_pos,
	get_reserved_serial_nos_for_sre,
	get_serial_no_reservation,
)
from erpnext.stock.serial_batch_bundle.availability.serial_nos import (
	get_available_serial_nos,
	get_serial_nos_based_on_posting_date,
)
from erpnext.stock.serial_batch_bundle.bundle_entries import (
	get_voucher_wise_serial_batch_from_bundle,
	parse_serial_nos,
)
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.valuation import FIFOValuation, LIFOValuation


class SerialNoExistsInFutureTransactionError(frappe.ValidationError):
	pass


class BatchNegativeStockError(frappe.ValidationError):
	pass


class SerialNoDuplicateError(frappe.ValidationError):
	pass


class SerialNoWarehouseError(frappe.ValidationError):
	pass


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
		self.validate_allow_to_set_serial_batch()
		if self.docstatus == 1 and self.voucher_detail_no:
			self.validate_voucher_detail_no()

		self.reset_serial_batch_bundle()
		self.set_batch_no()
		self.validate_serial_and_batch_no()
		self.validate_duplicate_serial_and_batch_no()
		self.validate_voucher_no()

		if self.type_of_transaction == "Maintenance":
			return

		self.allow_existing_serial_nos()
		if self.docstatus == 1:
			if not self.flags.ignore_validate_serial_batch or frappe.in_test:
				self.validate_serial_nos_duplicate()

			self.check_future_entries_exists()
		elif (
			self.has_serial_no
			and self.type_of_transaction == "Outward"
			and self.voucher_type != "Stock Reconciliation"
			and self.voucher_no
		):
			self.validate_serial_no_status()

		self.set_is_outward()
		self.calculate_total_qty(save=False)
		self.set_warehouse()

		if self.voucher_type != "Stock Entry" or not self.voucher_no or self.docstatus == 1:
			self.set_incoming_rate()

		self.calculate_qty_and_amount()
		self.set_child_details()

	def validate_allow_to_set_serial_batch(self):
		if not frappe.db.get_single_value("Stock Settings", "enable_serial_and_batch_no_for_item"):
			frappe.throw(
				_(
					"Please check the 'Activate Serial and Batch No for Item' checkbox in the {0} to make Serial and Batch Bundle for the item."
				).format(get_link_to_form("Stock Settings", "Stock Settings")),
				title=_("Serial and Batch No for Item Disabled"),
			)

	def validate_serial_no_status(self):
		serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		invalid_serial_nos = frappe.get_all(
			"Serial No",
			filters={
				"name": ("in", serial_nos),
				"warehouse": ("!=", self.warehouse),
			},
			pluck="serial_no",
		)

		if invalid_serial_nos:
			msg = _(
				"You cannot outward the following {0} as they are either Delivered, Inactive or located in a different warehouse."
			).format(_("Serial Nos") if len(invalid_serial_nos) > 1 else _("Serial No"))
			msg += "<hr>"
			msg += escape_html(", ".join(invalid_serial_nos))
			frappe.throw(msg)

	def validate_voucher_detail_no(self):
		if self.type_of_transaction not in ["Inward", "Outward"] or self.voucher_type in [
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
		]:
			return

		if self.voucher_type == "POS Invoice":
			if not frappe.db.exists("POS Invoice Item", self.voucher_detail_no):
				frappe.throw(
					_("The serial and batch bundle {0} is not linked to {1} {2}").format(
						bold(self.name), self.voucher_type, bold(self.voucher_no)
					)
				)

		elif not frappe.db.exists("Stock Ledger Entry", {"voucher_detail_no": self.voucher_detail_no}):
			if self.voucher_type in ["Delivery Note", "Sales Invoice"] and frappe.db.exists(
				"Packed Item", self.voucher_detail_no
			):
				return

			frappe.throw(
				_("The serial and batch bundle {0} is not linked to {1} {2}").format(
					bold(self.name), self.voucher_type, bold(self.voucher_no)
				)
			)

	def allow_existing_serial_nos(self):
		if self.type_of_transaction == "Outward" or not self.has_serial_no:
			return

		if frappe.get_single_value("Stock Settings", "allow_existing_serial_no"):
			return

		if self.voucher_type not in ["Purchase Receipt", "Purchase Invoice", "Stock Entry"]:
			return

		if self.voucher_type == "Stock Entry" and frappe.get_cached_value(
			"Stock Entry", self.voucher_no, "purpose"
		) in ["Material Transfer", "Send to Subcontractor", "Material Transfer for Manufacture"]:
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		if not serial_nos:
			return

		entry = frappe.qb.DocType("Serial and Batch Entry")
		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		query = (
			frappe.qb.from_(entry)
			.join(bundle)
			.on(bundle.name == entry.parent)
			.select(entry.serial_no, entry.parent, bundle.voucher_type, bundle.voucher_no)
			.where((entry.serial_no.isin(serial_nos)) & (entry.docstatus == 1) & (entry.qty < 0))
		)
		if self.docstatus == 0:
			# a serial no still in stock may be moving (e.g. a batch split), so check it on submit
			serial_no = frappe.qb.DocType("Serial No")
			query = (
				query.join(serial_no)
				.on(serial_no.name == entry.serial_no)
				.where(Coalesce(serial_no.warehouse, "") == "")
			)

		data = query.run(as_dict=True)

		# a serial no issued by this same voucher is moved within it, not received again
		moved = {
			row.serial_no
			for row in data
			if row.voucher_type == self.voucher_type and row.voucher_no == self.voucher_no
		}
		data = [row for row in data if row.serial_no not in moved]

		note = "<br><br> <b>Note</b>:<br>"
		for row in data:
			frappe.throw(
				_(
					"You cannot process the serial number {0} as it has already been used in the SABB {1}. {2} If you want to inward the same serial number multiple times, then enable 'Allow existing Serial No to be Manufactured/Received again' in the {3}"
				).format(
					SerialBatchIdentity("Serial No").get_label(row.serial_no),
					get_link_to_form("Serial and Batch Bundle", row.parent),
					note,
					get_link_to_form("Stock Settings", "Stock Settings"),
				)
			)

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

	def validate_serial_nos_inventory(self):
		if not (self.has_serial_no and self.type_of_transaction == "Outward"):
			return

		if self.voucher_type == "Stock Reconciliation":
			serial_nos, batches = self.get_serial_nos_for_validate()
		else:
			serial_nos = [d.serial_no for d in self.entries if d.serial_no]

		if not serial_nos:
			return

		kwargs = {
			"item_code": self.item_code,
			"warehouse": self.warehouse,
			"check_serial_nos": True,
			"serial_nos": serial_nos,
			"sabb_voucher_type": self.voucher_type,
			"sabb_voucher_no": self.voucher_no,
			"sabb_voucher_detail_no": self.voucher_detail_no,
		}

		if self.voucher_type == "POS Invoice":
			kwargs["ignore_voucher_nos"] = [self.voucher_no]

		if self.voucher_type == "Stock Reconciliation":
			kwargs.update(
				{
					"voucher_no": self.voucher_no,
					"posting_datetime": self.posting_datetime,
				}
			)

		available_serial_nos = get_available_serial_nos(frappe._dict(kwargs))

		serial_no_warehouse = {}
		for data in available_serial_nos:
			if data.serial_no not in serial_nos:
				continue

			serial_no_warehouse[data.serial_no] = data.warehouse

		for serial_no in serial_nos:
			if not serial_no_warehouse.get(serial_no) or serial_no_warehouse.get(serial_no) != self.warehouse:
				serial_number = SerialBatchIdentity("Serial No").get_label(serial_no)
				reservation = get_serial_no_reservation(self.item_code, serial_no, self.warehouse)
				if reservation:
					self.throw_error_message(
						_(
							"Serial No {0} is in warehouse {1} but is reserved for {2} {3} via {4}. Please use an unreserved serial number or cancel the reservation."
						).format(
							bold(serial_number),
							bold(self.warehouse),
							reservation.voucher_type,
							bold(reservation.voucher_no),
							get_link_to_form("Stock Reservation Entry", reservation.name),
						),
						SerialNoWarehouseError,
					)
				else:
					self.throw_error_message(
						_("Serial No {0} is not present in the warehouse {1}.").format(
							bold(serial_number), bold(self.warehouse)
						),
						SerialNoWarehouseError,
					)

	def validate_serial_nos_duplicate(self):
		# Don't inward same serial number multiple times
		if self.voucher_type in ["POS Invoice", "Pick List"]:
			return

		if not self.warehouse:
			return

		if self.voucher_type in ["Stock Reconciliation", "Stock Entry"] and self.docstatus != 1:
			return

		if not (self.has_serial_no and self.type_of_transaction == "Inward"):
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		kwargs = frappe._dict(
			{
				"item_code": self.item_code,
				"posting_datetime": self.posting_datetime,
				"serial_nos": serial_nos,
				"check_serial_nos": True,
			}
		)

		if self.docstatus == 1:
			kwargs["ignore_voucher_detail_no"] = self.voucher_detail_no
			kwargs["voucher_no"] = self.voucher_no

		available_serial_nos = get_available_serial_nos(kwargs)
		for data in available_serial_nos:
			if data.serial_no in serial_nos:
				serial_number = SerialBatchIdentity("Serial No").get_label(data.serial_no)
				self.throw_error_message(
					_("Serial No {0} is already present in the warehouse {1}.").format(
						bold(serial_number), bold(data.warehouse)
					),
					SerialNoDuplicateError,
				)

		if (
			self.voucher_type == "Stock Entry"
			and self.type_of_transaction == "Inward"
			and frappe.get_cached_value("Stock Entry", self.voucher_no, "purpose")
			in ["Manufacture", "Repack"]
		):
			serial_nos = frappe.get_all(
				"Serial No", filters={"name": ("in", serial_nos), "status": "Delivered"}, pluck="serial_no"
			)

			if serial_nos:
				if len(serial_nos) == 1:
					frappe.throw(
						_(
							"Serial No {0} is already Delivered. You cannot use it again in Manufacture / Repack entry."
						).format(bold(escape_html(serial_nos[0])))
					)
				else:
					frappe.throw(
						_(
							"Serial Nos {0} are already Delivered. You cannot use them again in Manufacture / Repack entry."
						).format(bold(escape_html(", ".join(serial_nos))))
					)

	def throw_error_message(self, message, exception=frappe.ValidationError):
		frappe.throw(message, exception, title=_("Error"))

	def set_incoming_rate(self, parent=None, row=None, save=False, allow_negative_stock=False, prev_sle=None):
		if self.type_of_transaction not in ["Inward", "Outward"] or self.voucher_type in [
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
		]:
			return

		if return_against := self.get_return_against(parent=parent):
			self.set_valuation_rate_for_return_entry(return_against, row, save, prev_sle=prev_sle)
		elif self.type_of_transaction == "Outward":
			self.set_incoming_rate_for_outward_transaction(
				row, save, allow_negative_stock=allow_negative_stock
			)
		else:
			self.set_incoming_rate_for_inward_transaction(row, save, prev_sle=prev_sle)

	def set_valuation_rate_for_return_entry(self, return_against, row, save=False, prev_sle=None):
		if valuation_details := self.get_valuation_rate_for_return_entry(return_against):
			from erpnext.stock.utils import get_valuation_method, is_serial_no_wise_valuation_disabled

			skip_rate_update = is_serial_no_wise_valuation_disabled(self.item_code)
			valuation_method = get_valuation_method(self.item_code, self.company)

			# An outward return must go out at the batch's current average rate for a
			# batchwise valuation batch. The original receipt rate is only correct while
			# the batch still holds stock at that rate; once other receipts have changed
			# the average, removing at the original rate strands a residue in the batch
			# value (negative when returning the costlier receipt).
			batchwise_avg_rates = self.get_batchwise_return_avg_rates()

			stock_queue = []
			non_batchwise_batches = []
			if not self.has_serial_no and valuation_method in ("FIFO", "LIFO"):
				non_batchwise_batches = frappe.get_all(
					"Batch",
					filters={
						"name": ("in", [d.batch_no for d in self.entries if d.batch_no]),
						"use_batchwise_valuation": 0,
					},
					pluck="name",
				)

				if non_batchwise_batches and prev_sle and prev_sle.stock_queue:
					stock_queue = parse_json(prev_sle.stock_queue)

			for row in self.entries:
				if valuation_details:
					self.validate_returned_serial_batch_no(return_against, row, valuation_details)

				if skip_rate_update:
					continue

				if row.serial_no:
					valuation_rate = valuation_details["serial_nos"].get(row.serial_no)
				else:
					valuation_rate = valuation_details["batches"].get(row.batch_no)

				if frappe.flags.through_repost_item_valuation and valuation_rate is None:
					# if different serial nos / batches are returned
					if row.serial_no:
						serial_nos = sorted(list(valuation_details["serial_nos"].keys()))
						valuation_rate = valuation_details["serial_nos"].get(serial_nos[cint(row.idx) - 1])
					else:
						batches = sorted(list(valuation_details["batches"].keys()))
						valuation_rate = valuation_details["batches"].get(batches[cint(row.idx) - 1])

				# a batch with an available balance goes out at its current average rate (a
				# valid 0.0 included); the original receipt rate applies only when there is
				# no balance to average
				if not row.serial_no and row.batch_no in batchwise_avg_rates:
					valuation_rate = batchwise_avg_rates[row.batch_no]

				row.incoming_rate = flt(valuation_rate)
				row.stock_value_difference = flt(row.qty) * flt(row.incoming_rate)

				if (
					non_batchwise_batches
					and row.batch_no in non_batchwise_batches
					and row.incoming_rate is not None
				):
					if flt(row.qty) > 0:
						stock_queue.append([row.qty, row.incoming_rate])
					elif flt(row.qty) < 0:
						queue_class = LIFOValuation if valuation_method == "LIFO" else FIFOValuation
						stock_queue = queue_class(stock_queue)
						stock_queue.remove_stock(
							qty=abs(row.qty), outgoing_rate=row.incoming_rate, is_return_purchase_entry=True
						)
						stock_queue = stock_queue.state
					row.stock_queue = json.dumps(stock_queue)

				if save:
					row.db_set(
						{
							"incoming_rate": row.incoming_rate,
							"stock_value_difference": row.stock_value_difference,
							"stock_queue": row.get("stock_queue"),
						}
					)

		elif self.type_of_transaction == "Inward":
			self.set_incoming_rate_for_inward_transaction(row, save, prev_sle=prev_sle)

	def get_batchwise_return_avg_rates(self):
		from erpnext.stock.utils import get_valuation_method

		if self.type_of_transaction != "Outward" or self.has_serial_no:
			return {}

		batch_nos = [d.batch_no for d in self.entries if d.batch_no]
		if not batch_nos:
			return {}

		if get_valuation_method(
			self.item_code, self.company
		) == "Moving Average" and frappe.db.get_single_value(
			"Stock Settings", "do_not_use_batchwise_valuation"
		):
			return {}

		batchwise_batches = frappe.get_all(
			"Batch",
			filters={"name": ("in", batch_nos), "use_batchwise_valuation": 1},
			pluck="name",
		)
		if not batchwise_batches:
			return {}

		# scoped to batchwise batches only, so BatchNoValuation's non-batchwise
		# machinery never runs for them
		sle = self.get_sle_for_outward_transaction()
		sle.batch_nos = {batch_no: sle.batch_nos[batch_no] for batch_no in batchwise_batches}
		sle.batchwise_valuation_batches = batchwise_batches
		sn_obj = BatchNoValuation(sle=sle, item_code=self.item_code, warehouse=self.warehouse)
		return {
			batch_no: abs(flt(sn_obj.batch_avg_rate.get(batch_no)))
			for batch_no in batchwise_batches
			if flt(sn_obj.available_qty.get(batch_no))
		}

	def validate_returned_serial_batch_no(self, return_against, row, original_inv_details):
		if frappe.flags.through_repost_item_valuation and not frappe.in_test:
			return

		if row.serial_no and row.serial_no not in original_inv_details["serial_nos"]:
			self.throw_error_message(
				_(
					"Serial No {0} is not present in the {1} {2}, hence you can't return it against the {1} {2}"
				).format(
					bold(SerialBatchIdentity("Serial No").get_label(row.serial_no)),
					self.voucher_type,
					bold(return_against),
				)
			)

		if row.batch_no and row.batch_no not in original_inv_details["batches"]:
			self.throw_error_message(
				_(
					"Batch No {0} is not present in the original {1} {2}, hence you can't return it against the {1} {2}"
				).format(
					bold(SerialBatchIdentity("Batch").get_label(row.batch_no)),
					self.voucher_type,
					bold(return_against),
				)
			)

	def get_valuation_rate_for_return_entry(self, return_against):
		from erpnext.controllers.sales_and_purchase_return import get_warehouses_for_return

		if not self.voucher_detail_no:
			return {}

		field = {
			"Sales Invoice": "sales_invoice_item",
			"Purchase Invoice": "purchase_invoice_item",
			"Delivery Note": "dn_detail",
			"Purchase Receipt": "purchase_receipt_item",
			"Subcontracting Receipt": "subcontracting_receipt_item",
		}.get(self.voucher_type)

		return_against_voucher_detail_no = frappe.db.get_value(
			self.child_table, self.voucher_detail_no, field
		)

		if not return_against_voucher_detail_no and self.voucher_type in ("Delivery Note", "Sales Invoice"):
			# Bundles built via the use_serial_batch_fields / SLE-driven path keep the Packed Item
			# as voucher_detail_no (not remapped to the DN/SI Item), so the lookup above misses.
			return_against_voucher_detail_no = self.get_return_against_packed_item(field)

		if not return_against_voucher_detail_no and self.voucher_type == "Subcontracting Receipt":
			return self.get_valuation_rate_for_returned_supplied_item(return_against)

		filters = [
			["Serial and Batch Bundle", "voucher_no", "=", return_against],
			["Serial and Batch Entry", "docstatus", "=", 1],
			["Serial and Batch Bundle", "is_cancelled", "=", 0],
			["Serial and Batch Bundle", "item_code", "=", self.item_code],
			["Serial and Batch Bundle", "voucher_detail_no", "=", return_against_voucher_detail_no],
		]

		# Added to handle rejected warehouse case
		return_warehouse = None
		if self.voucher_type in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
			warehouses = get_warehouses_for_return(self.voucher_type, return_against_voucher_detail_no)
			if self.warehouse in warehouses:
				return_warehouse = self.warehouse
				filters.append(["Serial and Batch Entry", "warehouse", "=", return_warehouse])

		bundle_data = frappe.get_all(
			"Serial and Batch Bundle",
			fields=[
				"name",
				"`tabSerial and Batch Entry`.`serial_no`",
				"`tabSerial and Batch Entry`.`batch_no`",
				"`tabSerial and Batch Entry`.`incoming_rate`",
			],
			filters=filters,
			order_by="`tabSerial and Batch Bundle`.`creation`, `tabSerial and Batch Entry`.`idx`",
		)
		if delivered_bundle := self.get_delivered_packed_item_bundle():
			# the delivered packed row's own rate wins for a batch other packed rows delivered too
			bundle_data.sort(key=lambda row: row.name == delivered_bundle)

		if not bundle_data:
			bundle_data = self.get_legacy_valuation_rate_for_return_entry(
				return_against, return_against_voucher_detail_no, return_warehouse
			)

		return self.get_valuation_details(bundle_data)

	def get_valuation_rate_for_returned_supplied_item(self, return_against):
		"""Rates of the serial nos and batches the returned receipt consumed for this raw material row."""
		returned = frappe.qb.DocType("Subcontracting Receipt Supplied Item")
		consumed = frappe.qb.DocType("Subcontracting Receipt Supplied Item").as_("consumed")
		item = frappe.qb.DocType("Subcontracting Receipt Item")
		original = frappe.qb.DocType("Subcontracting Receipt Item").as_("original")
		entry = frappe.qb.DocType("Serial and Batch Entry")

		bundle_data = (
			frappe.qb.from_(returned)
			.join(item)
			.on(item.name == returned.reference_name)
			.join(original)
			.on(original.name == item.subcontracting_receipt_item)
			.join(consumed)
			.on((consumed.reference_name == original.name) & (consumed.rm_item_code == returned.rm_item_code))
			.join(entry)
			.on(entry.parent == consumed.serial_and_batch_bundle)
			.select(entry.serial_no, entry.batch_no, entry.incoming_rate)
			.where(
				(returned.name == self.voucher_detail_no)
				& (consumed.parent == return_against)
				& (entry.docstatus == 1)
				# returned rejected goods bring raw materials back at the row rate, see get_rejected_return_rows
				& (item.warehouse != Coalesce(original.rejected_warehouse, ""))
			)
			.orderby(consumed.idx)
			.orderby(entry.idx)
		).run(as_dict=True)

		return self.get_valuation_details(bundle_data)

	@staticmethod
	def get_valuation_details(bundle_data):
		if not bundle_data:
			return {}

		valuation_details = frappe._dict(
			{
				"serial_nos": defaultdict(float),
				"batches": defaultdict(float),
			}
		)
		for row in bundle_data:
			if row.serial_no:
				valuation_details["serial_nos"][row.serial_no] = row.incoming_rate
			if row.batch_no:
				valuation_details["batches"][row.batch_no] = row.incoming_rate

		return valuation_details

	def get_delivered_packed_item_bundle(self):
		"""Bundle of the delivered packed row that the return's packed row of this bundle reverses."""
		if self.voucher_type not in ("Delivery Note", "Sales Invoice"):
			return

		returned = frappe.qb.DocType("Packed Item")
		delivered = frappe.qb.DocType("Packed Item").as_("delivered")
		bundles = (
			frappe.qb.from_(returned)
			.join(delivered)
			.on(delivered.name == returned.return_against_packed_item)
			.select(delivered.serial_and_batch_bundle)
			# a packed row's bundle points to the packed row, or to its bundle row once posted
			.where(
				(returned.name == self.voucher_detail_no)
				| (
					(returned.parent_detail_docname == self.voucher_detail_no)
					& (returned.serial_and_batch_bundle == self.name)
				)
			)
			.limit(1)
			.run()
		)
		return bundles[0][0] if bundles else None

	def get_return_against_packed_item(self, field):
		"""Resolve the original DN/SI Item when a return bundle's voucher_detail_no is the Packed Item."""
		parent_detail_docname = frappe.db.get_value(
			"Packed Item", self.voucher_detail_no, "parent_detail_docname"
		)
		if not parent_detail_docname:
			return

		return frappe.db.get_value(self.child_table, parent_detail_docname, field)

	def get_legacy_valuation_rate_for_return_entry(
		self, return_against, return_against_voucher_detail_no, return_warehouse=None
	):
		"""Return the original line's incoming rate per serial no / batch from the SLE, for legacy receipts with no bundle."""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if not (self.has_serial_no or self.has_batch_no):
			return []

		sle = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(sle)
			.select(sle.serial_no, sle.batch_no, sle.incoming_rate)
			.where(
				(sle.voucher_no == return_against)
				& (sle.voucher_detail_no == return_against_voucher_detail_no)
				& (sle.item_code == self.item_code)
				& (sle.is_cancelled == 0)
				& (sle.serial_and_batch_bundle.isnull())
			)
		)

		if return_warehouse:
			query = query.where(sle.warehouse == return_warehouse)

		data = []
		for d in query.run(as_dict=True):
			if d.serial_no:
				for serial_no in get_serial_nos(d.serial_no):
					data.append(
						frappe._dict(
							{"serial_no": serial_no, "batch_no": d.batch_no, "incoming_rate": d.incoming_rate}
						)
					)
			elif d.batch_no:
				data.append(
					frappe._dict(
						{"serial_no": None, "batch_no": d.batch_no, "incoming_rate": d.incoming_rate}
					)
				)

		return data

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

	def set_incoming_rate_for_outward_transaction(self, row=None, save=False, allow_negative_stock=False):
		from erpnext.stock.utils import get_valuation_method, is_serial_no_wise_valuation_disabled

		if is_serial_no_wise_valuation_disabled(self.item_code):
			return

		sle = self.get_sle_for_outward_transaction()

		if self.has_serial_no:
			sn_obj = SerialNoValuation(
				sle=sle,
				item_code=self.item_code,
				warehouse=self.warehouse,
			)

		else:
			sn_obj = BatchNoValuation(
				sle=sle,
				item_code=self.item_code,
				warehouse=self.warehouse,
			)

		stock_queue = []
		if hasattr(sn_obj, "stock_queue") and sn_obj.stock_queue:
			stock_queue = parse_json(sn_obj.stock_queue)

		val_method = get_valuation_method(self.item_code, self.company)

		for d in self.entries:
			available_qty = 0

			if self.has_serial_no:
				d.incoming_rate = abs(sn_obj.serial_no_incoming_rate.get(d.serial_no, 0.0))
			else:
				actual_qty = d.qty
				if (
					stock_queue
					and val_method in ("FIFO", "LIFO")
					and d.batch_no in sn_obj.non_batchwise_valuation_batches
				):
					if actual_qty < 0:
						queue_class = LIFOValuation if val_method == "LIFO" else FIFOValuation
						stock_queue = queue_class(stock_queue)
						_prev_qty, prev_stock_value = stock_queue.get_total_stock_and_value()

						stock_queue.remove_stock(qty=abs(actual_qty))
						_qty, stock_value = stock_queue.get_total_stock_and_value()

						stock_value_difference = stock_value - prev_stock_value
						d.incoming_rate = abs(flt(stock_value_difference) / abs(flt(actual_qty)))
						stock_queue = stock_queue.state
					else:
						d.incoming_rate = abs(flt(sn_obj.batch_avg_rate.get(d.batch_no)))
						stock_queue.append([d.qty, d.incoming_rate])
					d.stock_queue = json.dumps(stock_queue)
				else:
					d.incoming_rate = abs(flt(sn_obj.batch_avg_rate.get(d.batch_no)))

				precision = d.precision("qty")
				available_qty = flt(sn_obj.available_qty.get(d.batch_no), precision)
				if self.docstatus == 1:
					available_qty += flt(d.qty, precision)

				if not allow_negative_stock:
					self.validate_negative_batch(d.batch_no, available_qty)

			d.stock_value_difference = flt(d.qty) * flt(d.incoming_rate)

			if save:
				d.db_set(
					{
						"incoming_rate": d.incoming_rate,
						"stock_value_difference": d.stock_value_difference,
						"stock_queue": d.get("stock_queue"),
					}
				)

	def validate_negative_batch(self, batch_no, available_qty):
		if available_qty < 0 and not self.is_stock_reco_for_valuation_adjustment(available_qty):
			frappe.throw(
				_("Batch No {0} of Item {1} has negative stock of quantity {2} in the warehouse {3}").format(
					bold(SerialBatchIdentity("Batch").get_label(batch_no)),
					bold(self.item_code),
					bold(available_qty),
					self.warehouse,
				),
				BatchNegativeStockError,
			)

	def is_stock_reco_for_valuation_adjustment(self, available_qty):
		if (
			self.voucher_type == "Stock Reconciliation"
			and self.type_of_transaction == "Outward"
			and self.voucher_detail_no
			and (
				abs(frappe.db.get_value("Stock Reconciliation Item", self.voucher_detail_no, "qty"))
				== abs(available_qty)
			)
		):
			return True

		return False

	def get_sle_for_outward_transaction(self):
		sle = frappe._dict(
			{
				"posting_datetime": self.posting_datetime,
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"serial_and_batch_bundle": self.name,
				"company": self.company,
				"serial_nos": [row.serial_no for row in self.entries if row.serial_no],
				"batch_nos": {row.batch_no: row for row in self.entries if row.batch_no},
				"voucher_type": self.voucher_type,
				"voucher_detail_no": self.voucher_detail_no,
				"creation": self.creation,
			}
		)

		if self.docstatus == 1:
			sle["voucher_no"] = self.voucher_no

		if not sle.actual_qty:
			self.calculate_total_qty()
			sle.actual_qty = self.total_qty

		return sle

	def get_return_against(self, parent=None):
		return_against = None

		if parent and parent.get("is_return") and parent.get("return_against"):
			return parent.get("return_against")

		if (
			self.voucher_type
			in [
				"Delivery Note",
				"Sales Invoice",
				"Purchase Invoice",
				"Purchase Receipt",
				"POS Invoice",
				"Subcontracting Receipt",
			]
			and self.voucher_type
			and self.voucher_no
		):
			voucher_details = frappe.db.get_value(
				self.voucher_type, self.voucher_no, ["is_return", "return_against"], as_dict=True
			)
			if voucher_details and voucher_details.get("is_return") and voucher_details.get("return_against"):
				return voucher_details.get("return_against")

		return return_against

	def set_incoming_rate_for_inward_transaction(self, row=None, save=False, prev_sle=None):
		from erpnext.stock.utils import get_valuation_method

		valuation_method = get_valuation_method(self.item_code, self.company)

		valuation_field = "valuation_rate"
		if self.voucher_type in ["Sales Invoice", "Delivery Note", "Quotation"]:
			valuation_field = "incoming_rate"

		if self.voucher_type == "POS Invoice":
			valuation_field = "rate"

		rate = row.get(valuation_field) if row else 0.0
		child_table = self.child_table

		if self.voucher_type == "Subcontracting Receipt":
			if not self.voucher_detail_no:
				return
			elif frappe.db.exists("Subcontracting Receipt Supplied Item", self.voucher_detail_no):
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Supplied Item"
			else:
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Item"

		if not rate and self.voucher_detail_no and self.voucher_no:
			rate = frappe.db.get_value(child_table, self.voucher_detail_no, valuation_field)

		is_packed_item = False
		if rate is None and child_table in ["Delivery Note Item", "Sales Invoice Item"]:
			rate = frappe.db.get_value(
				"Packed Item",
				{"parent_detail_docname": self.voucher_detail_no, "item_code": self.item_code},
				"incoming_rate",
			)

			if rate is None:
				rate = frappe.db.get_value("Packed Item", self.voucher_detail_no, "incoming_rate")

			if rate is not None:
				is_packed_item = True

		stock_queue = []
		batches = frappe.get_all(
			"Batch",
			filters={
				"name": ("in", [d.batch_no for d in self.entries if d.batch_no]),
				"use_batchwise_valuation": 0,
			},
			pluck="name",
		)

		if prev_sle and prev_sle.stock_queue and parse_json(prev_sle.stock_queue):
			if batches and valuation_method in ("FIFO", "LIFO"):
				stock_queue = parse_json(prev_sle.stock_queue)

		values_rejected_material = is_rejected_material_valued(self.voucher_type, self.voucher_detail_no)

		if self.is_rejected and is_material_from_in_transit_warehouse(
			self.voucher_type, self.voucher_detail_no
		):
			# Rejected material of a transfer keeps the value it had in transit. A charge spread
			# over the accepted quantity does not belong to it.
			rate = flt(self.get_transit_rate(row)) or rate

		entry_rates = self.get_transfer_rates() or self.get_subcontracting_return_rates()
		precision = frappe.get_precision("Serial and Batch Entry", "incoming_rate")
		for d in self.entries:
			is_queue_valued = valuation_method in ("FIFO", "LIFO") and d.batch_no in batches

			entry_rate = entry_rates.get((d.serial_no, d.batch_no), rate)

			if self.is_rejected and not values_rejected_material:
				entry_rate = 0.0
			elif (
				(flt(d.incoming_rate, precision) == flt(entry_rate, precision))
				and not stock_queue
				and not is_queue_valued
				and d.qty
				and d.stock_value_difference
			):
				continue

			if is_packed_item and d.incoming_rate:
				entry_rate = d.incoming_rate

			d.incoming_rate = flt(entry_rate)
			if d.qty:
				d.stock_value_difference = flt(d.qty) * d.incoming_rate

			if is_queue_valued and d.incoming_rate is not None:
				stock_queue.append([d.qty, d.incoming_rate])
				d.stock_queue = json.dumps(stock_queue)

			if save:
				d.db_set(
					{
						"incoming_rate": d.incoming_rate,
						"stock_value_difference": d.stock_value_difference,
						"stock_queue": d.get("stock_queue"),
					}
				)

	def set_serial_and_batch_values(self, parent, row, qty_field=None):
		self.validate_not_linked_to_another_draft(parent, row)

		values_to_set = {"is_cancelled": 0}
		if not self.voucher_no or self.voucher_no != row.parent:
			values_to_set["voucher_no"] = row.parent

		if self.voucher_type != parent.doctype:
			values_to_set["voucher_type"] = parent.doctype

		if not self.voucher_detail_no or self.voucher_detail_no != row.name:
			values_to_set["voucher_detail_no"] = row.name

		if row.get("doctype") == "Packed Item" and row.get("parent_detail_docname"):
			values_to_set["voucher_detail_no"] = row.get("parent_detail_docname")

		if parent.get("posting_date") and parent.get("posting_time"):
			posting_datetime = combine_datetime(parent.posting_date, parent.posting_time)
			if not self.posting_datetime or self.posting_datetime != posting_datetime:
				values_to_set["posting_datetime"] = posting_datetime

		if parent.doctype in [
			"Delivery Note",
			"Purchase Receipt",
			"Purchase Invoice",
			"Sales Invoice",
		] and parent.get("is_return"):
			return_ref_field = frappe.scrub(parent.doctype) + "_item"
			if parent.doctype == "Delivery Note":
				return_ref_field = "dn_detail"

			if row.get(return_ref_field):
				values_to_set["returned_against"] = row.get(return_ref_field)

		self.db_set(values_to_set)
		values_to_set.pop("returned_against", None)
		frappe.db.set_value(
			"Serial and Batch Entry", {"parent": self.name}, values_to_set, update_modified=False
		)

		self.calculate_total_qty(save=True)

		# If user has changed the rate in the child table
		if self.docstatus == 0 and self.type_of_transaction == "Inward":
			self.set_incoming_rate(parent=parent, row=row, save=True)

		if self.docstatus == 0 and parent.get("is_return") and parent.is_new():
			self.reset_qty(row, qty_field=qty_field)

		self.calculate_qty_and_amount(save=True)
		self.validate_quantity(row, qty_field=qty_field)

	def validate_not_linked_to_another_draft(self, parent, row):
		"""A draft voucher can't take over the bundle of another draft voucher."""
		if not (self.voucher_type and self.voucher_no):
			return

		if self.voucher_type == parent.doctype and self.voucher_no == row.parent:
			return

		if frappe.db.get_value(self.voucher_type, self.voucher_no, "docstatus") != 0:
			return

		frappe.throw(
			_(
				"Row #{0}: Serial and Batch Bundle {1} belongs to {2} {3}. Select or create another bundle."
			).format(
				row.idx,
				bold(self.name),
				self.voucher_type,
				get_link_to_form(self.voucher_type, self.voucher_no),
			)
		)

	def validate_voucher_no(self):
		if not (self.voucher_type and self.voucher_no):
			return

		if (
			self.docstatus == 1
			and self.voucher_no
			and not frappe.db.exists(self.voucher_type, self.voucher_no)
		):
			self.throw_error_message(
				_("The {0} # {1} does not exist").format(self.voucher_type, self.voucher_no)
			)

		if self.flags.ignore_voucher_validation:
			return

		if (
			self.docstatus == 1
			and frappe.get_cached_value(self.voucher_type, self.voucher_no, "docstatus") != 1
		):
			self.throw_error_message(
				_("The {0} # {1} should be submitted first.").format(self.voucher_type, self.voucher_no)
			)

	def get_future_reconciliation_entries(self, future_entries):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		bundles = (
			frappe.qb.from_(sle)
			.select(sle.serial_and_batch_bundle)
			.where(
				(sle.item_code == self.item_code)
				& (sle.warehouse == self.warehouse)
				& (sle.posting_datetime > self.posting_datetime)
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
			& (child.warehouse == self.warehouse)
			& (child.voucher_type == "Stock Reconciliation")
		).run(as_dict=True)

	def check_future_entries_exists(self, is_cancelled=False):
		from erpnext.stock.valuation_adjustment import is_adjustment_voucher

		if self.flags and self.flags.via_landed_cost_voucher:
			return

		# an Adjustment Entry counts out and back in the same serial and batch nos, so what moves
		# them later is untouched by it, and backdated entries before it are blocked
		if is_adjustment_voucher(self.voucher_type, self.voucher_no):
			return

		serial_nos = []
		batches = []

		if self.voucher_type == "Stock Reconciliation":
			serial_nos, batches = self.get_serial_nos_for_validate(is_cancelled=is_cancelled)
		else:
			batches = [d.batch_no for d in self.entries if d.batch_no]

		if (
			self.voucher_type != "Stock Reconciliation"
			and not self.flags.ignore_validate_serial_batch
			and self.has_serial_no
		):
			serial_nos = [d.serial_no for d in self.entries if d.serial_no]

		if self.has_batch_no and not self.has_serial_no and not batches:
			return

		child = frappe.qb.DocType("Serial and Batch Entry")

		timestamp_condition = child.posting_datetime > self.posting_datetime

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
				(child.parent != self.name)
				& (child.item_code == self.item_code)
				& (child.docstatus == 1)
				& (child.is_cancelled == 0)
				& (child.type_of_transaction.isin(["Inward", "Outward"]))
			)
			.where(timestamp_condition)
		)

		if self.has_batch_no and not self.has_serial_no:
			future_entries = future_entries.where(child.voucher_type == "Stock Reconciliation")

		if serial_nos:
			future_reconciliation_entries = self.get_future_reconciliation_entries(future_entries)
			future_entries = future_entries.where(child.serial_no.isin(serial_nos)).run(as_dict=True)
			future_entries.extend(future_reconciliation_entries)
		elif self.has_serial_no:
			future_entries = self.get_future_reconciliation_entries(future_entries)
		elif batches:
			future_entries = future_entries.where(
				(child.batch_no.isin(batches)) & (child.warehouse == self.warehouse)
			).run(as_dict=True)
		else:
			future_entries = future_entries.run(as_dict=True)

		if future_entries:
			if self.has_serial_no:
				title = _("Serial No Exists In Future Transaction(s)")
			else:
				title = _("Batches Exists In Future Transaction(s)")

			msg = _(
				"Since the stock reconciliation exists for future dates, cancel it first. For Serial/Batch, if you want to make a backdated transaction, avoid using stock reconciliation. For more details about the transaction, please refer to the list below."
			)

			msg += "<br><br><ul>"

			for d in future_entries:
				if self.has_serial_no:
					number = SerialBatchIdentity("Serial No").get_label(d.serial_no)
				else:
					number = SerialBatchIdentity("Batch").get_label(d.batch_no)
				link = get_link_to_form(d.voucher_type, d.voucher_no)
				msg += "<li>" + _("{0} in {1}").format(number, link) + "</li>"
			msg += "</li></ul>"

			frappe.throw(msg, title=title, exc=SerialNoExistsInFutureTransactionError)

	def get_serial_nos_for_validate(self, is_cancelled=False):
		serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		batches = [d.batch_no for d in self.entries if d.batch_no]

		skip_serial_nos, skip_batches = self.get_skip_serial_nos_for_stock_reconciliation(
			is_cancelled=is_cancelled
		)

		serial_nos = list(set(sorted(serial_nos)) - set(sorted(skip_serial_nos)))
		batch_nos = list(set(sorted(batches)) - set(sorted(skip_batches)))

		return serial_nos, batch_nos

	def get_skip_serial_nos_for_stock_reconciliation(self, is_cancelled=False):
		data = get_stock_reco_details(self.voucher_detail_no)

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
			if self.has_serial_no and data.current_serial_and_batch_bundle and data.serial_and_batch_bundle:
				current_serial_nos = set(get_serial_nos_from_bundle(data.current_serial_and_batch_bundle))
				serial_nos = set(get_serial_nos_from_bundle(data.serial_and_batch_bundle))

			return list(serial_nos.intersection(current_serial_nos)), [data.batch_no]

		elif data.current_serial_and_batch_bundle:
			if self.has_serial_no:
				current_serial_nos = set(get_serial_nos_from_bundle(data.current_serial_and_batch_bundle))
			else:
				current_batches = set(get_batches_from_bundle(data.current_serial_and_batch_bundle))

			if is_cancelled:
				return list(current_serial_nos), list(current_batches)

			if self.has_serial_no:
				serial_nos = (
					set(get_serial_nos_from_bundle(data.serial_and_batch_bundle))
					if data.serial_and_batch_bundle
					else set([])
				)
			elif self.has_batch_no and data.serial_and_batch_bundle:
				batches = set(get_batches_from_bundle(data.serial_and_batch_bundle))

			return list(serial_nos.intersection(current_serial_nos)), list(
				batches.intersection(current_batches)
			)

		return [], []

	def reset_qty(self, row, qty_field=None):
		qty_field = self.get_qty_field(row, qty_field=qty_field)
		qty = abs(flt(self.get_row_qty(row, qty_field), self.precision("total_qty")))

		idx = None
		while qty > 0:
			for d in self.entries:
				row_qty = abs(flt(d.qty, d.precision("qty")))
				if row_qty >= qty:
					d.db_set("qty", qty if self.type_of_transaction == "Inward" else qty * -1)
					qty = 0
					idx = d.idx
					break
				else:
					qty = flt(qty - row_qty, d.precision("qty"))
					idx = d.idx

		if idx and len(self.entries) > idx:
			remove_rows = []
			for d in self.entries:
				if d.idx > idx:
					remove_rows.append(d)

			for d in remove_rows:
				self.entries.remove(d)

			self.flags.ignore_links = True
			self.save()

	def get_row_qty(self, row, qty_field) -> float:
		"""What the row holds in the units a package counts in."""
		if qty_field == "qty" and row.get("stock_qty"):
			return flt(row.get("stock_qty"))

		if qty_field == "rejected_qty":
			return flt(row.get(qty_field)) * flt(row.get("conversion_factor") or 1)

		return flt(row.get(qty_field))

	def validate_quantity(self, row, qty_field=None):
		qty_field = self.get_qty_field(row, qty_field=qty_field)
		qty = self.get_row_qty(row, qty_field)

		precision = row.precision(qty_field)
		if abs(abs(flt(self.total_qty, precision)) - abs(flt(qty, precision))) > 0.01:
			total_qty = frappe.format_value(abs(flt(self.total_qty)), "Float", row)
			set_qty = frappe.format_value(abs(flt(qty)), "Float", row)
			self.throw_error_message(
				_(
					"Total quantity {0} in the Serial and Batch Bundle {1} does not match with the quantity {2} for the Item {3} in the {4} # {5}"
				).format(
					total_qty,
					bold(self.name),
					set_qty,
					bold(self.item_code),
					self.voucher_type,
					self.voucher_no,
				)
			)

	def get_transfer_rates(self) -> dict:
		"""Rate of each serial/batch where the same transfer row took it out, plus the row's added cost."""
		from erpnext.stock.utils import is_serial_no_wise_valuation_disabled

		if not self.voucher_detail_no or is_serial_no_wise_valuation_disabled(self.item_code):
			return {}

		outward_bundles = frappe.get_all(
			"Serial and Batch Bundle",
			filters={
				"voucher_type": self.voucher_type,
				"voucher_detail_no": self.voucher_detail_no,
				"item_code": self.item_code,
				"type_of_transaction": "Outward",
				"is_cancelled": 0,
			},
			pluck="name",
		)
		if not outward_bundles:
			return {}

		added_cost_per_unit = self.get_transfer_added_cost_per_unit()
		if added_cost_per_unit is None:
			return {}

		return {
			(d.serial_no, d.batch_no): flt(d.incoming_rate) + added_cost_per_unit
			for d in frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": ("in", outward_bundles)},
				fields=["serial_no", "batch_no", "incoming_rate"],
			)
		}

	def get_transfer_added_cost_per_unit(self) -> float | None:
		"""Cost a transfer row adds to each stock unit it moves, None when the row is no transfer."""
		if self.voucher_type == "Stock Entry":
			additional_cost, transfer_qty = frappe.db.get_value(
				"Stock Entry Detail", self.voucher_detail_no, ["additional_cost", "transfer_qty"]
			)
			return flt(additional_cost) / flt(transfer_qty)

		if self.voucher_type in ("Delivery Note", "Sales Invoice"):
			target_warehouse = frappe.db.get_value(
				self.child_table, self.voucher_detail_no, "target_warehouse"
			)
			return 0.0 if target_warehouse else None

		if self.voucher_type not in ("Purchase Receipt", "Purchase Invoice"):
			return None

		row = frappe.db.get_value(
			self.child_table,
			self.voucher_detail_no,
			["from_warehouse", "landed_cost_voucher_amount", "stock_qty"],
			as_dict=True,
		)
		if not (row and row.from_warehouse):
			return None

		# the landed cost belongs to the accepted stock only
		if self.is_rejected or not flt(row.stock_qty):
			return 0.0

		return flt(row.landed_cost_voucher_amount) / flt(row.stock_qty)

	def get_subcontracting_return_rates(self) -> dict:
		"""Rate the returned Subcontracting Receipt consumed each serial/batch of a supplied item at."""
		from erpnext.stock.utils import get_valuation_method

		if self.voucher_type != "Subcontracting Receipt" or not self.voucher_detail_no:
			return {}

		row = frappe.db.get_value(
			"Subcontracting Receipt Supplied Item",
			self.voucher_detail_no,
			["parent", "reference_name", "rm_item_code"],
			as_dict=True,
		)
		if not row:
			return {}

		receipt = frappe.get_doc("Subcontracting Receipt", row.parent)
		# rejected returns and Standard Cost items keep the row rate
		if (
			not receipt.is_return
			or row.reference_name in receipt.get_rejected_return_rows()
			or get_valuation_method(self.item_code, self.company) == "Standard Cost"
		):
			return {}

		receipt_item = receipt.get("items", {"name": row.reference_name})[0].subcontracting_receipt_item
		consumed = receipt.get_consumed_serial_batches().get((receipt_item, row.rm_item_code), {})
		return {key: identity.rate for key, identity in consumed.items()}

	def get_transit_rate(self, row) -> float:
		"""What one stock unit of the material was worth on its way into the in-transit warehouse."""
		if not (row and row.get("sales_incoming_rate")):
			if not (self.voucher_detail_no and self.voucher_no):
				return 0.0

			row = (
				frappe.db.get_value(
					self.child_table,
					self.voucher_detail_no,
					["sales_incoming_rate", "conversion_factor"],
					as_dict=True,
				)
				or {}
			)

		# sales_incoming_rate is per purchase UOM, but the entries of the bundle hold stock UOM qty
		return flt(row.get("sales_incoming_rate")) / (flt(row.get("conversion_factor")) or 1.0)

	def get_qty_field(self, row, qty_field=None) -> str:
		if not qty_field:
			qty_field = "qty"

		if row.get("doctype") == "Subcontracting Receipt Supplied Item":
			qty_field = "consumed_qty"
		elif row.get("doctype") == "Stock Entry Detail":
			qty_field = "transfer_qty"
		elif row.get("doctype") in ["Sales Invoice Item", "Purchase Invoice Item"] and qty_field == "qty":
			qty_field = "stock_qty"

		return qty_field

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

	def validate_serial_and_batch_no(self):
		if self.item_code and not self.has_serial_no and not self.has_batch_no:
			frappe.throw(_("The Item {0} does not have Serial No or Batch No").format(self.item_code))

		serial_nos = []
		batch_nos = set()

		serial_batches = {}
		for row in self.entries:
			if not row.qty and row.batch_no and not row.serial_no:
				if self.voucher_type == "Stock Reconciliation" and self.type_of_transaction == "Inward":
					continue

				frappe.throw(
					_("At row {0}: Qty is mandatory for the batch {1}").format(
						bold(row.idx), bold(SerialBatchIdentity("Batch").get_label(row.batch_no))
					)
				)

			if self.has_serial_no and not row.serial_no:
				frappe.throw(
					_("At row {0}: Serial No is mandatory for Item {1}").format(
						bold(row.idx), bold(self.item_code)
					),
					title=_("Serial No is mandatory"),
				)

			if self.has_batch_no and not row.batch_no:
				frappe.throw(
					_("At row {0}: Batch No is mandatory for Item {1}").format(
						bold(row.idx), bold(self.item_code)
					),
					title=_("Batch No is mandatory"),
				)

			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no:
				batch_nos.add(row.batch_no)

			if row.serial_no and row.batch_no and self.type_of_transaction == "Outward":
				serial_batches.setdefault(row.serial_no, row.batch_no)

		if serial_nos:
			self.validate_incorrect_serial_nos(serial_nos)

		if batch_nos:
			self.validate_incorrect_batch_nos(list(batch_nos))

		if serial_batches:
			self.validate_serial_batch_no(serial_batches)

	def validate_serial_batch_no(self, serial_batches):
		correct_batches = frappe._dict(
			frappe.get_all(
				"Serial No",
				filters={"name": ("in", list(serial_batches.keys()))},
				fields=["name", "batch_no"],
				as_list=True,
			)
		)

		for serial_no, batch_no in serial_batches.items():
			if correct_batches.get(serial_no) and correct_batches.get(serial_no) != batch_no:
				serial_number = SerialBatchIdentity("Serial No").get_label(serial_no)
				batch_number = SerialBatchIdentity("Batch").get_label(batch_no)
				self.throw_error_message(
					_("Serial No {0} does not belong to Batch No {1}").format(
						bold(serial_number), bold(batch_number)
					)
				)

	def validate_incorrect_serial_nos(self, serial_nos):
		incorrect_serial_nos = frappe.get_all(
			"Serial No",
			filters={"name": ("in", serial_nos), "item_code": ("!=", self.item_code)},
			pluck="serial_no",
		)

		if incorrect_serial_nos:
			incorrect_serial_nos = escape_html(", ".join(incorrect_serial_nos))
			self.throw_error_message(
				_("Serial Nos {0} does not belong to Item {1}").format(
					bold(incorrect_serial_nos), bold(self.item_code)
				)
			)

	def validate_incorrect_batch_nos(self, batch_nos):
		incorrect_batch_nos = frappe.get_all(
			"Batch", filters={"name": ("in", batch_nos), "item": ("!=", self.item_code)}, pluck="batch_id"
		)

		if incorrect_batch_nos:
			incorrect_batch_nos = escape_html(", ".join(incorrect_batch_nos))
			self.throw_error_message(
				_("Batch Nos {0} does not belong to Item {1}").format(
					bold(incorrect_batch_nos), bold(self.item_code)
				)
			)

	def validate_serial_and_batch_no_for_returned(self):
		if not self.returned_against:
			return

		if self.voucher_type not in [
			"Purchase Receipt",
			"Purchase Invoice",
			"Sales Invoice",
			"Delivery Note",
		]:
			return

		data = self.get_orignal_document_data()
		if not data:
			return

		serial_nos, batches = [], []
		current_serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		current_batches = [d.batch_no for d in self.entries if d.batch_no]

		for d in data:
			if self.has_serial_no:
				if d.serial_and_batch_bundle:
					serial_nos = get_serial_nos_from_bundle(d.serial_and_batch_bundle)
				else:
					serial_nos = SerialBatchIdentity("Serial No").resolve(
						d.item_code, parse_serial_nos(d.serial_no), ignore_permissions=True
					)

			elif self.has_batch_no:
				if d.serial_and_batch_bundle:
					batches = get_batches_from_bundle(d.serial_and_batch_bundle)
				else:
					batches = frappe._dict({d.batch_no: d.stock_qty})

				if batches:
					batches = [d for d in batches if batches[d] > 0]

			if serial_nos:
				if invalid_serial_nos := set(current_serial_nos) - set(serial_nos):
					numbers = frappe.get_all(
						"Serial No", filters={"name": ("in", invalid_serial_nos)}, pluck="serial_no"
					)
					self.throw_error_message(
						_("Serial Nos {0} are not part of the original document.").format(
							bold(escape_html(", ".join(numbers)))
						)
					)

			if batches:
				if invalid_batches := set(current_batches) - set(batches):
					numbers = frappe.get_all(
						"Batch", filters={"name": ("in", invalid_batches)}, pluck="batch_id"
					)
					self.throw_error_message(
						_("Batch Nos {0} are not part of the original document.").format(
							bold(escape_html(", ".join(numbers)))
						)
					)

	def validate_returned_batch_qty(self):
		reference_field = {"Delivery Note": "dn_detail", "Sales Invoice": "sales_invoice_item"}.get(
			self.voucher_type
		)
		if (
			self.type_of_transaction != "Inward"
			or not reference_field
			or not self.has_batch_no
			or self.has_serial_no
		):
			return

		child_doctype = self.voucher_type + " Item"
		original_row = frappe.db.get_value(child_doctype, self.voucher_detail_no, reference_field)
		available = original_row and self.get_batch_qty_left_to_return(
			child_doctype, reference_field, original_row
		)
		if not available:
			return

		precision = self.precision("total_qty")
		for row in self.entries:
			remaining = flt(available.get(row.batch_no), precision)
			if row.batch_no and flt(abs(row.qty), precision) > remaining:
				self.throw_error_message(
					_(
						"Row #{0}: Cannot return {1} of Batch {2}, only {3} was delivered and not returned yet."
					).format(
						row.idx,
						abs(row.qty),
						bold(SerialBatchIdentity("Batch").get_label(row.batch_no)),
						max(remaining, 0),
					)
				)

	def get_batch_qty_left_to_return(self, child_doctype, reference_field, original_row):
		original = frappe.db.get_value(
			child_doctype, original_row, ["serial_and_batch_bundle", "batch_no", "stock_qty"], as_dict=True
		)
		if not original:
			return {}

		delivered = get_batches_from_bundle(original.serial_and_batch_bundle) or {
			original.batch_no: original.stock_qty
		}
		available = {batch_no: abs(flt(qty)) for batch_no, qty in delivered.items() if batch_no}
		if not available:
			return available

		for batch_no, qty in self.get_returned_batch_qty(child_doctype, reference_field, original_row):
			available[batch_no] = flt(available.get(batch_no)) - flt(qty)
		return available

	def get_returned_batch_qty(self, child_doctype, reference_field, original_row):
		child = frappe.qb.DocType(child_doctype)
		parent = frappe.qb.DocType(self.voucher_type)
		entry = frappe.qb.DocType("Serial and Batch Entry")
		return (
			frappe.qb.from_(entry)
			.join(child)
			.on(entry.parent == child.serial_and_batch_bundle)
			.join(parent)
			.on(child.parent == parent.name)
			.select(entry.batch_no, Sum(Abs(entry.qty)))
			.where(
				(child[reference_field] == original_row)
				& (child.name != self.voucher_detail_no)
				& (entry.docstatus == 1)
				& (parent.docstatus == 1)
				& (parent.is_return == 1)
			)
			.groupby(entry.batch_no)
		).run()

	def get_orignal_document_data(self):
		fields = ["item_code", "serial_and_batch_bundle", "stock_qty"]
		if self.has_serial_no:
			fields.append("serial_no")

		elif self.has_batch_no:
			fields.append("batch_no")

		child_doc = self.voucher_type + " Item"
		return frappe.get_all(child_doc, fields=fields, filters={"name": self.returned_against})

	def validate_duplicate_serial_and_batch_no(self):
		serial_nos = []
		batch_nos = []

		for row in self.entries:
			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no and not row.serial_no:
				batch_nos.append(row.batch_no)

		if serial_nos:
			for key, value in collections.Counter(serial_nos).items():
				if value > 1:
					self.throw_error_message(
						_("Duplicate Serial No {0} found").format(
							SerialBatchIdentity("Serial No").get_label(key)
						)
					)

		if batch_nos:
			for key, value in collections.Counter(batch_nos).items():
				if value > 1:
					self.throw_error_message(
						_("Duplicate Batch No {0} found").format(SerialBatchIdentity("Batch").get_label(key))
					)

	def before_cancel(self):
		self.delink_serial_and_batch_bundle()

	def delink_serial_and_batch_bundle(self):
		sles = frappe.get_all("Stock Ledger Entry", filters={"serial_and_batch_bundle": self.name})

		for sle in sles:
			frappe.db.set_value("Stock Ledger Entry", sle.name, "serial_and_batch_bundle", None)

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

	def delink_reference_from_voucher(self):
		or_filters = {"serial_and_batch_bundle": self.name}

		fields = ["name", "serial_and_batch_bundle"]
		if self.voucher_type == "Stock Reconciliation":
			fields = ["name", "current_serial_and_batch_bundle", "serial_and_batch_bundle"]
			or_filters["current_serial_and_batch_bundle"] = self.name

		elif self.voucher_type == "Purchase Receipt":
			fields = ["name", "rejected_serial_and_batch_bundle", "serial_and_batch_bundle"]
			or_filters["rejected_serial_and_batch_bundle"] = self.name

		if (
			self.voucher_type == "Subcontracting Receipt"
			and self.voucher_detail_no
			and not frappe.db.exists("Subcontracting Receipt Item", self.voucher_detail_no)
		):
			self.voucher_type = "Subcontracting Receipt Supplied"

		vouchers = frappe.get_all(
			self.child_table,
			fields=fields,
			filters={"docstatus": 0},
			or_filters=or_filters,
		)

		if not vouchers and self.voucher_type == "Delivery Note":
			if frappe.db.exists("Packed Item", self.voucher_detail_no):
				frappe.db.set_value("Packed Item", self.voucher_detail_no, "serial_and_batch_bundle", None)
			else:
				packed_items = frappe.get_all(
					"Packed Item",
					filters={
						"parent_detail_docname": self.voucher_detail_no,
						"serial_and_batch_bundle": self.name,
					},
					pluck="name",
				)

				for packed_item in packed_items:
					frappe.db.set_value("Packed Item", packed_item, "serial_and_batch_bundle", None)

			return

		for voucher in vouchers:
			if voucher.get("current_serial_and_batch_bundle"):
				frappe.db.set_value(self.child_table, voucher.name, "current_serial_and_batch_bundle", None)
			elif voucher.get("rejected_serial_and_batch_bundle"):
				frappe.db.set_value(self.child_table, voucher.name, "rejected_serial_and_batch_bundle", None)

			frappe.db.set_value(self.child_table, voucher.name, "serial_and_batch_bundle", None)

	def delink_reference_from_batch(self):
		batches = frappe.get_all(
			"Batch",
			fields=["name"],
			filters={"reference_name": self.name, "reference_doctype": "Serial and Batch Bundle"},
		)

		for batch in batches:
			frappe.db.set_value("Batch", batch.name, {"reference_name": None, "reference_doctype": None})

	def validate_serial_and_batch_data(self):
		if not self.voucher_no:
			frappe.throw(_("Voucher No is mandatory"))

	def before_submit(self):
		self.validate_submitted_with_its_voucher()
		self.validate_serial_and_batch_data()
		self.validate_serial_and_batch_no_for_returned()
		self.validate_returned_batch_qty()
		self.set_child_details()
		self.set_source_document_no()

	def validate_submitted_with_its_voucher(self):
		if self.flags.ignore_voucher_validation or self.type_of_transaction not in ("Inward", "Outward"):
			return

		if not self.voucher_no or self.voucher_type in (
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
			"POS Invoice",
		):
			return

		if frappe.db.get_value(self.voucher_type, self.voucher_no, "docstatus") != 1:
			return

		if not frappe.db.exists(
			"Stock Ledger Entry",
			{"serial_and_batch_bundle": self.name, "voucher_no": self.voucher_no, "is_cancelled": 0},
		):
			frappe.throw(
				_(
					"Serial and Batch Bundle {0} is not posted by {1} {2}. A bundle is submitted with the transaction it belongs to."
				).format(bold(self.name), self.voucher_type, bold(self.voucher_no))
			)

	def on_submit(self):
		self.validate_docstatus()
		self.validate_serial_nos_inventory()
		self.validate_batch_quantity()

	def validate_docstatus(self):
		for row in self.entries:
			if row.docstatus != 1:
				frappe.throw(
					_("At Row {0}: In Serial and Batch Bundle {1} must have docstatus as 1 and not 0").format(
						bold(row.idx), bold(self.name)
					)
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

	def set_source_document_no(self):
		if self.flags.ignore_validate_serial_batch:
			return

		if not self.has_serial_no and not self.has_batch_no:
			return

		if self.total_qty <= 0:
			return

		if self.has_serial_no:
			serial_nos = [d.serial_no for d in self.entries if d.serial_no]
			sn_table = frappe.qb.DocType("Serial No")
			(
				frappe.qb.update(sn_table)
				.set(sn_table.reference_doctype, self.voucher_type)
				.set(sn_table.reference_name, self.voucher_no)
				.set(sn_table.posting_date, getdate(self.posting_datetime))
				.where((sn_table.name.isin(serial_nos)) & (sn_table.reference_name.isnull()))
			).run()

		if self.has_batch_no:
			batch_nos = [d.batch_no for d in self.entries if d.batch_no]
			batch_table = frappe.qb.DocType("Batch")
			(
				frappe.qb.update(batch_table)
				.set(batch_table.reference_doctype, self.voucher_type)
				.set(batch_table.reference_name, self.voucher_no)
				.where((batch_table.name.isin(batch_nos)) & (batch_table.reference_name.isnull()))
			).run()

	def validate_serial_and_batch_inventory(self):
		self.check_future_entries_exists(is_cancelled=True)
		self.validate_batch_inventory()

	def validate_batch_inventory(self):
		if not self.has_batch_no:
			return

		batches = [d.batch_no for d in self.entries if d.batch_no]
		if not batches:
			return

		available_batches = get_auto_batch_nos(
			frappe._dict(
				{
					"item_code": self.item_code,
					"warehouse": self.warehouse,
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
				self.throw_error_message(
					_("Batch {0} is not available in the selected warehouse {1}").format(
						bold(batch_number), self.warehouse
					)
				)

	def on_cancel(self):
		self.validate_voucher_no_docstatus()
		self.validate_batch_quantity()
		self.remove_source_document_no()

	def validate_batch_quantity(self):
		# a reconciliation checks its outward bundles once its inward ones are posted
		if self.type_of_transaction != "Outward" or self.voucher_type == "Stock Reconciliation":
			return

		self.validate_future_batch_quantity()

	def validate_future_batch_quantity(self):
		if not self.has_batch_no:
			return

		batch_wise_available_qty = self.get_batchwise_available_qty()
		precision = frappe.get_precision("Serial and Batch Entry", "qty")

		for d in self.entries:
			available_qty = batch_wise_available_qty.get(d.batch_no, 0)
			if flt(available_qty, precision) < 0:
				self.throw_negative_batch(d.batch_no, available_qty, precision)

	def remove_source_document_no(self):
		if not self.has_serial_no and not self.has_batch_no:
			return

		if self.total_qty <= 0:
			return

		if self.has_serial_no:
			serial_nos = [d.serial_no for d in self.entries if d.serial_no]
			sn_table = frappe.qb.DocType("Serial No")
			(
				frappe.qb.update(sn_table)
				.set(sn_table.reference_doctype, None)
				.set(sn_table.reference_name, None)
				.set(sn_table.posting_date, None)
				.where(
					(sn_table.name.isin(serial_nos))
					& (sn_table.reference_doctype == self.voucher_type)
					& (sn_table.reference_name == self.voucher_no)
					& (sn_table.posting_date == getdate(self.posting_datetime))
				)
			).run()

		if self.has_batch_no:
			batch_nos = [d.batch_no for d in self.entries if d.batch_no]
			batch_table = frappe.qb.DocType("Batch")
			(
				frappe.qb.update(batch_table)
				.set(batch_table.reference_doctype, None)
				.set(batch_table.reference_name, None)
				.where(
					(batch_table.name.isin(batch_nos))
					& (batch_table.reference_doctype == self.voucher_type)
					& (batch_table.reference_name == self.voucher_no)
				)
			).run()

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
			bold(self.item_code),
			bold(self.warehouse),
			date_msg,
			bold(abs(flt(available_qty, precision))),
		)

		frappe.throw(
			msg,
			title=_("Negative Stock Error"),
			exc=NegativeStockError,
		)

	def get_batchwise_available_qty(self):
		posting_datetime = get_datetime(self.posting_datetime) if self.posting_datetime else None
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
		batches = [d.batch_no for d in self.entries if d.batch_no]
		sle = frappe.qb.DocType("Stock Ledger Entry")

		query = (
			frappe.qb.from_(sle)
			.select(sle.batch_no)
			.where(
				(sle.item_code == self.item_code)
				& (sle.warehouse == self.warehouse)
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
		batches = [d.batch_no for d in self.entries if d.batch_no]
		child = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(child)
			.select(child.batch_no)
			.where(
				(child.item_code == self.item_code)
				& (child.warehouse == self.warehouse)
				& (child.is_cancelled == 0)
				& (child.batch_no.isin(batches))
				& (child.docstatus == 1)
				& (child.type_of_transaction.isin(["Inward", "Outward"]))
				& (child.voucher_type != "Pick List")
			)
			.for_update()
		)

		return query, child

	def validate_voucher_no_docstatus(self):
		if self.is_cancelled:
			return

		if self.voucher_type == "POS Invoice":
			return

		child_doctype = self.voucher_type + " Item"
		mapper = {
			"Asset Capitalization": "Asset Capitalization Stock Item",
			"Asset Repair": "Asset Repair Consumed Item",
			"Stock Entry": "Stock Entry Detail",
		}.get(self.voucher_type)

		if mapper:
			child_doctype = mapper

		if self.voucher_type == "Delivery Note" and not frappe.db.exists(
			"Delivery Note Item", self.voucher_detail_no
		):
			child_doctype = "Packed Item"

		elif self.voucher_type == "Sales Invoice" and not frappe.db.exists(
			"Sales Invoice Item", self.voucher_detail_no
		):
			child_doctype = "Packed Item"

		elif self.voucher_type == "Subcontracting Receipt" and not frappe.db.exists(
			"Subcontracting Receipt Item", self.voucher_detail_no
		):
			child_doctype = "Subcontracting Receipt Supplied Item"

		if (
			frappe.db.get_value(self.voucher_type, self.voucher_no, "docstatus") == 1
			and self.voucher_detail_no
			and frappe.db.exists(child_doctype, self.voucher_detail_no)
		):
			frappe.throw(
				_("The {0} {1} is in submitted state, please cancel it first").format(
					self.voucher_type, bold(self.voucher_no)
				)
			)

	def on_trash(self):
		self.validate_voucher_no_docstatus()
		self.delink_reference_from_voucher()
		self.delink_reference_from_batch()

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


def allow_negative_stock_for_batch(batch_no):
	"""Return whether negative stock is allowed for the given batch.

	The batch-level setting takes priority: if `allow_negative_stock_for_batch`
	is enabled on the Batch, negative stock is allowed regardless of Stock Settings.
	Otherwise, fall back to the `allow_negative_stock_for_batch` Stock Setting.
	"""
	if batch_no and frappe.db.get_value("Batch", batch_no, "allow_negative_stock_for_batch"):
		return True

	return bool(frappe.db.get_single_value("Stock Settings", "allow_negative_stock_for_batch"))


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
