import collections
from collections import Counter, defaultdict
from typing import Any

import frappe
from frappe import _, _dict, bold
from frappe.model.naming import NamingSeries, parse_naming_series
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Max, Sum
from frappe.utils import (
	add_days,
	cint,
	cstr,
	flt,
	get_datetime,
	get_link_to_form,
	getdate,
	now,
	nowtime,
	parse_json,
	today,
)
from frappe.utils.csvutils import build_csv_response
from pypika import Order

from erpnext.stock.deprecated_serial_batch import DeprecatedSerialNoValuation
from erpnext.stock.valuation import FIFOValuation, round_off_if_near_zero

CONSUMED_SERIAL_NO_STOCK_ENTRY_PURPOSES = (
	"Manufacture",
	"Material Issue",
	"Repack",
	"Material Consumption for Manufacture",
)
INACTIVE_SERIAL_NO_STOCK_ENTRY_PURPOSES = ("Disassemble", "Material Receipt")


class SerialNoExistsInFutureTransactionError(frappe.ValidationError):
	pass


class SerialNoDuplicateError(frappe.ValidationError):
	pass


def get_serial_no_status(sle):
	warehouse = sle.warehouse if sle.actual_qty > 0 else None
	if warehouse:
		return "Active"

	status = get_status_for_serial_nos(sle)
	if sle.voucher_type == "Stock Entry" and sle.actual_qty < 0:
		purpose = frappe.get_cached_value("Stock Entry", sle.voucher_no, "purpose")
		if purpose in INACTIVE_SERIAL_NO_STOCK_ENTRY_PURPOSES:
			status = "Inactive"

	return status


def get_status_for_serial_nos(sle):
	status = "Inactive"
	if sle.actual_qty < 0:
		status = "Delivered"
		if sle.voucher_type == "Stock Entry":
			purpose = frappe.get_cached_value("Stock Entry", sle.voucher_no, "purpose")
			if purpose in CONSUMED_SERIAL_NO_STOCK_ENTRY_PURPOSES:
				status = "Consumed"

		if sle.is_cancelled == 1 and (
			sle.voucher_type in ["Purchase Invoice", "Purchase Receipt"] or status == "Consumed"
		):
			status = "Inactive"

	return status


class SerialBatchBundle:
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.set_item_details()
		self.process_serial_batch_ledgers()
		self.post_process()

	def process_serial_batch_ledgers(self):
		if self.item_details.has_serial_no:
			self.process_serial_no()
		elif self.item_details.has_batch_no:
			self.process_batch_no()

	def set_item_details(self):
		fields = [
			"has_batch_no",
			"has_serial_no",
			"item_name",
			"item_group",
			"serial_no_series",
			"create_new_batch",
			"batch_number_series",
		]

		self.item_details = frappe.get_cached_value("Item", self.sle.item_code, fields, as_dict=1)

	def process_serial_no(self):
		if (
			not self.sle.is_cancelled
			and self.item_details.has_serial_no == 1
			and not self.has_sll_native_entries()
		):
			self.make_serial_batch_no_bundle()

	def is_material_transfer(self):
		allowed_types = [
			"Material Transfer",
			"Send to Subcontractor",
			"Material Transfer for Manufacture",
		]

		if (
			self.sle.voucher_type == "Stock Entry"
			and not self.sle.is_cancelled
			and frappe.get_cached_value("Stock Entry", self.sle.voucher_no, "purpose") in allowed_types
		):
			return True

	def is_internal_transfer_inward(self):
		if self.sle.is_cancelled or self.sle.voucher_type not in ("Delivery Note", "Sales Invoice"):
			return False

		return bool(
			frappe.get_cached_value(self.sle.voucher_type, self.sle.voucher_no, "is_internal_customer")
		)

	def make_serial_batch_no_bundle_for_material_transfer(self):
		# The source leg's entries are SLL-native - the target leg shares the same
		# voucher_detail_no but a different warehouse and needs its own copy of the same
		# composition, qty sign flipped.
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			duplicate_location_entries_for_transfer,
		)

		duplicate_location_entries_for_transfer(self.sle)

	def make_serial_batch_no_bundle(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		self.validate_item()
		if self.sle.actual_qty > 0 and (self.is_material_transfer() or self.is_internal_transfer_inward()):
			self.make_serial_batch_no_bundle_for_material_transfer()
			return

		# The SLE's own serial_no/batch_no fields (use_serial_batch_fields flow) name an explicit
		# composition - auto-picking would silently consume a different batch than the user chose.
		# The row can carry more serials than this movement (e.g. a Subcontracting Receipt row
		# listing every transferred serial while consuming fewer), so cap at the SLE qty.
		serial_nos = get_serial_nos(self.sle.serial_no) if self.sle.get("serial_no") else None
		if serial_nos and (qty := cint(abs(flt(self.sle.actual_qty)))) and len(serial_nos) > qty:
			serial_nos = serial_nos[:qty]

		batch_nos = None
		if self.sle.get("batch_no") and not serial_nos:
			batch_nos = frappe._dict({self.sle.batch_no: abs(flt(self.sle.actual_qty))})

		entries = SerialBatchCreation(
			{
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"posting_datetime": self.sle.posting_datetime,
				"voucher_type": self.sle.voucher_type,
				"voucher_no": self.sle.voucher_no,
				"voucher_detail_no": self.sle.voucher_detail_no,
				"qty": self.sle.actual_qty,
				"type_of_transaction": "Inward" if self.sle.actual_qty > 0 else "Outward",
				"company": self.company,
				"is_rejected": self.is_rejected_entry(),
				"is_packed": self.is_packed_entry(),
				"make_bundle_from_sle": 1,
				"batch_no": self.sle.get("batch_no"),
			}
		).make_location_ledger_entries(serial_nos=serial_nos, batch_nos=batch_nos)

		if entries:
			self.apply_ledger_entries(entries)

	def validate_item(self):
		msg = ""
		if self.sle.actual_qty > 0:
			if not self.item_details.has_batch_no and not self.item_details.has_serial_no:
				msg = f"Item {self.item_code} is not a batch or serial no item"

			if self.item_details.has_serial_no and not self.item_details.serial_no_series:
				msg += f". If you want auto pick serial bundle, then kindly set Serial No Series in Item {self.item_code}"

			if (
				self.item_details.has_batch_no
				and not self.item_details.batch_number_series
				and not frappe.get_single_value("Stock Settings", "naming_series_prefix")
			):
				msg += f". If you want auto pick batch bundle, then kindly set Batch Number Series in Item {self.item_code}"

		elif self.sle.actual_qty < 0:
			if not frappe.get_single_value("Stock Settings", "auto_create_serial_batch_entries_for_outward"):
				msg += ". If you want to auto pick serial/batch entries, then kindly enable 'Auto create Serial / Batch entries for outward' in Stock Settings."

		if msg:
			error_msg = (
				f"Serial / Batch entries not set for item {self.item_code} in warehouse {self.warehouse}"
				+ msg
			)
			frappe.throw(_(error_msg))

	def apply_ledger_entries(self, entries):
		"""Composition is already persisted to Stock Location Ledger by make_location_ledger_entries -
		only the auto-created flag and the display fields on the child row still need updating."""
		self.sle.auto_created_serial_batch = 1
		self.sle.db_set({"auto_created_serial_batch": 1})

		if self.is_rejected_entry():
			return

		values_to_update = {}

		if self.sle.actual_qty < 0 and self.is_material_transfer():
			basic_rate = flt(self.sle.incoming_rate)
			ste_detail = frappe.db.get_value(
				"Stock Entry Detail",
				self.sle.voucher_detail_no,
				["additional_cost", "landed_cost_voucher_amount", "transfer_qty"],
				as_dict=True,
			)

			additional_cost = 0.0

			if ste_detail:
				additional_cost = (
					flt(ste_detail.additional_cost) + flt(ste_detail.landed_cost_voucher_amount)
				) / flt(ste_detail.transfer_qty)

			values_to_update["basic_rate"] = basic_rate
			values_to_update["valuation_rate"] = basic_rate + additional_cost

		if not frappe.get_single_value("Stock Settings", "do_not_update_serial_batch_on_auto_creation"):
			serial_nos = [d["serial_no"] for d in entries if d.get("serial_no")]
			batch_nos = list(dict.fromkeys(d["batch_no"] for d in entries if d.get("batch_no")))
			if serial_nos:
				values_to_update["serial_no"] = ",".join(cstr(sn) for sn in serial_nos)
			elif len(batch_nos) == 1:
				values_to_update["batch_no"] = batch_nos[0]

		if not values_to_update:
			return

		doctype = self.child_doctype
		name = self.sle.voucher_detail_no
		if self.is_packed_entry():
			doctype = "Packed Item"
			name = self.get_packed_item_row()

		if name:
			frappe.db.set_value(doctype, name, values_to_update)

	def get_packed_item_row(self):
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import has_bundled_entries

		candidates = frappe.get_all(
			"Packed Item",
			filters={"parent_detail_docname": self.sle.voucher_detail_no, "item_code": self.sle.item_code},
			pluck="name",
			order_by="idx asc",
		)
		if not candidates:
			return None

		for name in candidates:
			if not has_bundled_entries(self.sle.voucher_type, self.sle.voucher_no, name, self.sle.warehouse):
				return name

		return candidates[0]

	@property
	def child_doctype(self):
		child_doctype = self.sle.voucher_type + " Item"

		if self.sle.voucher_type == "Subcontracting Receipt" and self.sle.dependant_sle_voucher_detail_no:
			child_doctype = "Subcontracting Receipt Supplied Item"

		if self.sle.voucher_type == "Stock Entry":
			child_doctype = "Stock Entry Detail"

		if self.sle.voucher_type == "Asset Capitalization":
			child_doctype = "Asset Capitalization Stock Item"

		if self.sle.voucher_type == "Asset Repair":
			child_doctype = "Asset Repair Consumed Item"

		return child_doctype

	def is_rejected_entry(self):
		return is_rejected(self.sle.voucher_type, self.sle.voucher_detail_no, self.sle.warehouse)

	def is_packed_entry(self):
		if self.sle.voucher_type in ["Delivery Note", "Sales Invoice"]:
			item_code = frappe.db.get_value(
				self.sle.voucher_type + " Item",
				self.sle.voucher_detail_no,
				"item_code",
			)

			if item_code != self.sle.item_code:
				return frappe.db.get_value("Item", item_code, "is_stock_item") == 0

		return False

	def process_batch_no(self):
		if (
			not self.sle.is_cancelled
			and self.item_details.has_batch_no == 1
			and not self.has_sll_native_entries()
			and (
				(self.item_details.create_new_batch and self.sle.actual_qty > 0)
				or (
					frappe.get_single_value("Stock Settings", "auto_create_serial_batch_entries_for_outward")
					and self.sle.actual_qty < 0
				)
			)
		):
			self.make_serial_batch_no_bundle()

	def has_sll_native_entries(self):
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import has_bundled_entries

		# On voucher cancel the ledger rows are already flipped to docstatus 2 before this SLE
		# is processed, so restoring each serial's status/warehouse must read the cancelled rows.
		return has_bundled_entries(
			self.sle.voucher_type,
			self.sle.voucher_no,
			self.sle.voucher_detail_no,
			self.sle.warehouse,
			item_code=self.sle.item_code,
			include_cancelled=bool(self.sle.is_cancelled),
		)

	def get_sll_native_serial_nos(self):
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			get_serial_nos_for_voucher,
		)

		return get_serial_nos_for_voucher(
			self.sle.voucher_type,
			self.sle.voucher_no,
			self.sle.voucher_detail_no,
			self.sle.warehouse,
			item_code=self.sle.item_code,
			include_cancelled=bool(self.sle.is_cancelled),
		)

	def post_process(self):
		if not self.sle.serial_no and not self.sle.batch_no and not self.has_sll_native_entries():
			return

		if not self.sle.is_cancelled and self.has_sll_native_entries():
			# Mirrors the bundle-submit revalidation above (duplicate/already-delivered serial
			# checks) - must run before set_warehouse_and_status_in_serial_nos below flips each
			# serial's status, or an "already Delivered" reuse would pass by the time it's checked.
			from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
				validate_ledger_promotion,
			)

			validate_ledger_promotion(self.sle)

		if self.item_details.has_serial_no == 1:
			self.set_warehouse_and_status_in_serial_nos()

		if (
			self.sle.actual_qty > 0
			and self.item_details.has_serial_no == 1
			and self.item_details.has_batch_no == 1
		):
			self.set_batch_no_in_serial_nos()

	def set_warehouse_and_status_in_serial_nos(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as get_parsed_serial_nos

		if self.sle.get("auto_created_serial_batch") and self.sle.actual_qty > 0:
			return

		serial_nos = []
		if self.sle.serial_no:
			serial_nos = get_parsed_serial_nos(self.sle.serial_no)
		if not serial_nos:
			serial_nos = self.get_sll_native_serial_nos()

		if not serial_nos:
			return

		if self.sle.voucher_type == "Stock Reconciliation" and (
			self.sle.actual_qty > 0 or self.sle.is_cancelled
		):
			# On cancellation a reconciliation reverses both its legs, so the direction of either
			# reversing entry says nothing about where the serial ends up - the status has to be
			# re-derived from the ledger rows that survive the cancellation.
			self.update_serial_no_status_for_stock_reco(serial_nos)
			return

		self.update_serial_no_status_warehouse(self.sle, serial_nos)

	def get_status_for_serial_nos(self, sle):
		return get_status_for_serial_nos(sle)

	def update_serial_no_status_warehouse(self, sle, serial_nos):
		warehouse = sle.warehouse if sle.actual_qty > 0 else None

		if isinstance(serial_nos, str):
			serial_nos = [serial_nos]

		status = get_serial_no_status(sle)

		customer = None
		if sle.voucher_type in ["Sales Invoice", "Delivery Note"] and sle.actual_qty < 0:
			customer = frappe.get_cached_value(sle.voucher_type, sle.voucher_no, "customer")

		sn_table = frappe.qb.DocType("Serial No")

		query = (
			frappe.qb.update(sn_table)
			.set(sn_table.warehouse, warehouse)
			.set(
				sn_table.status,
				"Active"
				if warehouse
				else status
				if (sn_table.reference_name != sle.voucher_no or sle.is_cancelled != 1)
				else "Inactive",
			)
			.set(sn_table.company, sle.company)
			.set(sn_table.customer, customer)
			.where(sn_table.name.isin(serial_nos))
		)

		if status == "Delivered":
			warranty_period = frappe.get_cached_value("Item", sle.item_code, "warranty_period")
			if warranty_period:
				warranty_expiry_date = add_days(getdate(sle.posting_datetime), cint(warranty_period))
				query = query.set(sn_table.warranty_expiry_date, warranty_expiry_date)
				query = query.set(sn_table.warranty_period, warranty_period)
		else:
			query = query.set(sn_table.warranty_expiry_date, None)
			query = query.set(sn_table.warranty_period, 0)

		query.run()

	def update_serial_no_status_for_stock_reco(self, serial_nos):
		for serial_no in serial_nos:
			sle_doctype = frappe.qb.DocType("Stock Ledger Entry")
			sll_table = frappe.qb.DocType("Stock Location Ledger")

			query = (
				frappe.qb.from_(sle_doctype)
				.inner_join(sll_table)
				.on(
					(sle_doctype.voucher_type == sll_table.voucher_type)
					& (sle_doctype.voucher_no == sll_table.voucher_no)
					& (sle_doctype.voucher_detail_no == sll_table.voucher_detail_no)
					& (sle_doctype.warehouse == sll_table.warehouse)
					# A Stock Reconciliation's reversal and new-state legs share one voucher tuple,
					# so the SLE must only pair with SLL rows of its own direction - otherwise a
					# serial removed by the reversal leg matches the inward SLE and goes back Active.
					& (
						((sle_doctype.actual_qty < 0) & (sll_table.is_outward == 1))
						| ((sle_doctype.actual_qty >= 0) & (sll_table.is_outward == 0))
					)
				)
				.select(
					sle_doctype.warehouse,
					sle_doctype.actual_qty,
					sle_doctype.voucher_type,
					sle_doctype.voucher_no,
					sle_doctype.is_cancelled,
					sle_doctype.item_code,
					sle_doctype.posting_datetime,
					sle_doctype.company,
				)
				.where(
					(sll_table.serial_no == serial_no)
					& (sle_doctype.is_cancelled == 0)
					& (
						(sll_table.docstatus == 1)
						| ((sll_table.docstatus == 0) & (sll_table.voucher_no == self.sle.voucher_no))
					)
				)
				.orderby(sle_doctype.posting_datetime, order=Order.desc)
				.orderby(sle_doctype.creation, order=Order.desc)
				.limit(1)
			)

			sle = query.run(as_dict=1)
			if sle:
				self.update_serial_no_status_warehouse(sle[0], serial_no)
			elif self.sle.is_cancelled:
				# Nothing left anywhere for this serial no once the reconciliation is reversed -
				# an opening reconciliation being cancelled, say - so it cannot keep pointing at
				# the warehouse that reconciliation put it in.
				reversal = frappe._dict(
					{
						"warehouse": self.sle.warehouse,
						"actual_qty": -1,
						"voucher_type": self.sle.voucher_type,
						"voucher_no": self.sle.voucher_no,
						"is_cancelled": 1,
					}
				)
				self.update_serial_no_status_warehouse(reversal, serial_no)

	def set_batch_no_in_serial_nos(self):
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import get_voucher_entries

		entries = get_voucher_entries(
			self.sle.voucher_type,
			self.sle.voucher_no,
			self.sle.voucher_detail_no,
			self.sle.warehouse,
			fields=["serial_no", "batch_no"],
		)

		batch_serial_nos = {}
		for ledger in entries:
			batch_serial_nos.setdefault(ledger.batch_no, []).append(ledger.serial_no)

		for batch_no, serial_nos in batch_serial_nos.items():
			sn_table = frappe.qb.DocType("Serial No")
			(
				frappe.qb.update(sn_table)
				.set(sn_table.batch_no, batch_no)
				.where(sn_table.name.isin(serial_nos))
			).run()


class SerialNoValuation(DeprecatedSerialNoValuation):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.calculate_stock_value_change()
		self.calculate_valuation_rate()

	def calculate_stock_value_change(self):
		if flt(self.sle.actual_qty) > 0:
			self.stock_value_change = flt(self.sle.actual_qty) * flt(self.sle.incoming_rate)

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
		bundle_child = frappe.qb.DocType("Stock Location Ledger")

		def get_latest_based_on_posting_datetime():
			# Get latest inward record based on posting datetime for each serial no

			latest_posting = (
				frappe.qb.from_(bundle_child)
				.select(
					bundle_child.serial_no,
					Max(bundle_child.posting_datetime).as_("max_posting_dt"),
				)
				.where(
					(bundle_child.docstatus == 1)
					& (bundle_child.type_of_transaction == "Inward")
					& (bundle_child.qty > 0)
					& (bundle_child.item_code == self.sle.item_code)
					& (bundle_child.warehouse == self.sle.warehouse)
					& (bundle_child.serial_no.isin(serial_nos))
				)
				.groupby(bundle_child.serial_no)
			)

			# Important to exclude the current voucher to calculate correct the stock value difference
			if self.sle.voucher_no:
				latest_posting = latest_posting.where(bundle_child.voucher_no != self.sle.voucher_no)

			if self.sle.posting_datetime:
				timestamp_condition = bundle_child.posting_datetime <= self.sle.posting_datetime

				latest_posting = latest_posting.where(timestamp_condition)

			latest_posting = latest_posting.as_("latest_posting")

			return latest_posting

		def get_latest_based_on_creation(latest_posting):
			# Get latest inward record based on creation for each serial no
			latest_creation = (
				frappe.qb.from_(bundle_child)
				.join(latest_posting)
				.on(
					(latest_posting.serial_no == bundle_child.serial_no)
					& (latest_posting.max_posting_dt == bundle_child.posting_datetime)
				)
				.select(
					bundle_child.serial_no,
					Max(bundle_child.creation).as_("max_creation"),
				)
				.where(
					(bundle_child.docstatus == 1)
					& (bundle_child.type_of_transaction == "Inward")
					& (bundle_child.qty > 0)
					& (bundle_child.item_code == self.sle.item_code)
					& (bundle_child.warehouse == self.sle.warehouse)
				)
				.groupby(bundle_child.serial_no)
			).as_("latest_creation")

			return latest_creation

		latest_posting = get_latest_based_on_posting_datetime()
		latest_creation = get_latest_based_on_creation(latest_posting)

		query = (
			frappe.qb.from_(bundle_child)
			.join(latest_creation)
			.on(
				(latest_creation.serial_no == bundle_child.serial_no)
				& (latest_creation.max_creation == bundle_child.creation)
			)
			.select(
				bundle_child.serial_no,
				bundle_child.incoming_rate,
			)
		)

		result = query.run(as_list=1)

		return frappe._dict(result) if result else frappe._dict({})

	def get_serial_nos(self):
		return self.sle.get("serial_nos") or []

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
		return abs(flt(self.stock_value_change) / flt(self.sle.actual_qty))

	def get_incoming_rate_of_serial_no(self, serial_no):
		return self.serial_no_incoming_rate.get(serial_no, 0.0)


def is_rejected(voucher_type, voucher_detail_no, warehouse):
	if voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
		return warehouse == frappe.get_cached_value(
			voucher_type + " Item", voucher_detail_no, "rejected_warehouse"
		)

	return False


class BatchNoValuation:
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
			self.stock_value_change = flt(self.sle.actual_qty) * flt(self.sle.incoming_rate)
		else:
			# Serialize concurrent valuations of this (item, warehouse) on postgres. MariaDB's
			# grouped FOR UPDATE + gap locks do this via the history reads below; postgres has no
			# gap locks, and row-locking the whole history writes a lock marker on every tuple --
			# a txn-scoped advisory lock (released at commit/rollback) serializes without either.
			if frappe.db.db_type == "postgres":
				frappe.db.transaction_advisory_lock(
					("batch-valuation", self.sle.item_code, self.sle.warehouse)
				)

			self.stock_value_change = 0.0
			self.batch_avg_rate = defaultdict(float)
			self.available_qty = defaultdict(float)
			self.stock_value_differece = defaultdict(float)

			for ledger in self.get_batch_stock_before_date():
				self.stock_value_differece[ledger.batch_no] += flt(ledger.incoming_rate)
				self.available_qty[ledger.batch_no] += flt(ledger.qty)

			self.calculate_avg_rate_for_non_batchwise_valuation()
			self.set_stock_value_difference()

	def get_batch_stock_before_date(self) -> list[dict]:
		"""Batch-wise valuation prices a batch off the running qty_after_transaction/stock_value
		carried on the most recent prior Stock Location Ledger row for that batch - those running
		balances are kept correct by repost_location_balance/resync_location_balance - instead of
		re-summing the batch's whole history on every valuation call."""
		if not self.batchwise_valuation_batches:
			return []

		timestamp_condition = self.get_batch_timestamp_condition()

		entries = []
		for batch_no in self.batchwise_valuation_batches:
			balance_qty, balance_value = self.get_batch_balance(batch_no, timestamp_condition)
			entries.append(
				frappe._dict(
					{
						"batch_no": batch_no,
						"qty": balance_qty,
						"incoming_rate": balance_value,
					}
				)
			)

		return entries

	def get_batch_timestamp_condition(self):
		if not self.sle.posting_datetime:
			return ""

		child = frappe.qb.DocType("Stock Location Ledger")
		timestamp_condition = child.posting_datetime < self.sle.posting_datetime

		if sle_creation := self.get_current_sle_creation():
			timestamp_condition |= (child.posting_datetime == self.sle.posting_datetime) & (
				child.creation < sle_creation
			)
		else:
			# the current entry is not yet in the ledger and will get the
			# latest creation, so the same-timestamp entries which are
			# already in the ledger precede it
			timestamp_condition |= child.posting_datetime == self.sle.posting_datetime

		return timestamp_condition

	def get_current_sle_creation(self):
		if self.sle.get("name"):
			return self.sle.creation

		if not self.sle.get("voucher_detail_no"):
			return None

		return frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_no": self.sle.voucher_no,
				"voucher_detail_no": self.sle.voucher_detail_no,
				"warehouse": self.sle.warehouse,
				"is_cancelled": 0,
			},
			"creation",
			order_by="creation asc",
		)

	def get_batch_balance(self, batch_no, timestamp_condition):
		from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
			get_closing_balance_for_batch,
		)

		# A batch with pre-ledger (legacy) history carries it only in the closing snapshot: rows
		# inside the snapshot window hold pre-snapshot balances, so read past them and fall back
		# to the snapshot itself when no live row exists yet.
		closing = get_closing_balance_for_batch(self.sle.item_code, self.sle.warehouse, batch_no)
		row = self.get_last_location_ledger_row(batch_no, timestamp_condition, closing)
		if not row and closing:
			row = frappe._dict(qty_after_transaction=closing.actual_qty, stock_value=closing.stock_value)

		balance_qty = flt(row.qty_after_transaction) if row else 0.0
		balance_value = flt(row.stock_value) if row else 0.0
		# Never price an outgoing off a negative balance value while qty is not negative -
		# bad legacy rates (outgoing above incoming) are floored at zero, not propagated.
		if balance_value < 0 and balance_qty >= 0:
			balance_value = 0.0

		return balance_qty, balance_value

	def get_last_location_ledger_row(self, batch_no, timestamp_condition, closing):
		child = frappe.qb.DocType("Stock Location Ledger")

		conditions = (
			(child.item_code == self.sle.item_code)
			& (child.warehouse == self.sle.warehouse)
			& (child.batch_no == batch_no)
			& (child.docstatus == 1)
			& (child.type_of_transaction.isin(["Inward", "Outward"]))
			& (child.voucher_type != "Pick List")
		)

		# Important to exclude the current voucher detail no / voucher no to calculate the correct stock value difference
		if self.sle.voucher_detail_no:
			conditions &= child.voucher_detail_no != self.sle.voucher_detail_no
		elif self.sle.voucher_no:
			conditions &= child.voucher_no != self.sle.voucher_no

		if timestamp_condition:
			conditions &= timestamp_condition

		if closing:
			conditions &= child.posting_datetime > closing.posting_datetime

		query = (
			frappe.qb.from_(child)
			.select(child.qty_after_transaction, child.stock_value)
			.where(conditions)
			.orderby(child.posting_datetime, order=Order.desc)
			.orderby(child.creation, order=Order.desc)
			.limit(1)
		)
		if frappe.db.db_type != "postgres":
			query = query.for_update()

		rows = query.run(as_dict=True)
		return rows[0] if rows else None

	def prepare_batches(self):
		from erpnext.stock.utils import get_valuation_method

		self.batches = self.batch_nos
		if isinstance(self.batch_nos, dict):
			self.batches = list(self.batch_nos.keys())

		self.batchwise_valuation_batches = []
		self.non_batchwise_valuation_batches = []

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

	def get_batch_nos(self) -> dict:
		return self.sle.get("batch_nos") or frappe._dict()

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
				self.stock_value_differece[batch_no] = self.non_batchwise_balance_value[batch_no]

			stock_value_change = self.batch_avg_rate[batch_no] * ledger.qty
			self.stock_value_change += stock_value_change

			self.non_batchwise_balance_value[batch_no] -= stock_value_change
			self.non_batchwise_balance_qty[batch_no] -= ledger.qty

			if not ledger.get("name"):
				continue

			frappe.db.set_value(
				"Stock Location Ledger",
				ledger.name,
				{
					"stock_value_difference": stock_value_change,
					"incoming_rate": self.batch_avg_rate[batch_no],
				},
			)

	def set_balance_value_for_non_batchwise_valuation_batches(self):
		if hasattr(self, "prev_sle"):
			self.last_sle = self.prev_sle
		else:
			self.last_sle = self.get_last_sle_for_non_batch()

		if self.last_sle and self.last_sle.stock_queue:
			self.stock_queue = self.last_sle.stock_queue
			if isinstance(self.stock_queue, str):
				self.stock_queue = parse_json(self.stock_queue) or []

		self.set_balance_value_from_sl_entries()

	def set_balance_value_from_sl_entries(self) -> None:
		from erpnext.stock.utils import get_combine_datetime

		child = frappe.qb.DocType("Stock Location Ledger")
		batch = frappe.qb.DocType("Batch")

		posting_datetime = self.sle.posting_datetime
		if not posting_datetime and self.sle.posting_date:
			posting_datetime = get_combine_datetime(self.sle.posting_date, self.sle.posting_time)

		timestamp_condition = child.posting_datetime < posting_datetime

		if self.sle.creation:
			timestamp_condition |= (child.posting_datetime == posting_datetime) & (
				child.creation < self.sle.creation
			)

		conditions = (
			(child.item_code == self.sle.item_code)
			& (child.warehouse == self.sle.warehouse)
			& (child.batch_no.isnotnull())
			& (child.docstatus == 1)
			& (child.type_of_transaction.isin(["Inward", "Outward"]))
			& (child.batch_no.isin(self.non_batchwise_valuation_batches))
			& timestamp_condition
		)
		if self.sle.voucher_detail_no:
			conditions &= child.voucher_detail_no != self.sle.voucher_detail_no
		elif self.sle.voucher_no:
			conditions &= child.voucher_no != self.sle.voucher_no

		conditions &= child.voucher_type != "Pick List"

		# MariaDB carries a row lock on the grouped query below; on postgres the caller
		# (calculate_avg_rate) serializes via a txn-scoped advisory lock on (item, warehouse).
		query = (
			frappe.qb.from_(child)
			.inner_join(batch)
			.on(child.batch_no == batch.name)
			.select(
				child.batch_no,
				Sum(child.qty).as_("batch_qty"),
				Sum(child.stock_value_difference).as_("batch_value"),
			)
			.where(conditions)
			.groupby(child.batch_no)
		)

		# Moving Average items with no Use Batch wise Valuation but want to use batch wise valuation
		moving_avg_item_non_batch_value = False
		if valuation_method := self.get_valuation_method(self.sle.item_code):
			if valuation_method == "Moving Average" and not frappe.db.get_single_value(
				"Stock Settings", "do_not_use_batchwise_valuation"
			):
				query = query.where(batch.use_batchwise_valuation == 0)
				moving_avg_item_non_batch_value = True

		if frappe.db.db_type != "postgres":
			query = query.for_update()

		batch_data = query.run(as_dict=True)
		batch_data += self.get_closing_balances_for_non_batchwise(moving_avg_item_non_batch_value)
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

	def get_closing_balances_for_non_batchwise(self, only_non_batchwise):
		"""Snapshot qty/value for non-batchwise batches whose pre-ledger history was frozen
		into Stock Closing Balance, net of ledger rows the snapshot already absorbed."""
		from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
			get_closing_balances_for_batches,
		)

		if not self.non_batchwise_valuation_batches:
			return []

		closing_rows = get_closing_balances_for_batches(
			frappe._dict(
				item_code=self.sle.item_code,
				warehouse=self.sle.warehouse,
				batch_no=self.non_batchwise_valuation_batches,
			)
		)

		if closing_rows and only_non_batchwise:
			batchwise_flags = dict(
				frappe.get_all(
					"Batch",
					filters={"name": ("in", [batch_no for batch_no, _warehouse in closing_rows])},
					fields=["name", "use_batchwise_valuation"],
					as_list=True,
				)
			)
			closing_rows = {key: row for key, row in closing_rows.items() if not batchwise_flags.get(key[0])}

		if not closing_rows:
			return []

		absorbed = get_absorbed_availability(closing_rows, frappe._dict())

		entries = []
		for (batch_no, warehouse), row in closing_rows.items():
			absorbed_row = absorbed.get((batch_no, warehouse)) or frappe._dict()
			batch_qty = flt(row.actual_qty) - flt(absorbed_row.qty)
			batch_value = flt(row.stock_value) - flt(absorbed_row.stock_value)
			if batch_value < 0 and batch_qty >= 0:
				batch_value = 0.0

			entries.append(frappe._dict(batch_no=batch_no, batch_qty=batch_qty, batch_value=batch_value))

		return entries

	def get_last_sle_for_non_batch(self):
		sle = frappe.qb.DocType("Stock Ledger Entry")

		timestamp_condition = sle.posting_datetime < self.sle.posting_datetime

		if self.sle.creation:
			timestamp_condition |= (sle.posting_datetime == self.sle.posting_datetime) & (
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

		data = query.run(as_dict=True)

		return data[0] if data else frappe._dict()

	def get_valuation_method(self, item_code):
		from erpnext.stock.utils import get_valuation_method

		return get_valuation_method(item_code, self.sle.company)

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


def get_empty_batches_based_work_order(work_order, item_code):
	batches = get_batches_from_work_order(work_order, item_code)
	if not batches:
		return batches

	entries = get_batches_from_stock_entries(work_order, item_code)
	if not entries:
		return batches

	from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import get_batches_for_voucher

	for d in entries:
		if d.batch_no:
			batches[d.batch_no] -= d.qty
			continue

		for batch_no, qty in get_batches_for_voucher("Stock Entry", d.parent, d.name).items():
			if batch_no in batches:
				batches[batch_no] -= qty

	return batches


def get_batches_from_work_order(work_order, item_code):
	return frappe._dict(
		frappe.get_all(
			"Batch",
			fields=["name", "qty_to_produce"],
			filters={"reference_name": work_order, "item": item_code},
			as_list=1,
		)
	)


def get_batches_from_stock_entries(work_order, item_code):
	entries = frappe.get_all(
		"Stock Entry",
		filters={"work_order": work_order, "docstatus": 1, "purpose": "Manufacture"},
		fields=["name"],
	)

	return frappe.get_all(
		"Stock Entry Detail",
		fields=["name", "parent", "batch_no", "qty"],
		filters={
			"parent": ("in", [d.name for d in entries]),
			"is_finished_item": 1,
			"item_code": item_code,
		},
	)


class SerialBatchCreation:
	def __init__(self, args):
		self.set(args)
		self.set_item_details()
		self.set_other_details()

	def set(self, args):
		self.__dict__ = {}
		for key, value in args.items():
			setattr(self, key, value)
			self.__dict__[key] = value

	def get(self, key):
		return self.__dict__.get(key)

	def set_item_details(self):
		fields = [
			"has_batch_no",
			"has_serial_no",
			"item_name",
			"item_group",
			"serial_no_series",
			"create_new_batch",
			"batch_number_series",
			"description",
		]

		item_details = frappe.get_cached_value("Item", self.item_code, fields, as_dict=1)
		for key, value in item_details.items():
			setattr(self, key, value)

		self.__dict__.update(item_details)

	def set_other_details(self):
		from erpnext.stock.utils import get_combine_datetime

		if not self.get("posting_datetime"):
			if self.get("posting_date") and self.get("posting_time"):
				self.posting_datetime = get_combine_datetime(self.posting_date, self.posting_time)

		if not self.get("posting_datetime"):
			self.posting_datetime = now()
			self.__dict__["posting_datetime"] = self.posting_datetime

		if not self.get("actual_qty"):
			qty = self.get("qty") or self.get("total_qty")

			self.actual_qty = qty
			self.__dict__["actual_qty"] = self.actual_qty

		if not hasattr(self, "use_serial_batch_fields"):
			self.use_serial_batch_fields = 0

	def make_location_ledger_entries(self, serial_nos=None, batch_nos=None, rows=None):
		"""Resolves the composition (auto-picked or explicit), validates it, and persists
		directly as Stock Location Ledger rows - entries are plain in-memory dicts, never a
		saved/submitted document, since nothing downstream needs one to exist as data."""
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			upsert_draft_ledger_entries,
		)

		entries = self.resolve_entries(serial_nos=serial_nos, batch_nos=batch_nos, rows=rows)
		if not entries:
			return []

		self.validate_entries(entries)

		entries = [
			{
				"serial_no": row.serial_no,
				"batch_no": row.batch_no,
				"rack": row.get("rack"),
				"bin": row.get("bin"),
				"qty": row.qty,
				"incoming_rate": row.incoming_rate,
				"stock_value_difference": row.stock_value_difference,
			}
			for row in entries
		]
		upsert_draft_ledger_entries(
			entries,
			voucher_type=self.voucher_type,
			voucher_no=self.voucher_no,
			voucher_detail_no=self.voucher_detail_no,
			warehouse=self.warehouse,
			item_code=self.item_code,
			company=self.get("company"),
			posting_datetime=self.get("posting_datetime"),
			is_outward=self.get("ledger_is_outward"),
		)
		return entries

	def resolve_entries(self, serial_nos=None, batch_nos=None, rows=None):
		"""Auto-picks (or accepts explicit) serial/batch composition and returns it as plain
		row dicts, ready for validate_entries() - no Document involved, only the header
		attributes already set on self (item_code, warehouse, voucher_type, etc.)."""
		if rows:
			self.explicit_rows = self.resolve_explicit_rows(rows)
			return self.build_entry_rows()

		serial_nos = serial_nos or []
		batch_nos = batch_nos or []

		if serial_nos:
			self.serial_nos = serial_nos
		if batch_nos:
			self.batches = batch_nos

		if self.type_of_transaction == "Outward":
			self.set_auto_serial_batch_entries_for_outward()
		elif self.type_of_transaction == "Inward":
			self.set_auto_serial_batch_entries_for_inward()
			self.add_serial_nos_for_batch_item()

		return self.build_entry_rows()

	def resolve_explicit_rows(self, rows):
		rows = [frappe._dict(row) for row in rows]
		if self.has_serial_no and not any(row.serial_no for row in rows):
			rows = self.expand_rows_with_serial_nos(rows)

		return rows

	def expand_rows_with_serial_nos(self, rows):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos_for_outward

		expanded = []
		for row in rows:
			qty = cint(abs(flt(row.qty))) or 1
			if self.type_of_transaction == "Outward":
				kwargs = frappe._dict(
					{
						"item_code": self.item_code,
						"warehouse": self.warehouse,
						"qty": qty,
						"based_on": frappe.get_single_value(
							"Stock Settings", "pick_serial_and_batch_based_on"
						),
						"ignore_serial_nos": [d.serial_no for d in expanded],
					}
				)
				if row.batch_no:
					kwargs["batches"] = row.batch_no

				serial_nos = get_serial_nos_for_outward(kwargs)
			else:
				self.batch_no = row.batch_no
				self.actual_qty = qty
				serial_nos = self.get_auto_created_serial_nos()

			for serial_no in serial_nos:
				expanded.append(frappe._dict(row, serial_no=serial_no, qty=1))

		return expanded

	def add_serial_nos_for_batch_item(self):
		if not (self.has_serial_no and self.has_batch_no):
			return

		if not self.get("serial_nos") and self.get("batches"):
			batches = list(self.get("batches").keys())
			if len(batches) == 1:
				self.batch_no = batches[0]
				self.serial_nos = self.get_auto_created_serial_nos()

	def set_auto_serial_batch_entries_for_outward(self):
		from erpnext.stock.doctype.batch.batch import get_available_batches
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos_for_outward

		kwargs = frappe._dict(
			{
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"qty": abs(self.actual_qty) if self.actual_qty else 0,
				"based_on": frappe.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
			}
		)

		if self.get("ignore_serial_nos"):
			kwargs["ignore_serial_nos"] = self.ignore_serial_nos

		if (
			self.has_serial_no
			and self.has_batch_no
			and not self.get("serial_nos")
			and self.get("batches")
			and len(self.get("batches")) == 1
		):
			# If only one batch is available and no serial no is available
			kwargs["batches"] = next(iter(self.get("batches").keys()))
			self.serial_nos = get_serial_nos_for_outward(kwargs)
		elif self.has_serial_no and not self.get("serial_nos"):
			self.serial_nos = get_serial_nos_for_outward(kwargs)
		elif not self.has_serial_no and self.has_batch_no and not self.get("batches"):
			if self.get("posting_datetime"):
				kwargs["posting_datetime"] = self.get("posting_datetime")

			self.batches = get_available_batches(kwargs)

	def set_auto_serial_batch_entries_for_inward(self):
		if (self.get("batches") and self.has_batch_no) or (self.get("serial_nos") and self.has_serial_no):
			if self.use_serial_batch_fields and self.get("serial_nos"):
				self.make_serial_no_if_not_exists()

			return

		self.batch_no = None
		if self.has_batch_no:
			self.batch_no = self.create_batch()

		if self.has_serial_no:
			self.serial_nos = self.get_auto_created_serial_nos()
		else:
			self.batches = frappe._dict({self.batch_no: abs(self.actual_qty)})

	def make_serial_no_if_not_exists(self):
		non_exists_serial_nos = []
		for row in self.serial_nos:
			if not frappe.db.exists("Serial No", row):
				non_exists_serial_nos.append(row)

		if non_exists_serial_nos:
			self.make_serial_nos(non_exists_serial_nos)

	def make_serial_nos(self, serial_nos):
		serial_nos_details = []
		batch_no = None
		if self.batches:
			batch_no = next(iter(self.batches.keys()))

		for serial_no in serial_nos:
			serial_nos_details.append(
				(
					serial_no,
					serial_no,
					now(),
					now(),
					frappe.session.user,
					frappe.session.user,
					self.warehouse,
					self.company,
					self.item_code,
					self.item_name,
					self.description,
					"Active",
					batch_no,
				)
			)

		if serial_nos_details:
			fields = [
				"name",
				"serial_no",
				"creation",
				"modified",
				"owner",
				"modified_by",
				"warehouse",
				"company",
				"item_code",
				"item_name",
				"description",
				"status",
				"batch_no",
			]

			frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	def build_entry_rows(self):
		"""Turns the resolved serial_nos/batches into plain row dicts (idx-ordered), shaped for
		insertion into Stock Location Ledger."""
		incoming_rate = self.get("incoming_rate")

		standard_rate = self.get_standard_cost_rate()
		if standard_rate is not None:
			# Standard Cost values every serial/batch at the same rate, so the entries must
			# carry the standard rate (not the document/billed rate) to stay consistent with
			# the standard-valued Stock Ledger Entry.
			incoming_rate = standard_rate
			self.serial_nos_valuation = None
			self.batches_valuation = None

		precision = frappe.get_precision("Stock Location Ledger", "qty")
		if rows := self.get("explicit_rows"):
			return self.build_rows_from_explicit(rows, incoming_rate, precision)

		entries = []
		if self.get("serial_nos"):
			serial_no_wise_batch = frappe._dict({})
			if self.has_batch_no:
				serial_no_wise_batch = get_serial_nos_batch(self.serial_nos)

			qty = -1 if self.type_of_transaction == "Outward" else 1
			for idx, serial_no in enumerate(self.serial_nos, start=1):
				if self.get("serial_nos_valuation"):
					incoming_rate = self.get("serial_nos_valuation").get(serial_no)

				entries.append(
					frappe._dict(
						{
							"idx": idx,
							"serial_no": serial_no,
							"qty": qty,
							"batch_no": serial_no_wise_batch.get(serial_no) or self.get("batch_no"),
							"incoming_rate": incoming_rate,
						}
					)
				)

		elif self.get("batches"):
			for idx, (batch_no, batch_qty) in enumerate(self.batches.items(), start=1):
				if self.get("batches_valuation"):
					incoming_rate = self.get("batches_valuation").get(batch_no)

				entries.append(
					frappe._dict(
						{
							"idx": idx,
							"batch_no": batch_no,
							"qty": flt(batch_qty, precision)
							* (-1 if self.type_of_transaction == "Outward" else 1),
							"incoming_rate": incoming_rate,
						}
					)
				)

		return entries

	def build_rows_from_explicit(self, rows, incoming_rate, precision):
		sign = -1 if self.type_of_transaction == "Outward" else 1
		entries = []
		for idx, row in enumerate(rows, start=1):
			qty = 1 if row.get("serial_no") else flt(row.get("qty"), precision) or 1
			entries.append(
				frappe._dict(
					{
						"idx": idx,
						"serial_no": row.get("serial_no"),
						"batch_no": row.get("batch_no"),
						"rack": row.get("rack"),
						"bin": row.get("bin"),
						"qty": qty * sign,
						"incoming_rate": incoming_rate,
					}
				)
			)

		return entries

	def child_table(self):
		"""The per-voucher-type child doctype whose rows carry the item detail this set of
		entries belongs to."""
		if self.voucher_type == "Job Card":
			return None

		parent_child_map = {
			"Asset Capitalization": "Asset Capitalization Stock Item",
			"Asset Repair": "Asset Repair Consumed Item",
			"Quotation": "Packed Item",
			"Stock Entry": "Stock Entry Detail",
		}

		return parent_child_map.get(self.voucher_type, f"{self.voucher_type} Item")

	def throw_error_message(self, message, exception=frappe.ValidationError):
		frappe.throw(_(message), exception, title=_("Error"))

	def validate_entries(self, entries):
		"""Validation/valuation chain run before entries are written to Stock Location Ledger.
		Duplicate-serial and future-entry checks are deliberately not part of this - they run at
		promotion time instead, via validate_ledger_promotion()."""
		if (self.has_serial_no or self.has_batch_no) and not frappe.db.get_single_value(
			"Stock Settings", "enable_serial_and_batch_no_for_item"
		):
			frappe.throw(
				_(
					"Please check the 'Activate Serial and Batch No for Item' checkbox in the {0} to make serial/batch entries for the item."
				).format(get_link_to_form("Stock Settings", "Stock Settings")),
				title=_("Serial and Batch No for Item Disabled"),
			)

		self.fill_missing_batch_no(entries)
		self.validate_serial_and_batch_no(entries)
		self.validate_duplicate_serial_and_batch_no(entries)

		if self.type_of_transaction == "Maintenance":
			return

		if (
			self.has_serial_no
			and self.type_of_transaction == "Outward"
			and self.voucher_type != "Stock Reconciliation"
		):
			self.validate_serial_no_status(entries)

			if self.voucher_type == "POS Invoice":
				self.validate_pos_reserved_serial_nos(entries)

		self.set_is_outward(entries)
		self.calculate_total_qty(entries)
		self.set_warehouse_on_entries(entries)

		if self.voucher_type != "Stock Entry" or not self.get("voucher_no"):
			self.set_incoming_rate(entries)

		self.calculate_qty_and_amount(entries)
		self.set_child_details(entries)

	def fill_missing_batch_no(self, entries):
		if not (self.has_serial_no and self.has_batch_no):
			return

		has_no_batch = any(not d.batch_no for d in entries)
		if not has_no_batch:
			return

		serial_nos = [d.serial_no for d in entries if d.serial_no]
		serial_no_batch = frappe._dict(
			frappe.get_all(
				"Serial No", filters={"name": ("in", serial_nos)}, fields=["name", "batch_no"], as_list=True
			)
		)

		for row in entries:
			if not row.batch_no:
				row.batch_no = serial_no_batch.get(row.serial_no)

	def validate_serial_and_batch_no(self, entries):
		if (
			self.item_code
			and not self.has_serial_no
			and not self.has_batch_no
			and not any(row.get("rack") or row.get("bin") for row in entries)
		):
			frappe.throw(_("The Item {0} does not have Serial No or Batch No").format(self.item_code))

		serial_nos = []
		batch_nos = []
		serial_batches = {}
		for row in entries:
			if not row.qty and not row.serial_no and (row.batch_no or row.get("rack") or row.get("bin")):
				if self.voucher_type == "Stock Reconciliation" and self.type_of_transaction == "Inward":
					continue

				if row.batch_no:
					frappe.throw(
						_("At row {0}: Qty is mandatory for the batch {1}").format(
							bold(row.idx), bold(row.batch_no)
						)
					)

				frappe.throw(_("At row {0}: Qty is mandatory").format(bold(row.idx)))

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

			if row.batch_no and not row.serial_no:
				batch_nos.append(row.batch_no)

			if row.serial_no and row.batch_no and self.type_of_transaction == "Outward":
				serial_batches.setdefault(row.serial_no, row.batch_no)

		if serial_nos:
			self.validate_incorrect_serial_nos(serial_nos)
		elif batch_nos:
			self.validate_incorrect_batch_nos(batch_nos)

		if serial_batches:
			self.validate_serial_batch_match(serial_batches)

	def validate_serial_batch_match(self, serial_batches):
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
				self.throw_error_message(
					f"Serial No {bold(serial_no)} does not belong to Batch No {bold(batch_no)}"
				)

	def validate_incorrect_serial_nos(self, serial_nos):
		incorrect_serial_nos = frappe.get_all(
			"Serial No",
			filters={"name": ("in", serial_nos), "item_code": ("!=", self.item_code)},
			fields=["name"],
		)

		if incorrect_serial_nos:
			incorrect_serial_nos = ", ".join([d.name for d in incorrect_serial_nos])
			self.throw_error_message(
				f"Serial Nos {bold(incorrect_serial_nos)} does not belong to Item {bold(self.item_code)}"
			)

	def validate_incorrect_batch_nos(self, batch_nos):
		incorrect_batch_nos = frappe.get_all(
			"Batch", filters={"name": ("in", batch_nos), "item": ("!=", self.item_code)}, fields=["name"]
		)

		if incorrect_batch_nos:
			incorrect_batch_nos = ", ".join([d.name for d in incorrect_batch_nos])
			self.throw_error_message(
				f"Batch Nos {bold(incorrect_batch_nos)} does not belong to Item {bold(self.item_code)}"
			)

	def validate_duplicate_serial_and_batch_no(self, entries):
		serial_nos = []
		batch_nos = []

		for row in entries:
			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no and not row.serial_no:
				batch_nos.append(row.batch_no)

		if serial_nos:
			for key, value in collections.Counter(serial_nos).items():
				if value > 1:
					self.throw_error_message(f"Duplicate Serial No {key} found")

		if batch_nos:
			for key, value in collections.Counter(batch_nos).items():
				if value > 1:
					self.throw_error_message(f"Duplicate Batch No {key} found")

	def validate_serial_no_status(self, entries):
		# A consolidated Sales Invoice replays POS sales that were each validated (including
		# the POS double-sell check) at their own submit; the serial statuses already reflect
		# that intra-day sequence, so re-validating here would reject legitimate resales.
		if self.voucher_type == "Sales Invoice" and frappe.get_cached_value(
			"Sales Invoice", self.get("voucher_no"), "is_consolidated"
		):
			return

		serial_nos = [d.serial_no for d in entries if d.serial_no]
		invalid_serial_nos = frappe.get_all(
			"Serial No",
			filters={"name": ("in", serial_nos), "warehouse": ("!=", self.warehouse)},
			pluck="name",
		)

		if invalid_serial_nos:
			msg = _(
				"You cannot outward the following {0} as they are either Delivered, Inactive or located in a different warehouse."
			).format(_("Serial Nos") if len(invalid_serial_nos) > 1 else _("Serial No"))
			msg += "<hr>"
			msg += ", ".join(sn for sn in invalid_serial_nos)
			frappe.throw(msg)

	def validate_pos_reserved_serial_nos(self, entries):
		"""A POS Invoice moves no stock until consolidation, so the warehouse check above can't
		catch a serial already sold on another open POS Invoice - check those directly."""
		serial_nos = [d.serial_no for d in entries if d.serial_no]
		if not serial_nos:
			return

		reserved = get_reserved_serial_nos_for_pos(
			frappe._dict(
				{
					"item_code": self.item_code,
					"warehouse": self.warehouse,
					"ignore_voucher_nos": [self.get("voucher_no") or ""],
				}
			)
		)

		if sold := set(serial_nos) & set(reserved):
			frappe.throw(
				_("The following {0} already sold on another POS Invoice: {1}").format(
					_("Serial Nos") if len(sold) > 1 else _("Serial No"), ", ".join(sorted(sold))
				)
			)

	def set_is_outward(self, entries):
		for row in entries:
			if self.type_of_transaction == "Outward" and row.qty > 0:
				row.qty *= -1
			elif self.type_of_transaction == "Inward" and row.qty < 0:
				row.qty *= -1

			row.is_outward = 1 if self.type_of_transaction == "Outward" else 0

	def calculate_total_qty(self, entries):
		total_qty = 0.0
		for d in entries:
			d.qty = 1 if self.has_serial_no and abs(d.qty) > 1 else abs(d.qty) if d.qty else 0
			d.stock_value_difference = (
				abs(d.get("stock_value_difference")) if d.get("stock_value_difference") else 0
			)
			if self.type_of_transaction == "Outward":
				d.qty *= -1
				d.stock_value_difference *= -1

			total_qty += flt(d.qty)

		return total_qty

	def set_warehouse_on_entries(self, entries):
		for row in entries:
			if row.get("warehouse") != self.warehouse:
				row.warehouse = self.warehouse

	def set_incoming_rate(self, entries):
		if self.type_of_transaction not in ["Inward", "Outward"] or self.voucher_type in [
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
		]:
			return

		# A plain item's rack/bin rows carry no valuation of their own - rates are overlaid
		# from the Stock Ledger Entry when the drafts are reconciled at posting.
		if not (self.has_serial_no or self.has_batch_no):
			return

		if return_against := self.get_return_against():
			self.set_valuation_rate_for_return_entry(entries, return_against)
		elif self.type_of_transaction == "Outward":
			self.set_incoming_rate_for_outward_transaction(entries)
		else:
			self.set_incoming_rate_for_inward_transaction(entries)

	def get_return_against(self):
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
			and self.get("voucher_no")
		):
			voucher_details = frappe.db.get_value(
				self.voucher_type, self.voucher_no, ["is_return", "return_against"], as_dict=True
			)
			if voucher_details and voucher_details.get("is_return") and voucher_details.get("return_against"):
				return voucher_details.get("return_against")

		return None

	def set_valuation_rate_for_return_entry(self, entries, return_against):
		if valuation_details := self.get_valuation_rate_for_return_entry(return_against):
			for row in entries:
				if valuation_details:
					self.validate_returned_serial_batch_no(return_against, row, valuation_details)

				if row.serial_no:
					valuation_rate = valuation_details["serial_nos"].get(row.serial_no)
				else:
					valuation_rate = valuation_details["batches"].get(row.batch_no)

				if frappe.flags.through_repost_item_valuation and not valuation_rate:
					# if different serial nos / batches are returned
					if row.serial_no:
						serial_nos = sorted(list(valuation_details["serial_nos"].keys()))
						valuation_rate = valuation_details["serial_nos"].get(serial_nos[cint(row.idx) - 1])
					else:
						batches = sorted(list(valuation_details["batches"].keys()))
						valuation_rate = valuation_details["batches"].get(batches[cint(row.idx) - 1])

				row.incoming_rate = flt(valuation_rate)
				row.stock_value_difference = flt(row.qty) * flt(row.incoming_rate)

		elif self.type_of_transaction == "Inward":
			self.set_incoming_rate_for_inward_transaction(entries)

	def validate_returned_serial_batch_no(self, return_against, row, original_inv_details):
		if frappe.flags.through_repost_item_valuation and not frappe.in_test:
			return

		if row.serial_no and row.serial_no not in original_inv_details["serial_nos"]:
			self.throw_error_message(
				_(
					"Serial No {0} is not present in the {1} {2}, hence you can't return it against the {1} {2}"
				).format(bold(row.serial_no), self.voucher_type, bold(return_against))
			)

		if row.batch_no and row.batch_no not in original_inv_details["batches"]:
			self.throw_error_message(
				_(
					"Batch No {0} is not present in the original {1} {2}, hence you can't return it against the {1} {2}"
				).format(bold(row.batch_no), self.voucher_type, bold(return_against))
			)

	def get_valuation_rate_for_return_entry(self, return_against):
		"""Returns the original transaction's incoming rate per serial no / batch. Composition
		lives in Stock Location Ledger; the denormalised Stock Ledger Entry serial_no/batch_no
		columns are only populated by the use_serial_batch_fields path, so they are the fallback
		rather than the source."""
		from erpnext.controllers.sales_and_purchase_return import get_warehouses_for_return

		if not self.get("voucher_detail_no"):
			return {}

		if not (self.has_serial_no or self.has_batch_no):
			return {}

		field = {
			"Sales Invoice": "sales_invoice_item",
			"Purchase Invoice": "purchase_invoice_item",
			"Delivery Note": "dn_detail",
			"Purchase Receipt": "purchase_receipt_item",
		}.get(self.voucher_type)

		return_against_voucher_detail_no = frappe.db.get_value(
			self.child_table(), self.voucher_detail_no, field
		)

		if not return_against_voucher_detail_no and self.voucher_type in ("Delivery Note", "Sales Invoice"):
			return_against_voucher_detail_no = self.get_return_against_packed_item(field)

		# Added to handle rejected warehouse case
		return_warehouse = None
		if self.voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
			warehouses = get_warehouses_for_return(self.voucher_type, return_against_voucher_detail_no)
			if self.warehouse in warehouses:
				return_warehouse = self.warehouse

		valuation_details = self.get_returned_against_composition(
			return_against, return_against_voucher_detail_no, return_warehouse
		)
		if not (valuation_details["serial_nos"] or valuation_details["batches"]):
			valuation_details = self.get_returned_against_composition_from_sle(
				return_against, return_against_voucher_detail_no, return_warehouse
			)

		if not (valuation_details["serial_nos"] or valuation_details["batches"]):
			return {}

		return valuation_details

	def get_return_against_packed_item(self, field):
		"""Resolve the original DN/SI Item when a return bundle's voucher_detail_no is the Packed Item."""
		parent_detail_docname = frappe.db.get_value(
			"Packed Item", self.voucher_detail_no, "parent_detail_docname"
		)
		if not parent_detail_docname:
			return

		return frappe.db.get_value(self.child_table(), parent_detail_docname, field)

	def get_returned_against_composition(self, return_against, voucher_detail_no, return_warehouse):
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			get_serial_batch_valuation_details,
		)

		valuation_details = frappe._dict({"serial_nos": defaultdict(float), "batches": defaultdict(float)})
		for d in get_serial_batch_valuation_details(
			self.voucher_type,
			return_against,
			voucher_detail_no,
			return_warehouse,
			item_code=self.item_code,
		):
			if d.serial_no:
				valuation_details["serial_nos"][d.serial_no] = d.incoming_rate
			if d.batch_no:
				valuation_details["batches"][d.batch_no] = d.incoming_rate

		return valuation_details

	def get_returned_against_composition_from_sle(self, return_against, voucher_detail_no, return_warehouse):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		valuation_details = frappe._dict({"serial_nos": defaultdict(float), "batches": defaultdict(float)})

		sle = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(sle)
			.select(sle.serial_no, sle.batch_no, sle.incoming_rate)
			.where(
				(sle.voucher_no == return_against)
				& (sle.voucher_detail_no == voucher_detail_no)
				& (sle.item_code == self.item_code)
				& (sle.is_cancelled == 0)
			)
		)

		if return_warehouse:
			query = query.where(sle.warehouse == return_warehouse)

		for d in query.run(as_dict=True):
			if d.serial_no:
				for serial_no in get_serial_nos(d.serial_no):
					valuation_details["serial_nos"][serial_no] = d.incoming_rate
			elif d.batch_no:
				valuation_details["batches"][d.batch_no] = d.incoming_rate

		return valuation_details

	def set_incoming_rate_for_outward_transaction(self, entries):
		from erpnext.stock.utils import get_valuation_method

		sle = self.get_sle_for_outward_transaction(entries)

		if self.has_serial_no:
			sn_obj = SerialNoValuation(sle=sle, item_code=self.item_code, warehouse=self.warehouse)
		else:
			sn_obj = BatchNoValuation(sle=sle, item_code=self.item_code, warehouse=self.warehouse)

		stock_queue = []
		if hasattr(sn_obj, "stock_queue") and sn_obj.stock_queue:
			stock_queue = parse_json(sn_obj.stock_queue)

		val_method = get_valuation_method(self.item_code, self.get("company"))

		for d in entries:
			if self.has_serial_no:
				d.incoming_rate = abs(sn_obj.serial_no_incoming_rate.get(d.serial_no, 0.0))
			else:
				actual_qty = d.qty
				if (
					stock_queue
					and val_method == "FIFO"
					and d.batch_no in sn_obj.non_batchwise_valuation_batches
				):
					if actual_qty < 0:
						stock_queue = FIFOValuation(stock_queue)
						_prev_qty, prev_stock_value = stock_queue.get_total_stock_and_value()

						stock_queue.remove_stock(qty=abs(actual_qty))
						_qty, stock_value = stock_queue.get_total_stock_and_value()

						stock_value_difference = stock_value - prev_stock_value
						d.incoming_rate = abs(flt(stock_value_difference) / abs(flt(actual_qty)))
						stock_queue = stock_queue.state
					else:
						d.incoming_rate = abs(flt(sn_obj.batch_avg_rate.get(d.batch_no)))
						stock_queue.append([d.qty, d.incoming_rate])
				else:
					d.incoming_rate = abs(flt(sn_obj.batch_avg_rate.get(d.batch_no)))

			d.stock_value_difference = flt(d.qty) * flt(d.incoming_rate)

	def get_sle_for_outward_transaction(self, entries):
		return frappe._dict(
			{
				"posting_datetime": self.posting_datetime,
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"company": self.get("company"),
				"serial_nos": [row.serial_no for row in entries if row.serial_no],
				"batch_nos": {row.batch_no: row for row in entries if row.batch_no},
				"voucher_type": self.voucher_type,
				"voucher_detail_no": self.get("voucher_detail_no"),
				"actual_qty": self.calculate_total_qty(entries),
				"creation": None,
			}
		)

	def set_incoming_rate_for_inward_transaction(self, entries):
		from erpnext.stock.utils import get_valuation_method

		valuation_method = get_valuation_method(self.item_code, self.get("company"))

		valuation_field = "valuation_rate"
		if self.voucher_type in ["Sales Invoice", "Delivery Note", "Quotation"]:
			valuation_field = "incoming_rate"

		if self.voucher_type == "POS Invoice":
			valuation_field = "rate"

		rate = 0.0
		child_table = self.child_table()

		if self.voucher_type == "Subcontracting Receipt":
			if not self.get("voucher_detail_no"):
				return
			elif frappe.db.exists("Subcontracting Receipt Supplied Item", self.voucher_detail_no):
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Supplied Item"
			else:
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Item"

		if not rate and self.get("voucher_detail_no") and self.get("voucher_no"):
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
				"name": ("in", [d.batch_no for d in entries if d.batch_no]),
				"use_batchwise_valuation": 0,
			},
			pluck="name",
		)

		set_valuation_rate_for_rejected_materials = frappe.db.get_single_value(
			"Buying Settings", "set_valuation_rate_for_rejected_materials"
		)

		precision = frappe.get_precision("Stock Location Ledger", "incoming_rate")
		for d in entries:
			fifo_batch_wise_val = True
			if valuation_method == "FIFO" and d.batch_no in batches:
				fifo_batch_wise_val = False

			if self.get("is_rejected") and not set_valuation_rate_for_rejected_materials:
				rate = 0.0
			elif (
				(flt(d.get("incoming_rate"), precision) == flt(rate, precision))
				and not stock_queue
				and fifo_batch_wise_val
				and d.qty
				and d.get("stock_value_difference")
			):
				continue

			if is_packed_item and d.get("incoming_rate"):
				rate = d.incoming_rate

			d.incoming_rate = flt(rate)
			if d.qty:
				d.stock_value_difference = flt(d.qty) * d.incoming_rate

			if valuation_method == "FIFO" and d.batch_no in batches and d.incoming_rate is not None:
				stock_queue.append([d.qty, d.incoming_rate])

	def calculate_qty_and_amount(self, entries):
		total_amount = 0.0
		total_qty = 0.0

		for row in entries:
			rate = flt(row.incoming_rate)
			row.stock_value_difference = flt(row.qty) * rate
			total_amount += flt(row.qty) * rate
			total_qty += flt(row.qty)

		return total_qty, (flt(total_amount) / flt(total_qty) if total_qty else 0.0)

	def set_child_details(self, entries):
		for row in entries:
			for field in [
				"warehouse",
				"posting_datetime",
				"voucher_type",
				"voucher_no",
				"voucher_detail_no",
				"type_of_transaction",
				"item_code",
			]:
				value = self.get(field)
				if not row.get(field) or row.get(field) != value:
					row[field] = value

	def validate_serial_nos_duplicate(self, entries):
		"""Guards against inwarding the same serial no twice. Called from
		validate_ledger_promotion(), when the ledger entries are promoted on voucher submit."""
		if self.voucher_type in ["POS Invoice", "Pick List"]:
			return

		if not self.warehouse:
			return

		if not (self.has_serial_no and self.type_of_transaction == "Inward"):
			return

		serial_nos = [d.serial_no for d in entries if d.serial_no]
		kwargs = frappe._dict(
			{
				"item_code": self.item_code,
				"posting_datetime": self.posting_datetime,
				"serial_nos": serial_nos,
				"voucher_no": self.get("voucher_no"),
			}
		)

		if self.voucher_type == "Stock Reconciliation":
			# Reconciling a serial no that is already in stock is the normal case - its reversal
			# leg takes the serial out at the same instant this leg puts it back. Only this row's
			# own new-state entries are excluded, so the reversal still counts and a serial the
			# reconciliation does not remove is still reported as a duplicate.
			kwargs["ignore_voucher_detail_no"] = self.get("voucher_detail_no")
			kwargs["ignore_is_outward"] = 0
		elif self.get("returned_against"):
			kwargs["ignore_voucher_detail_no"] = self.get("voucher_detail_no")

		available_serial_nos = get_available_serial_nos(kwargs)
		for data in available_serial_nos:
			if data.serial_no in serial_nos:
				self.throw_error_message(
					f"Serial No {bold(data.serial_no)} is already present in the warehouse {bold(data.warehouse)}.",
					SerialNoDuplicateError,
				)

		if (
			self.voucher_type == "Stock Entry"
			and self.type_of_transaction == "Inward"
			and frappe.get_cached_value("Stock Entry", self.get("voucher_no"), "purpose")
			in ["Manufacture", "Repack"]
		):
			delivered_serial_nos = frappe.get_all(
				"Serial No", filters={"name": ("in", serial_nos), "status": "Delivered"}, pluck="name"
			)

			if delivered_serial_nos:
				if len(delivered_serial_nos) == 1:
					frappe.throw(
						_(
							"Serial No {0} is already Delivered. You cannot use it again in Manufacture / Repack entry."
						).format(bold(delivered_serial_nos[0]))
					)
				else:
					frappe.throw(
						_(
							"Serial Nos {0} are already Delivered. You cannot use them again in Manufacture / Repack entry."
						).format(bold(", ".join(delivered_serial_nos)))
					)

	def validate_existing_serial_nos(self, entries):
		if self.type_of_transaction == "Outward" or not self.has_serial_no:
			return

		if frappe.get_single_value("Stock Settings", "allow_existing_serial_no"):
			return

		if self.voucher_type not in ["Purchase Receipt", "Purchase Invoice", "Stock Entry"]:
			return

		if self.voucher_type == "Stock Entry" and frappe.get_cached_value(
			"Stock Entry", self.get("voucher_no"), "purpose"
		) in ["Material Transfer", "Send to Subcontractor", "Material Transfer for Manufacture"]:
			return

		serial_nos = [d.serial_no for d in entries if d.serial_no]
		if not serial_nos:
			return

		data = frappe.get_all(
			"Stock Location Ledger",
			filters={"serial_no": ("in", serial_nos), "docstatus": 1, "qty": ("<", 0)},
			fields=["serial_no", "voucher_type", "voucher_no"],
		)

		for row in data:
			frappe.throw(
				_(
					"You cannot process the serial number {0} as it has already been used in the {1} {2}. If you want to inward the same serial number multiple times, then enable 'Allow existing Serial No to be Manufactured/Received again' in the {3}"
				).format(
					bold(row.serial_no),
					row.voucher_type,
					get_link_to_form(row.voucher_type, row.voucher_no),
					get_link_to_form("Stock Settings", "Stock Settings"),
				)
			)

	def check_future_entries_exists(self, entries, is_cancelled=False):
		"""Blocks a backdated submit/cancel when a later Stock Reconciliation (or, for
		serial/batch items, any later movement) exists for the same item - a Stock
		Reconciliation freezes qty as of its own posting_datetime, so an earlier change
		would retroactively invalidate the snapshot it took. Reads Stock Location Ledger
		directly."""
		if self.get("via_landed_cost_voucher"):
			return

		serial_nos = []
		batches = []

		if self.voucher_type == "Stock Reconciliation":
			serial_nos, batches = self.get_serial_nos_for_validate(entries, is_cancelled=is_cancelled)
		else:
			batches = [d.batch_no for d in entries if d.batch_no]

		if self.voucher_type != "Stock Reconciliation" and self.has_serial_no:
			serial_nos = [d.serial_no for d in entries if d.serial_no]

		if self.has_batch_no and not self.has_serial_no and not batches:
			return

		table = frappe.qb.DocType("Stock Location Ledger")

		future_entries = (
			frappe.qb.from_(table)
			.select(
				table.serial_no,
				table.batch_no,
				table.voucher_type,
				table.voucher_no,
			)
			.distinct()
			.where(
				(table.item_code == self.item_code)
				& (table.docstatus == 1)
				& (table.type_of_transaction.isin(["Inward", "Outward"]))
				& (table.posting_datetime > self.posting_datetime)
			)
		)

		if self.get("voucher_detail_no"):
			future_entries = future_entries.where(table.voucher_detail_no != self.voucher_detail_no)
		elif self.get("voucher_no"):
			future_entries = future_entries.where(table.voucher_no != self.voucher_no)

		if self.has_batch_no and not self.has_serial_no:
			future_entries = future_entries.where(table.voucher_type == "Stock Reconciliation")

		if serial_nos:
			future_entries = future_entries.where(
				(table.serial_no.isin(serial_nos))
				| ((table.warehouse == self.warehouse) & (table.voucher_type == "Stock Reconciliation"))
			)
		elif self.has_serial_no:
			future_entries = future_entries.where(
				(table.warehouse == self.warehouse) & (table.voucher_type == "Stock Reconciliation")
			)
		elif batches:
			future_entries = future_entries.where(
				(table.batch_no.isin(batches)) & (table.warehouse == self.warehouse)
			)

		future_entries = future_entries.run(as_dict=True)

		if future_entries:
			if self.has_serial_no:
				title = "Serial No Exists In Future Transaction(s)"
			else:
				title = "Batches Exists In Future Transaction(s)"

			msg = """Since the stock transactions exists
				for future dates, cancel it first. For Serial/Batch,
				if you want to make a backdated transaction,
				avoid using stock transactions.
				For more details about the transaction,
				please refer to the list below.
			"""

			msg += "<br><br><ul>"

			for d in future_entries:
				if self.has_serial_no:
					msg += f"<li>{d.serial_no} in {get_link_to_form(d.voucher_type, d.voucher_no)}</li>"
				else:
					msg += f"<li>{d.batch_no} in {get_link_to_form(d.voucher_type, d.voucher_no)}</li>"
			msg += "</li></ul>"

			frappe.throw(_(msg), title=_(title), exc=SerialNoExistsInFutureTransactionError)

	def get_serial_nos_for_validate(self, entries, is_cancelled=False):
		serial_nos = [d.serial_no for d in entries if d.serial_no]
		batches = [d.batch_no for d in entries if d.batch_no]

		skip_serial_nos, skip_batches = self.get_skip_serial_nos_for_stock_reconciliation()

		serial_nos = list(set(sorted(serial_nos)) - set(sorted(skip_serial_nos)))
		batch_nos = list(set(sorted(batches)) - set(sorted(skip_batches)))

		return serial_nos, batch_nos

	def get_skip_serial_nos_for_stock_reconciliation(self):
		if self.voucher_type != "Stock Reconciliation" or not self.get("voucher_detail_no"):
			return [], []

		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import get_voucher_entries

		legs = {}
		for is_outward in (0, 1):
			legs[is_outward] = get_voucher_entries(
				self.voucher_type,
				self.get("voucher_no"),
				self.get("voucher_detail_no"),
				self.get("warehouse"),
				fields=["serial_no", "batch_no", "qty"],
				item_code=self.get("item_code"),
				is_outward=is_outward,
			)

		current_entries, new_entries = legs[1], legs[0]

		skip_serial_nos = {d.serial_no for d in current_entries if d.serial_no} & {
			d.serial_no for d in new_entries if d.serial_no
		}

		current_batch_qty = get_batch_qty_map(current_entries)
		new_batch_qty = get_batch_qty_map(new_entries)
		skip_batches = [
			batch_no
			for batch_no, qty in current_batch_qty.items()
			if flt(qty) == flt(new_batch_qty.get(batch_no))
		]

		return list(skip_serial_nos), skip_batches

	def get_standard_cost_rate(self):
		"""Return the standard valuation rate for the item if its valuation method is
		Standard Cost, else None — used to value bundle entries at standard."""
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import get_item_standard_rate
		from erpnext.stock.utils import get_valuation_method

		company = self.get("company")
		if not company and self.get("warehouse"):
			company = frappe.get_cached_value("Warehouse", self.warehouse, "company")

		if not company or get_valuation_method(self.item_code, company) != "Standard Cost":
			return None

		posting_date = self.get("posting_date")
		if not posting_date and self.get("posting_datetime"):
			posting_date = getdate(self.posting_datetime)

		return get_item_standard_rate(self.item_code, company, posting_date)

	def create_batch(self):
		from erpnext.stock.doctype.batch.batch import make_batch
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import get_voucher_entries

		if self.get("is_rejected"):
			# The non-rejected leg of the same voucher_detail_no (a different warehouse) already
			# picked/created a batch - reuse it instead of minting a second batch for one receipt.
			for entry in get_voucher_entries(
				self.voucher_type, self.voucher_no, self.voucher_detail_no, fields=["batch_no", "warehouse"]
			):
				if entry.batch_no and entry.warehouse != self.warehouse:
					return entry.batch_no

		return make_batch(
			frappe._dict(
				{
					"item": self.get("item_code"),
					"reference_doctype": self.get("voucher_type"),
					"reference_name": self.get("voucher_no"),
				}
			)
		)

	def get_auto_created_serial_nos(self):
		sr_nos = []
		serial_nos_details = []

		if not self.serial_no_series:
			msg = f"Please set Serial No Series in the item {self.item_code} or add the serial numbers manually."
			frappe.throw(_(msg))

		voucher_no = ""
		if self.get("voucher_no"):
			voucher_no = self.get("voucher_no")

		voucher_type = ""
		if self.get("voucher_type"):
			voucher_type = self.get("voucher_type")

		obj = NamingSeries(self.serial_no_series)
		current_value = obj.get_current_value()

		def get_series(partial_series, digits):
			return f"{current_value:0{digits}d}"

		posting_date = frappe.db.get_value(
			voucher_type,
			voucher_no,
			"posting_date",
		)

		for _i in range(abs(cint(self.actual_qty))):
			current_value += 1
			serial_no = parse_naming_series(self.serial_no_series, number_generator=get_series)

			sr_nos.append(serial_no)
			serial_nos_details.append(
				(
					serial_no,
					serial_no,
					now(),
					now(),
					frappe.session.user,
					frappe.session.user,
					self.warehouse,
					self.company,
					self.item_code,
					self.item_name,
					self.description,
					"Active",
					voucher_type,
					voucher_no,
					posting_date,
					self.batch_no,
				)
			)

		if serial_nos_details:
			fields = [
				"name",
				"serial_no",
				"creation",
				"modified",
				"owner",
				"modified_by",
				"warehouse",
				"company",
				"item_code",
				"item_name",
				"description",
				"status",
				"reference_doctype",
				"reference_name",
				"posting_date",
				"batch_no",
			]

			try:
				frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))
			except Exception as e:
				if e and len(e.args) > 1 and "Duplicate" in e.args[1]:
					frappe.throw(
						_(
							"A naming series conflict occurred while creating serial numbers. Please change the naming series for the item {0}."
						).format(bold(self.item_code)),
						title=_("Duplicate Serial Number Error"),
					)
				else:
					raise e

		obj.update_counter(current_value)

		return sr_nos


def get_serial_or_batch_items(items):
	serial_or_batch_items = frappe.get_all(
		"Item",
		filters={"name": ("in", [d.item_code for d in items])},
		or_filters={"has_serial_no": 1, "has_batch_no": 1},
	)

	if not serial_or_batch_items:
		return
	else:
		serial_or_batch_items = [d.name for d in serial_or_batch_items]

	return serial_or_batch_items


def get_serial_nos_batch(serial_nos):
	return frappe._dict(
		frappe.get_all(
			"Serial No",
			fields=["name", "batch_no"],
			filters={"name": ("in", serial_nos)},
			as_list=1,
		)
	)


def update_batch_qty(voucher_type, voucher_no, docstatus):
	# Negative-stock enforcement lives on Stock Location Ledger submit/cancel
	# (validate_no_negative_balance) - this only keeps the Batch.batch_qty display/report
	# cache in sync, it does not re-validate.
	batches = get_batchwise_qty(voucher_type, voucher_no)
	if not batches:
		return

	precision = frappe.get_precision("Batch", "batch_qty")
	for batch, qty in sorted(batches.items()):
		current_qty = get_batch_current_qty(batch)
		current_qty += flt(qty, precision) * (-1 if docstatus == 2 else 1)

		frappe.db.set_value("Batch", batch, "batch_qty", current_qty)


def get_batch_current_qty(batch):
	doctype = frappe.qb.DocType("Batch")
	query = frappe.qb.from_(doctype).select(doctype.batch_qty).where(doctype.name == batch).for_update()
	batch_qty = query.run()

	return flt(batch_qty[0][0]) if batch_qty else 0.0


def get_batchwise_qty(voucher_type, voucher_no):
	# docstatus > 0 (not is_cancelled == 0): a cancellation must reverse the exact qty a
	# submitted row carried, so already-cancelled rows still need to be counted here.
	table = frappe.qb.DocType("Stock Location Ledger")
	rows = (
		frappe.qb.from_(table)
		.select(table.batch_no, Sum(table.qty).as_("qty"))
		.where(
			(table.voucher_type == voucher_type)
			& (table.voucher_no == voucher_no)
			& (table.docstatus > 0)
			& (table.batch_no.isnotnull())
		)
		.groupby(table.batch_no)
	).run(as_dict=True)

	if not rows:
		return

	return frappe._dict({row.batch_no: row.qty for row in rows})


def get_serial_batch_list_from_item(item):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
	from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import get_voucher_entries

	serial_list, batch_list = [], []
	if item.get("parenttype") and item.get("parent") and item.get("name"):
		rows = get_voucher_entries(item.parenttype, item.parent, item.name, fields=["serial_no", "batch_no"])
		for row in rows:
			if row.serial_no and row.serial_no not in serial_list:
				serial_list.append(row.serial_no)
			if row.batch_no and row.batch_no not in batch_list:
				batch_list.append(row.batch_no)

	if not serial_list and not batch_list:
		serial_list = get_serial_nos(item.serial_no) if item.serial_no else []
		batch_list = [item.batch_no] if item.batch_no else []

	return serial_list, batch_list


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


def get_type_of_transaction(parent_doc, child_row):
	type_of_transaction = child_row.get("type_of_transaction")
	if parent_doc.get("doctype") == "Stock Entry":
		type_of_transaction = "Outward" if child_row.s_warehouse else "Inward"

	if not type_of_transaction:
		type_of_transaction = "Outward"
		if parent_doc.get("doctype") in ["Purchase Receipt", "Purchase Invoice"]:
			type_of_transaction = "Inward"

	if parent_doc.get("doctype") == "Subcontracting Receipt":
		type_of_transaction = "Outward"
		if child_row.get("doctype") == "Subcontracting Receipt Item":
			type_of_transaction = "Inward"
	elif parent_doc.get("doctype") == "Stock Reconciliation":
		type_of_transaction = "Inward"

	if parent_doc.get("is_return") and parent_doc.get("doctype") != "Stock Entry":
		type_of_transaction = "Inward"
		if (
			parent_doc.get("doctype") in ["Purchase Receipt", "Purchase Invoice"]
			or child_row.get("doctype") == "Subcontracting Receipt Item"
		):
			type_of_transaction = "Outward"

	return type_of_transaction


def get_serial_no_reservation(item_code: str, serial_no: str, warehouse: str) -> frappe._dict | None:
	"""Returns the Stock Reservation Entry that has reserved the given serial number, if any."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Stock Reservation Serial Batch")
	result = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(sre.name, sre.voucher_type, sre.voucher_no)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == item_code)
			& (sre.warehouse == warehouse)
			& (sre.status.notin(["Delivered", "Cancelled", "Closed"]))
			& (sre.reservation_based_on == "Serial and Batch")
			& (sb_entry.serial_no == serial_no)
			& (sb_entry.qty != sb_entry.delivered_qty)
		)
		.limit(1)
		.run(as_dict=True)
	)

	return result[0] if result else None


# --- Serial / batch entry utilities shared by the pickers and the inline editor ---


@frappe.whitelist()
def download_blank_csv_template(content: str | list):
	csv_data = []
	if isinstance(content, str):
		content = parse_json(content)

	csv_data.append(content)
	csv_data.append([])
	csv_data.append([])

	filename = "serial_and_batch_entries"
	build_csv_response(csv_data, filename)


@frappe.whitelist()
def upload_csv_file(item_code: str, file_path: str):
	serial_nos, batch_nos = [], []
	serial_nos, batch_nos = get_serial_batch_from_csv(item_code, file_path)

	return {
		"serial_nos": serial_nos,
		"batch_nos": batch_nos,
	}


def get_serial_batch_from_csv(item_code, file_path):
	from frappe.utils.csvutils import read_csv_content

	serial_nos = []
	batch_nos = []

	if not file_path:
		return serial_nos, batch_nos

	try:
		file = frappe.get_doc("File", {"file_url": file_path})
	except frappe.DoesNotExistError:
		frappe.msgprint(
			_("File '{0}' not found").format(frappe.bold(file_path)),
			alert=True,
			indicator="red",
			raise_exception=FileNotFoundError,
		)

	if file.file_type != "CSV":
		frappe.msgprint(
			_("{0} is not a CSV file.").format(frappe.bold(file.file_name)),
			alert=True,
			indicator="red",
			raise_exception=frappe.ValidationError,
		)

	csv_data = read_csv_content(file.get_content())
	serial_nos, batch_nos = parse_csv_file_to_get_serial_batch(csv_data)

	if serial_nos:
		make_serial_nos(item_code, serial_nos)

	if batch_nos:
		make_batch_nos(item_code, batch_nos)

	return serial_nos, batch_nos


def parse_csv_file_to_get_serial_batch(reader):
	has_serial_no, has_batch_no = False, False
	serial_nos = []
	batch_nos = []

	for index, row in enumerate(reader):
		if index == 0:
			has_serial_no = row[0] == "Serial No"
			has_batch_no = row[0] == "Batch No"
			if not has_batch_no and len(row) > 1:
				has_batch_no = row[1] == "Batch No"

			continue

		if not row[0]:
			continue

		if has_serial_no or (has_serial_no and has_batch_no):
			_dict = {"serial_no": row[0].strip(), "qty": 1}

			if has_batch_no:
				_dict.update(
					{
						"batch_no": row[1].strip(),
						"qty": row[2],
					}
				)

				batch_nos.append(
					{
						"batch_no": row[1].strip(),
						"qty": row[2],
					}
				)

			serial_nos.append(_dict)
		elif has_batch_no:
			batch_nos.append(
				{
					"batch_no": row[0].strip(),
					"qty": row[1],
				}
			)

	return serial_nos, batch_nos


def get_serial_batch_from_data(item_code, kwargs):
	serial_nos = []
	batch_nos = []
	if kwargs.get("serial_nos"):
		data = parse_serial_nos(kwargs.get("serial_nos"))
		for serial_no in data:
			if not serial_no:
				continue
			serial_nos.append({"serial_no": serial_no, "qty": 1})

		make_serial_nos(item_code, serial_nos)

	if kwargs.get("_has_serial_nos"):
		return serial_nos

	return serial_nos, batch_nos


@frappe.whitelist()
def create_serial_nos(item_code: str, serial_nos: list | str):
	serial_nos = get_serial_batch_from_data(
		item_code,
		{
			"serial_nos": serial_nos,
			"_has_serial_nos": True,
		},
	)

	return serial_nos


def make_serial_nos(item_code, serial_nos):
	item = frappe.get_cached_value(
		"Item", item_code, ["description", "item_code", "item_name", "warranty_period"], as_dict=1
	)

	serial_nos = [d.get("serial_no").strip() for d in serial_nos if d.get("serial_no")]
	existing_serial_nos = frappe.get_all("Serial No", filters={"name": ("in", serial_nos)})

	existing_serial_nos = [d.get("name") for d in existing_serial_nos if d.get("name")]
	serial_nos = list(set(serial_nos) - set(existing_serial_nos))

	if not serial_nos:
		return

	serial_nos_details = []
	user = frappe.session.user
	for serial_no in serial_nos:
		serial_nos_details.append(
			(
				serial_no,
				serial_no,
				now(),
				now(),
				user,
				user,
				item.item_code,
				item.item_name,
				item.description,
				item.warranty_period or 0,
				"Inactive",
			)
		)

	fields = [
		"name",
		"serial_no",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"item_code",
		"item_name",
		"description",
		"warranty_period",
		"status",
	]

	frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	frappe.msgprint(_("Serial Nos are created successfully"), alert=True)


def make_batch_nos(item_code, batch_nos):
	item = frappe.get_cached_value("Item", item_code, ["description", "item_code"], as_dict=1)
	batch_nos = [d.get("batch_no") for d in batch_nos if d.get("batch_no")]

	existing_batches = frappe.get_all("Batch", filters={"name": ("in", batch_nos)})

	existing_batches = [d.get("name") for d in existing_batches if d.get("name")]

	batch_nos = list(set(batch_nos) - set(existing_batches))
	if not batch_nos:
		return

	batch_nos_details = []
	user = frappe.session.user
	for batch_no in batch_nos:
		if frappe.db.exists("Batch", batch_no):
			continue

		batch_nos_details.append(
			(
				batch_no,
				batch_no,
				now(),
				now(),
				user,
				user,
				item.item_code,
				item.item_name,
				item.description,
				1,
			)
		)

	fields = [
		"name",
		"batch_id",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"item",
		"item_name",
		"description",
		"use_batchwise_valuation",
	]

	frappe.db.bulk_insert("Batch", fields=fields, values=set(batch_nos_details))

	frappe.msgprint(_("Batch Nos are created successfully"), alert=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(
	doctype: Any, txt: str, searchfield: str, start: int, page_len: int, filters: Any, as_dict: bool = False
):
	item_filters = {"disabled": 0}
	if txt:
		item_filters["name"] = ("like", f"%{txt}%")

	return frappe.get_all(
		"Item",
		filters=item_filters,
		or_filters={"has_serial_no": 1, "has_batch_no": 1},
		fields=["name", "item_name"],
		as_list=1,
	)


def get_batch(item_code):
	from erpnext.stock.doctype.batch.batch import make_batch

	return make_batch(
		frappe._dict(
			{
				"item": item_code,
			}
		)
	)


@frappe.whitelist()
def get_auto_data(**kwargs):
	kwargs = frappe._dict(kwargs)
	if cint(kwargs.has_serial_no):
		return get_serial_nos_from_sre(kwargs) if kwargs.scio_detail else get_available_serial_nos(kwargs)
	elif cint(kwargs.has_batch_no):
		return get_batch_nos_from_sre(kwargs) if kwargs.scio_detail else get_auto_batch_nos(kwargs)


def get_available_batches_qty(available_batches):
	available_batches_qty = defaultdict(float)
	for batch in available_batches:
		available_batches_qty[batch.batch_no] += batch.qty

	return available_batches_qty


def get_available_serial_nos(kwargs):
	fields = ["name as serial_no", "warehouse"]
	if kwargs.has_batch_no:
		fields.append("batch_no")

	order_by = "creation"
	if kwargs.based_on == "LIFO":
		order_by = "creation"
	elif kwargs.based_on == "Expiry":
		order_by = "amc_expiry_date"

	if not kwargs.get("posting_datetime") and kwargs.get("posting_date"):
		kwargs["posting_datetime"] = combine_datetime(kwargs.get("posting_date"), kwargs.get("posting_time"))

	filters = {"item_code": kwargs.item_code}

	# ignore_warehouse is used for backdated stock transactions
	# There might be chances that the serial no not exists in the warehouse during backdated stock transactions
	if not kwargs.get("ignore_warehouse"):
		filters["warehouse"] = ("is", "set")
		if kwargs.warehouse:
			filters["warehouse"] = kwargs.warehouse

	reserved_entries = get_reserved_serial_nos_for_sre(kwargs)

	ignore_serial_nos = []
	if reserved_entries:
		if kwargs.get("sabb_voucher_type") == "Delivery Note" and kwargs.get("against_sales_order"):
			reserved_voucher_details = [kwargs.get("against_sales_order")]
		else:
			reserved_voucher_details = get_reserved_voucher_details(kwargs)

		# Check if serial nos are reserved for the current voucher then fetch only those serial nos
		if reserved_serial_nos := get_reserved_serial_nos_for_voucher(
			kwargs, reserved_entries, reserved_voucher_details
		):
			filters["name"] = ("in", reserved_serial_nos)
			return get_serial_nos_based_on_filters(filters, fields, order_by, kwargs)

		# Check if serial nos are reserved for other vouchers then ignore those serial nos
		elif ignore_reserved_serial_nos := get_other_doc_reserved_serials(
			kwargs, reserved_entries, reserved_voucher_details
		):
			ignore_serial_nos.extend(ignore_reserved_serial_nos)

	if reserved_for_pos := get_reserved_serial_nos_for_pos(kwargs):
		ignore_serial_nos.extend(reserved_for_pos)

	# To ignore serial nos in the same record for the draft state
	if kwargs.get("ignore_serial_nos"):
		ignore_serial_nos.extend(kwargs.get("ignore_serial_nos"))

	ignore_serial_nos = list(set(ignore_serial_nos))
	if kwargs.get("posting_datetime"):
		time_based_serial_nos = get_serial_nos_based_on_posting_date(kwargs, ignore_serial_nos)

		if not time_based_serial_nos:
			return []

		filters["name"] = ("in", time_based_serial_nos)
	elif ignore_serial_nos:
		filters["name"] = ("not in", ignore_serial_nos)
	elif kwargs.get("serial_nos"):
		filters["name"] = ("in", kwargs.get("serial_nos"))

	if kwargs.get("batches"):
		batches = get_non_expired_batches(kwargs.get("batches"))
		if not batches:
			return []

		filters["batch_no"] = ("in", batches)

	return get_serial_nos_based_on_filters(filters, fields, order_by, kwargs)


def get_serial_nos_based_on_filters(filters, fields, order_by, kwargs):
	doctype = frappe.qb.DocType("Serial No")

	order_by_column = getattr(doctype, order_by)
	query = frappe.qb.from_(doctype).limit(cint(kwargs.qty) or 10000000).for_update()

	if kwargs.based_on == "LIFO":
		query = query.orderby(order_by_column, order=frappe.query_builder.Order.desc)
	else:
		if order_by == "amc_expiry_date":
			query = query.orderby(order_by_column.isnull(), order=frappe.query_builder.Order.desc)
		query = query.orderby(order_by_column)

	for key, value in filters.items():
		column = getattr(doctype, key)

		if isinstance(value, tuple):
			operator = value[0]

			if operator == "between":
				query = query.where(column.between(value[1], value[2]))

			elif operator == "in":
				query = query.where(column.isin(value[1]))

			elif operator == "not in":
				query = query.where(column.notin(value[1]))

			elif operator == "is":
				if value[1] == "set":
					query = query.where(column.isnotnull())
				elif value[1] == "not set":
					query = query.where(column.isnull())
		else:
			query = query.where(column == value)

	for field in fields:
		if " as " in field.lower():
			# Split field and alias
			field_name, alias = field.split(" as ", 1)
			query = query.select(getattr(doctype, field_name).as_(alias))
		else:
			query = query.select(getattr(doctype, field))

	return query.run(as_dict=True)


def get_serial_nos_from_sre(kwargs):
	table = frappe.qb.DocType("Stock Reservation Entry")
	child_table = frappe.qb.DocType("Stock Reservation Serial Batch")
	query = (
		frappe.qb.from_(table)
		.join(child_table)
		.on(table.name == child_table.parent)
		.select(child_table.serial_no, child_table.batch_no, child_table.warehouse)
		.where(
			(table.docstatus == 1)
			& (table.voucher_detail_no == kwargs.scio_detail)
			& (child_table.qty != child_table.delivered_qty)
		)
		.limit(cint(kwargs.qty) or 10000000)
	)
	if kwargs.based_on == "LIFO":
		query = query.orderby(child_table.creation, order=frappe.query_builder.Order.desc)
	else:
		query = query.orderby(child_table.creation)
	return query.run(as_dict=True)


def get_non_expired_batches(batches):
	filters = {}
	if isinstance(batches, list):
		filters["name"] = ("in", batches)
	else:
		filters["name"] = batches

	data = frappe.get_all(
		"Batch",
		filters=filters,
		or_filters=[["expiry_date", ">=", today()], ["expiry_date", "is", "not set"]],
		fields=["name"],
	)

	return [d.name for d in data] if data else []


def get_serial_nos_based_on_posting_date(kwargs, ignore_serial_nos):
	"""Replays Stock Location Ledger entries in time order (up to kwargs.posting_datetime, the
	tiebreaker being kwargs.creation for same-instant backdated entries) to work out which serial
	nos were actually in stock at that point - inward entries add the serial no, outward entries
	remove it."""
	sll = frappe.qb.DocType("Stock Location Ledger")
	query = (
		frappe.qb.from_(sll)
		.select(sll.serial_no, sll.is_outward)
		.where((sll.docstatus == 1) & (sll.serial_no.isnotnull()) & (sll.serial_no != ""))
		.orderby(sll.posting_datetime)
		.orderby(sll.creation)
	)

	timestamp_condition = sll.posting_datetime <= kwargs.posting_datetime
	if kwargs.get("creation"):
		timestamp_condition = (sll.posting_datetime < kwargs.posting_datetime) | (
			(sll.posting_datetime == kwargs.posting_datetime) & (sll.creation < kwargs.creation)
		)
	query = query.where(timestamp_condition)

	for field in ["warehouse", "item_code"]:
		if not kwargs.get(field):
			continue

		value = kwargs.get(field)
		query = query.where(sll[field].isin(value) if isinstance(value, list) else sll[field] == value)

	serial_nos = kwargs.get("serial_nos") or kwargs.get("serial_no")
	if serial_nos:
		query = query.where(sll.serial_no.isin(serial_nos if isinstance(serial_nos, list) else [serial_nos]))

	if kwargs.ignore_voucher_detail_no:
		condition = sll.voucher_detail_no != kwargs.ignore_voucher_detail_no
		if kwargs.get("ignore_is_outward") is not None:
			# Ignore only one leg of that row - a Stock Reconciliation keeps its reversal and
			# new-state entries under the same voucher_detail_no.
			condition = condition | (sll.is_outward != cint(kwargs.ignore_is_outward))
		query = query.where(condition)
	elif kwargs.voucher_no:
		query = query.where(sll.voucher_no != kwargs.voucher_no)

	available_serial_nos = set()
	for row in query.run(as_dict=True):
		if row.is_outward:
			available_serial_nos.discard(row.serial_no)
		else:
			available_serial_nos.add(row.serial_no)

	available_serial_nos.difference_update(ignore_serial_nos)
	return list(available_serial_nos)


def get_reserved_voucher_details(kwargs):
	reserved_voucher_details = []

	field_mapper = {
		"Delivery Note": [["Delivery Note Item", "against_sales_order"]],
		"Stock Entry": [["Stock Entry", "work_order"], ["Stock Entry", "subcontracting_inward_order"]],
		"Work Order": [["Work Order", "production_plan"], ["Work Order", "subcontracting_inward_order"]],
	}.get(kwargs.get("sabb_voucher_type"))

	if not field_mapper or not kwargs.get("sabb_voucher_no"):
		return reserved_voucher_details

	voucher_based_filters = {
		"Delivery Note": {
			"name": kwargs.get("sabb_voucher_detail_no"),
			"parent": kwargs.get("sabb_voucher_no"),
			"docstatus": ("<", 2),
		},
		"Stock Entry": {
			"name": kwargs.get("sabb_voucher_no"),
			"docstatus": ("<", 2),
		},
		"Work Order": {
			"name": kwargs.get("sabb_voucher_no"),
			"docstatus": ("<", 2),
		},
	}.get(kwargs.get("sabb_voucher_type"))

	reserved_voucher_details = []
	for row in field_mapper:
		reserved_voucher_details.extend(
			frappe.get_all(
				row[0],
				pluck=row[1],
				filters=voucher_based_filters,
			)
		)

	return reserved_voucher_details


def get_reserved_serial_nos_for_pos(kwargs):
	from erpnext.controllers.sales_and_purchase_return import get_returned_serial_nos

	ignore_serial_nos = []
	pos_invoices = frappe.get_all(
		"POS Invoice",
		fields=[
			"`tabPOS Invoice Item`.serial_no",
			"`tabPOS Invoice`.is_return",
			"`tabPOS Invoice Item`.name as child_docname",
			"`tabPOS Invoice`.name as parent_docname",
		],
		filters=[
			["POS Invoice", "consolidated_invoice", "is", "not set"],
			["POS Invoice", "docstatus", "=", 1],
			["POS Invoice", "is_return", "=", 0],
			["POS Invoice Item", "item_code", "=", kwargs.item_code],
			["POS Invoice", "name", "not in", kwargs.ignore_voucher_nos],
		],
	)

	returned_serial_nos = []
	for pos_invoice in pos_invoices:
		if pos_invoice.serial_no:
			ignore_serial_nos.extend(parse_serial_nos(pos_invoice.serial_no))

		if pos_invoice.is_return:
			continue

		child_doc = _dict(
			{
				"doctype": "POS Invoice Item",
				"name": pos_invoice.child_docname,
			}
		)

		parent_doc = _dict(
			{
				"doctype": "POS Invoice",
				"name": pos_invoice.parent_docname,
			}
		)

		returned_serial_nos.extend(
			get_returned_serial_nos(
				child_doc, parent_doc, ignore_voucher_detail_no=kwargs.get("ignore_voucher_detail_no")
			)
		)
	# Counter is used to create a hashmap of serial nos, which contains count of each serial no
	# so we subtract returned serial nos from ignore serial nos after creating a counter of each to get the items which we need 	to ignore(which are sold)

	ignore_serial_nos_counter = Counter(ignore_serial_nos)
	returned_serial_nos_counter = Counter(returned_serial_nos)

	return list(ignore_serial_nos_counter - returned_serial_nos_counter)


def get_reserved_serial_nos_for_voucher(kwargs, reserved_entries, reserved_voucher_details):
	serial_nos = []
	if not kwargs.get("pick_reserved_items"):
		return serial_nos

	for entry in reserved_entries:
		if entry.voucher_no in reserved_voucher_details:
			serial_nos.append(entry.serial_no)
			continue

		if kwargs.get("serial_nos") and entry.serial_no in kwargs.get("serial_nos"):
			frappe.throw(
				_(
					"The Serial No {0} is reserved against the {1} {2} and cannot be used for any other transaction."
				).format(bold(entry.serial_no), entry.voucher_type, bold(entry.voucher_no)),
				title=_("Serial No Reserved"),
			)

	return serial_nos


def get_other_doc_reserved_serials(kwargs, reserved_entries, reserved_voucher_details):
	serial_nos = []
	for entry in reserved_entries:
		if entry.voucher_no in reserved_voucher_details:
			continue

		serial_nos.append(entry.serial_no)

	return serial_nos


def get_reserved_serial_nos_for_sre(kwargs) -> list:
	"""Returns a list of `Serial No` reserved in Stock Reservation Entry."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Stock Reservation Serial Batch")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.serial_no,
			sre.voucher_no,
			sre.voucher_type,
		)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.delivered_qty < sre.reserved_qty)
			& (sb_entry.delivered_qty < sb_entry.qty)
			& (sre.reservation_based_on == "Serial and Batch")
		)
		.orderby(sb_entry.idx)
	)

	if kwargs.warehouse:
		query = query.where(sre.warehouse == kwargs.warehouse)

	if kwargs.ignore_voucher_nos:
		query = query.where(sre.name.notin(kwargs.ignore_voucher_nos))

	return query.run(as_dict=True)


def get_reserved_batches_for_pos(kwargs) -> dict:
	"""Returns a dict of `Batch No` followed by the `Qty` reserved in POS Invoices."""

	pos_batches = frappe._dict()
	POS_Invoice = frappe.qb.DocType("POS Invoice")
	POS_Invoice_Item = frappe.qb.DocType("POS Invoice Item")

	pos_invoices = (
		frappe.qb.from_(POS_Invoice)
		.inner_join(POS_Invoice_Item)
		.on(POS_Invoice.name == POS_Invoice_Item.parent)
		.select(
			POS_Invoice_Item.batch_no,
			POS_Invoice_Item.qty,
			POS_Invoice.is_return,
			POS_Invoice_Item.warehouse,
			POS_Invoice_Item.name.as_("child_docname"),
			POS_Invoice.name.as_("parent_docname"),
		)
		.where(
			(POS_Invoice.consolidated_invoice.isnull() | (POS_Invoice.consolidated_invoice == ""))
			& (POS_Invoice.docstatus == 1)
			& (POS_Invoice_Item.item_code == kwargs.item_code)
		)
	)

	if kwargs.get("company"):
		pos_invoices = pos_invoices.where(POS_Invoice.company == kwargs.get("company"))

	if kwargs.get("ignore_voucher_nos"):
		pos_invoices = pos_invoices.where(POS_Invoice.name.notin(kwargs.get("ignore_voucher_nos")))

	pos_invoices = pos_invoices.run(as_dict=True)

	def add_to_pos_batches(batch_no, warehouse, qty):
		if kwargs.get("batch_no") and batch_no != kwargs.get("batch_no"):
			return

		key = (batch_no, warehouse)
		if key in pos_batches:
			pos_batches[key]["qty"] += qty
		else:
			pos_batches[key] = frappe._dict({"qty": qty, "warehouse": warehouse})

	# A row whose batch_no text was cleared after composition creation (e.g. a return) still
	# carries its real composition in Stock Location Ledger - net from there. Ledger qty is
	# already signed by direction, matching the text-based `qty * -1` convention.
	textless_rows = [row.child_docname for row in pos_invoices if not row.batch_no]
	ledger_map = defaultdict(list)
	if textless_rows:
		for d in frappe.get_all(
			"Stock Location Ledger",
			filters={
				"voucher_detail_no": ("in", textless_rows),
				"voucher_type": "POS Invoice",
				"docstatus": ("<", 2),
				"batch_no": ("is", "set"),
			},
			fields=["voucher_detail_no", "batch_no", "warehouse", "qty"],
		):
			ledger_map[d.voucher_detail_no].append(d)

	for row in pos_invoices:
		if not row.batch_no:
			for d in ledger_map.get(row.child_docname, []):
				add_to_pos_batches(d.batch_no, d.warehouse, d.qty)
			continue

		add_to_pos_batches(row.batch_no, row.warehouse, row.qty * -1)

	return pos_batches


def get_reserved_batches_for_sre(kwargs) -> dict:
	"""Returns a dict of `Batch No` followed by the `Qty` reserved in Stock Reservation Entry."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Stock Reservation Serial Batch")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.batch_no, sre.warehouse, (-1 * Sum(sb_entry.qty - sb_entry.delivered_qty)).as_("qty")
		)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.delivered_qty < sre.reserved_qty)
			& (sre.reservation_based_on == "Serial and Batch")
		)
		.groupby(sb_entry.batch_no, sre.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(sre.company == kwargs.get("company"))

	if kwargs.batch_no:
		if isinstance(kwargs.batch_no, list):
			query = query.where(sb_entry.batch_no.isin(kwargs.batch_no))
		else:
			query = query.where(sb_entry.batch_no == kwargs.batch_no)

	if kwargs.warehouse:
		if isinstance(kwargs.warehouse, list):
			query = query.where(sre.warehouse.isin(kwargs.warehouse))
		else:
			query = query.where(sre.warehouse == kwargs.warehouse)

	if kwargs.ignore_voucher_nos:
		query = query.where(sre.name.notin(kwargs.ignore_voucher_nos))

	data = query.run(as_dict=True)

	reserved_batches_details = frappe._dict()
	if data:
		reserved_batches_details = frappe._dict(
			{(d.batch_no, d.warehouse): frappe._dict({"warehouse": d.warehouse, "qty": d.qty}) for d in data}
		)

	return reserved_batches_details


def get_auto_batch_nos(kwargs):
	if kwargs.against_sales_order and (
		only_consider_batches := get_batches_to_be_considered(kwargs.against_sales_order)
	):
		batches, warehouses = [], []
		for item in only_consider_batches:
			batches.append(item.batch_no)
			warehouses.append(item.warehouse)

		if batches:
			kwargs.batch_no = batches
			kwargs.warehouse = warehouses

	if not kwargs.get("posting_datetime") and kwargs.get("posting_date"):
		kwargs["posting_datetime"] = combine_datetime(kwargs.get("posting_date"), kwargs.get("posting_time"))

	available_batches = get_available_batches(kwargs)

	pos_invoice_batches = frappe._dict()
	if not kwargs.for_stock_levels:
		pos_invoice_batches = get_reserved_batches_for_pos(kwargs)

	sre_reserved_batches = frappe._dict()
	if not kwargs.ignore_reserved_stock:
		sre_reserved_batches = get_reserved_batches_for_sre(kwargs)

	if kwargs.against_sales_order and only_consider_batches:
		kwargs.batch_no = kwargs.warehouse = None

	picked_batches = frappe._dict()
	if kwargs.get("is_pick_list"):
		picked_batches = get_picked_batches(kwargs)

	if pos_invoice_batches or sre_reserved_batches or picked_batches:
		update_available_batches(
			available_batches,
			pos_invoice_batches,
			sre_reserved_batches,
			picked_batches,
		)

	if not kwargs.ignore_reserved_stock and not kwargs.for_stock_levels:
		available_batches = remove_reservation_conflict_batches(available_batches, kwargs)

	if kwargs.based_on == "Expiry":
		available_batches = sorted(available_batches, key=lambda x: x.expiry_date or getdate("9999-12-31"))

	if not kwargs.get("do_not_check_future_batches") and available_batches and kwargs.get("posting_datetime"):
		filter_zero_near_batches(available_batches, kwargs)

	if not kwargs.consider_negative_batches:
		precision = frappe.get_precision("Stock Ledger Entry", "actual_qty")
		available_batches = [d for d in available_batches if flt(d.qty, precision) > 0]

	qty = flt(kwargs.qty)

	if not qty:
		return available_batches

	return get_qty_based_available_batches(available_batches, qty)


def remove_reservation_conflict_batches(available_batches, kwargs):
	if not available_batches or not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
		return available_batches

	conflicting_batches = get_cross_warehouse_reserved_batches(kwargs)
	if not conflicting_batches:
		return available_batches

	return [d for d in available_batches if d.batch_no not in conflicting_batches]


def get_cross_warehouse_reserved_batches(kwargs) -> set:
	from erpnext.stock.doctype.batch.batch import get_batch_qty

	conflicting_batches = set()
	for row in get_cross_warehouse_sre_details(kwargs):
		if flt(row.outstanding_qty) <= 0:
			continue

		batch_qty = get_batch_qty(
			row.batch_no,
			row.warehouse,
			posting_date=kwargs.get("posting_date"),
			posting_time=kwargs.get("posting_time"),
			consider_negative_batches=True,
		)

		if flt(batch_qty, 6) < flt(row.outstanding_qty, 6):
			conflicting_batches.add(row.batch_no)

	return conflicting_batches


def get_cross_warehouse_sre_details(kwargs):
	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Stock Reservation Serial Batch")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.batch_no,
			sre.warehouse,
			Sum(sb_entry.qty - sb_entry.delivered_qty).as_("outstanding_qty"),
		)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.delivered_qty < sre.reserved_qty)
			& (sre.reservation_based_on == "Serial and Batch")
			& (sb_entry.batch_no.isnotnull())
		)
		.groupby(sb_entry.batch_no, sre.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(sre.company == kwargs.get("company"))

	if kwargs.warehouse:
		warehouses = kwargs.warehouse if isinstance(kwargs.warehouse, list) else [kwargs.warehouse]
		query = query.where(sre.warehouse.notin(warehouses))

	return query.run(as_dict=True)


def get_batch_nos_from_sre(kwargs):
	from frappe.query_builder.functions import Sum

	table = frappe.qb.DocType("Stock Reservation Entry")
	child_table = frappe.qb.DocType("Stock Reservation Serial Batch")

	query = (
		frappe.qb.from_(table)
		.join(child_table)
		.on(table.name == child_table.parent)
		.select(
			child_table.batch_no,
			child_table.warehouse,
			Sum(child_table.qty - child_table.delivered_qty).as_("qty"),
		)
		.where(
			(table.docstatus == 1)
			& (table.voucher_detail_no == kwargs.scio_detail)
			& (child_table.qty != child_table.delivered_qty)
		)
		.groupby(child_table.batch_no, child_table.warehouse)
		.orderby(child_table.batch_no, order=frappe.query_builder.Order.asc)
	)

	result = query.run(as_dict=True)
	return get_qty_based_available_batches(result, flt(kwargs.qty)) if flt(kwargs.qty) else result


def get_batches_to_be_considered(sales_order_name):
	parent = frappe.qb.DocType("Stock Reservation Entry")
	child = frappe.qb.DocType("Stock Reservation Serial Batch")

	query = (
		frappe.qb.from_(parent)
		.join(child)
		.on(parent.name == child.parent)
		.select(child.batch_no, child.warehouse)
		.distinct()
		.where(
			(parent.docstatus == 1)
			& (parent.voucher_no == sales_order_name)
			& (child.delivered_qty < child.qty)
		)
	)
	return query.run(as_dict=True)


def filter_zero_near_batches(available_batches, kwargs):
	kwargs.batch_no = [d.batch_no for d in available_batches]

	del kwargs["posting_datetime"]

	kwargs.do_not_check_future_batches = 1
	available_batches_in_future = get_auto_batch_nos(kwargs)
	for batch in available_batches:
		if batch.qty <= 0:
			continue

		for future_batch in available_batches_in_future:
			if (
				batch.batch_no == future_batch.batch_no
				and batch.warehouse == future_batch.warehouse
				and future_batch.qty <= 0
			):
				batch.qty = 0


def get_qty_based_available_batches(available_batches, qty):
	batches = []
	for batch in available_batches:
		if qty <= 0:
			break

		batch_qty = flt(batch.qty)
		if qty > batch_qty:
			batches.append(
				frappe._dict(
					{
						"batch_no": batch.batch_no,
						"qty": batch_qty,
						"warehouse": batch.warehouse,
					}
				)
			)
			qty -= batch_qty
		else:
			batches.append(
				frappe._dict(
					{
						"batch_no": batch.batch_no,
						"qty": qty,
						"warehouse": batch.warehouse,
					}
				)
			)
			qty = 0

	return batches


def update_available_batches(available_batches, *reserved_batches) -> None:
	for batches in reserved_batches:
		if batches:
			for key, data in batches.items():
				batch_no, warehouse = key
				batch_not_exists = True
				for batch in available_batches:
					if batch.batch_no == batch_no and batch.warehouse == warehouse:
						batch.qty += data.qty
						batch_not_exists = False

				if batch_not_exists:
					available_batches.append(data)


def get_available_batches(kwargs):
	sll = frappe.qb.DocType("Stock Location Ledger")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(sll)
		.inner_join(batch_table)
		.on(sll.batch_no == batch_table.name)
		.select(
			sll.batch_no,
			sll.warehouse,
			Sum(sll.qty).as_("qty"),
			Max(batch_table.expiry_date).as_("expiry_date"),
		)
		.where(batch_table.disabled == 0)
		.where(sll.docstatus == 1)
		# A Pick List's rows are a reservation, not a stock movement - get_picked_batches
		# already accounts for them separately.
		.where(sll.voucher_type != "Pick List")
		.groupby(sll.batch_no, sll.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(sll.company == kwargs.get("company"))

	if not kwargs.get("for_stock_levels"):
		query = query.where((batch_table.expiry_date >= today()) | (batch_table.expiry_date.isnull()))

	if kwargs.get("posting_datetime"):
		timestamp_condition = sll.posting_datetime <= kwargs.posting_datetime

		if kwargs.get("creation"):
			timestamp_condition = sll.posting_datetime < kwargs.posting_datetime

			timestamp_condition |= (sll.posting_datetime == kwargs.posting_datetime) & (
				sll.creation < kwargs.creation
			)

		query = query.where(timestamp_condition)

	for field in ["warehouse", "item_code"]:
		if not kwargs.get(field):
			continue

		if isinstance(kwargs.get(field), list):
			query = query.where(sll[field].isin(kwargs.get(field)))
		else:
			query = query.where(sll[field] == kwargs.get(field))

	if kwargs.get("batch_no"):
		if isinstance(kwargs.batch_no, list):
			query = query.where(sll.batch_no.isin(kwargs.batch_no))
		else:
			query = query.where(sll.batch_no == kwargs.batch_no)

	# order by aggregates (one row per batch_no+warehouse); raw columns aren't valid under GROUP BY on postgres
	if kwargs.based_on == "LIFO":
		query = query.orderby(Max(batch_table.creation), order=frappe.qb.desc)
	elif kwargs.based_on == "Expiry":
		query = query.orderby(Max(batch_table.expiry_date))
	else:
		query = query.orderby(Max(batch_table.creation))

	if kwargs.get("ignore_voucher_nos"):
		query = query.where(sll.voucher_no.notin(kwargs.get("ignore_voucher_nos")))

	data = query.run(as_dict=True)

	return apply_closing_balances_on_availability(data, kwargs)


def apply_closing_balances_on_availability(data, kwargs):
	"""Pre-ledger (legacy) batch history exists only as Stock Closing Balance snapshots, so each
	snapshot's qty is added on top of the live ledger sum - minus whatever ledger rows the
	snapshot already absorbed, to avoid double counting."""
	from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
		get_closing_balances_for_batches,
	)

	closing_rows = get_closing_balances_for_batches(kwargs)

	if closing_rows and kwargs.get("posting_datetime"):
		# availability asked as of a moment inside a snapshot window can't be answered from the
		# snapshot; keep the raw ledger behaviour for those keys
		posting_datetime = get_datetime(kwargs.get("posting_datetime"))
		closing_rows = {
			key: row for key, row in closing_rows.items() if posting_datetime > row.posting_datetime
		}

	if not closing_rows:
		return data

	batch_meta = get_closing_batch_meta(closing_rows, kwargs)
	absorbed = get_absorbed_availability(closing_rows, kwargs)

	index = {(row.batch_no, row.warehouse): row for row in data}
	appended = False
	for (batch_no, warehouse), closing in closing_rows.items():
		meta = batch_meta.get(batch_no)
		if meta is None:
			continue

		absorbed_row = absorbed.get((batch_no, warehouse)) or frappe._dict()
		delta = flt(closing.actual_qty) - flt(absorbed_row.qty)
		if row := index.get((batch_no, warehouse)):
			row.qty += delta
		elif delta:
			data.append(
				frappe._dict(batch_no=batch_no, warehouse=warehouse, qty=delta, expiry_date=meta.expiry_date)
			)
			appended = True

	if appended:
		data = sort_available_batches(data, kwargs)

	return data


def get_closing_batch_meta(closing_rows, kwargs) -> dict:
	batch_nos = list({batch_no for batch_no, _warehouse in closing_rows})
	batches = frappe.get_all(
		"Batch",
		fields=["name", "expiry_date", "creation"],
		filters={"name": ("in", batch_nos), "disabled": 0},
	)

	if not kwargs.get("for_stock_levels"):
		batches = [b for b in batches if not b.expiry_date or getdate(b.expiry_date) >= getdate(today())]

	return {b.name: b for b in batches}


def get_absorbed_availability(closing_rows, kwargs) -> dict:
	sll = frappe.qb.DocType("Stock Location Ledger")

	conditions = [
		(sll.batch_no == batch_no)
		& (sll.warehouse == warehouse)
		& (sll.posting_datetime <= row.posting_datetime)
		for (batch_no, warehouse), row in closing_rows.items()
	]

	query = (
		frappe.qb.from_(sll)
		.select(
			sll.batch_no,
			sll.warehouse,
			Sum(sll.qty).as_("qty"),
			Sum(sll.stock_value_difference).as_("stock_value"),
		)
		.where((sll.docstatus == 1) & (sll.voucher_type != "Pick List"))
		.where(Criterion.any(conditions))
		.groupby(sll.batch_no, sll.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(sll.company == kwargs.get("company"))

	if kwargs.get("ignore_voucher_nos"):
		query = query.where(sll.voucher_no.notin(kwargs.get("ignore_voucher_nos")))

	return {(d.batch_no, d.warehouse): d for d in query.run(as_dict=True)}


def sort_available_batches(data, kwargs):
	batch_creation = {
		d.name: d.creation
		for d in frappe.get_all(
			"Batch",
			fields=["name", "creation"],
			filters={"name": ("in", list({row.batch_no for row in data}))},
		)
	}

	if kwargs.based_on == "Expiry":
		return sorted(data, key=lambda x: x.expiry_date or getdate("9999-12-31"))

	reverse = kwargs.based_on == "LIFO"
	fallback = get_datetime("9999-12-31 23:59:59")
	return sorted(data, key=lambda x: batch_creation.get(x.batch_no) or fallback, reverse=reverse)


def get_picked_batches(kwargs) -> dict[str, dict]:
	"""Batch qty already reserved by other open Pick Lists (status != Completed) - so the same
	stock isn't offered again to a second pick. Reads Stock Location Ledger directly."""
	picked_batches = frappe._dict()

	table = frappe.qb.DocType("Stock Location Ledger")
	pick_list_table = frappe.qb.DocType("Pick List")

	query = (
		frappe.qb.from_(table)
		.inner_join(pick_list_table)
		.on(table.voucher_no == pick_list_table.name)
		.select(
			table.batch_no,
			table.warehouse,
			Sum(table.qty).as_("qty"),
		)
		.where(
			(table.docstatus == 1)
			& (pick_list_table.status != "Completed")
			& (table.is_outward == 1)
			& (table.voucher_type == "Pick List")
			& (table.batch_no.isnotnull())
		)
		.groupby(table.batch_no, table.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(table.company == kwargs.get("company"))

	if kwargs.get("item_code"):
		query = query.where(table.item_code == kwargs.get("item_code"))

	if kwargs.get("warehouse"):
		if isinstance(kwargs.warehouse, list):
			query = query.where(table.warehouse.isin(kwargs.warehouse))
		else:
			query = query.where(table.warehouse == kwargs.get("warehouse"))

	data = query.run(as_dict=True)
	for row in data:
		if not row.qty:
			continue

		key = (row.batch_no, row.warehouse)
		if key not in picked_batches:
			picked_batches[key] = frappe._dict(
				{
					"qty": row.qty,
					"warehouse": row.warehouse,
				}
			)
		else:
			picked_batches[key].qty += row.qty

	return picked_batches


@frappe.whitelist()
def get_batch_no_from_serial_no(serial_no: str):
	return frappe.get_cached_value("Serial No", serial_no, "batch_no")


@frappe.whitelist()
def is_serial_batch_no_exists(
	item_code: str, type_of_transaction: str, serial_no: str | None = None, batch_no: str | None = None
):
	if serial_no and not frappe.db.exists("Serial No", serial_no):
		if type_of_transaction != "Inward":
			frappe.throw(_("Serial No {0} does not exist").format(serial_no))

		make_serial_no(serial_no, item_code)

	if batch_no and not frappe.db.exists("Batch", batch_no):
		if type_of_transaction != "Inward":
			frappe.throw(_("Batch No {0} does not exist").format(batch_no))

		make_batch_no(batch_no, item_code)


def make_serial_no(serial_no, item_code):
	serial_no_doc = frappe.new_doc("Serial No")
	serial_no_doc.serial_no = serial_no
	serial_no_doc.item_code = item_code
	serial_no_doc.save(ignore_permissions=True)


def make_batch_no(batch_no, item_code):
	batch_doc = frappe.new_doc("Batch")
	batch_doc.batch_id = batch_no
	batch_doc.item = item_code
	batch_doc.save(ignore_permissions=True)


def parse_serial_nos(serial_no):
	if isinstance(serial_no, list):
		return serial_no

	return [s.strip() for s in cstr(serial_no).strip().replace(",", "\n").split("\n") if s.strip()]


def get_batch_qty_map(entries):
	qty_map = defaultdict(float)
	for row in entries:
		if row.batch_no:
			qty_map[row.batch_no] += abs(flt(row.qty))

	return qty_map
