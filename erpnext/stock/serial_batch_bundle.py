from collections import defaultdict
from typing import List

import frappe
from frappe import _, bold
from frappe.model.naming import make_autoname
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import cint, flt, now

from erpnext.stock.deprecated_serial_batch import (
	DeprecatedBatchNoValuation,
	DeprecatedSerialNoValuation,
)
from erpnext.stock.valuation import round_off_if_near_zero


class SerialBatchBundle:
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.set_item_details()
		self.process_serial_and_batch_bundle()
		if self.sle.is_cancelled:
			self.delink_serial_and_batch_bundle()

		self.post_process()

	def process_serial_and_batch_bundle(self):
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
			and not self.sle.serial_and_batch_bundle
			and self.sle.actual_qty > 0
			and self.item_details.has_serial_no == 1
			and self.item_details.serial_no_series
			and self.allow_to_make_auto_bundle()
		):
			self.make_serial_batch_no_bundle()
		elif not self.sle.is_cancelled:
			self.validate_item_and_warehouse()

	def auto_create_serial_nos(self, batch_no=None):
		sr_nos = []
		serial_nos_details = []

		for i in range(cint(self.sle.actual_qty)):
			serial_no = make_autoname(self.item_details.serial_no_series, "Serial No")
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
					self.item_details.item_name,
					self.item_details.description,
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

		return sr_nos

	def make_serial_batch_no_bundle(self):
		sn_doc = frappe.new_doc("Serial and Batch Bundle")
		sn_doc.item_code = self.item_code
		sn_doc.warehouse = self.warehouse
		sn_doc.item_name = self.item_details.item_name
		sn_doc.item_group = self.item_details.item_group
		sn_doc.has_serial_no = self.item_details.has_serial_no
		sn_doc.has_batch_no = self.item_details.has_batch_no
		sn_doc.voucher_type = self.sle.voucher_type
		sn_doc.voucher_no = self.sle.voucher_no
		sn_doc.voucher_detail_no = self.sle.voucher_detail_no
		sn_doc.total_qty = self.sle.actual_qty
		sn_doc.avg_rate = self.sle.incoming_rate
		sn_doc.total_amount = flt(self.sle.actual_qty) * flt(self.sle.incoming_rate)
		sn_doc.type_of_transaction = "Inward"
		sn_doc.posting_date = self.sle.posting_date
		sn_doc.posting_time = self.sle.posting_time
		sn_doc.is_rejected = self.is_rejected_entry()

		sn_doc.flags.ignore_mandatory = True
		sn_doc.insert()

		batch_no = ""
		if self.item_details.has_batch_no:
			batch_no = self.create_batch()

		incoming_rate = self.sle.incoming_rate
		if not incoming_rate:
			incoming_rate = frappe.get_cached_value(
				self.child_doctype, self.sle.voucher_detail_no, "valuation_rate"
			)

		if self.item_details.has_serial_no:
			sr_nos = self.auto_create_serial_nos(batch_no)
			self.add_serial_no_to_bundle(sn_doc, sr_nos, incoming_rate, batch_no)
		elif self.item_details.has_batch_no:
			self.add_batch_no_to_bundle(sn_doc, batch_no, incoming_rate)

		sn_doc.save()
		sn_doc.submit()
		self.set_serial_and_batch_bundle(sn_doc)

	def set_serial_and_batch_bundle(self, sn_doc):
		self.sle.db_set("serial_and_batch_bundle", sn_doc.name)

		if sn_doc.is_rejected:
			frappe.db.set_value(
				self.child_doctype, self.sle.voucher_detail_no, "rejected_serial_and_batch_bundle", sn_doc.name
			)
		else:
			frappe.db.set_value(
				self.child_doctype, self.sle.voucher_detail_no, "serial_and_batch_bundle", sn_doc.name
			)

	@property
	def child_doctype(self):
		child_doctype = self.sle.voucher_type + " Item"
		if self.sle.voucher_type == "Stock Entry":
			child_doctype = "Stock Entry Detail"

		return child_doctype

	def is_rejected_entry(self):
		return is_rejected(self.sle.voucher_type, self.sle.voucher_detail_no, self.sle.warehouse)

	def add_serial_no_to_bundle(self, sn_doc, serial_nos, incoming_rate, batch_no=None):
		for serial_no in serial_nos:
			sn_doc.append(
				"entries",
				{
					"serial_no": serial_no,
					"qty": 1,
					"incoming_rate": incoming_rate,
					"batch_no": batch_no,
					"warehouse": self.warehouse,
					"is_outward": 0,
				},
			)

	def add_batch_no_to_bundle(self, sn_doc, batch_no, incoming_rate):
		stock_value_difference = flt(self.sle.actual_qty) * flt(incoming_rate)

		if self.sle.actual_qty < 0:
			stock_value_difference *= -1

		sn_doc.append(
			"entries",
			{
				"batch_no": batch_no,
				"qty": self.sle.actual_qty,
				"incoming_rate": incoming_rate,
				"stock_value_difference": stock_value_difference,
			},
		)

	def create_batch(self):
		from erpnext.stock.doctype.batch.batch import make_batch

		return make_batch(
			frappe._dict(
				{
					"item": self.item_code,
					"reference_doctype": self.sle.voucher_type,
					"reference_name": self.sle.voucher_no,
				}
			)
		)

	def process_batch_no(self):
		if (
			not self.sle.is_cancelled
			and not self.sle.serial_and_batch_bundle
			and self.sle.actual_qty > 0
			and self.item_details.has_batch_no == 1
			and self.item_details.create_new_batch
			and self.item_details.batch_number_series
			and self.allow_to_make_auto_bundle()
		):
			self.make_serial_batch_no_bundle()
		elif not self.sle.is_cancelled:
			self.validate_item_and_warehouse()

	def validate_item_and_warehouse(self):

		data = frappe.db.get_value(
			"Serial and Batch Bundle",
			self.sle.serial_and_batch_bundle,
			["item_code", "warehouse", "voucher_no", "name"],
			as_dict=1,
		)

		if self.sle.serial_and_batch_bundle and not frappe.db.exists(
			"Serial and Batch Bundle",
			{
				"name": self.sle.serial_and_batch_bundle,
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"voucher_no": self.sle.voucher_no,
			},
		):
			msg = f"""
					The Serial and Batch Bundle
					{bold(self.sle.serial_and_batch_bundle)}
					does not belong to Item {bold(self.item_code)}
					or Warehouse {bold(self.warehouse)}
					or {self.sle.voucher_type} no {bold(self.sle.voucher_no)}
				"""

			frappe.throw(_(msg))

	def delink_serial_and_batch_bundle(self):
		update_values = {
			"serial_and_batch_bundle": "",
		}

		if is_rejected(self.sle.voucher_type, self.sle.voucher_detail_no, self.sle.warehouse):
			update_values["rejected_serial_and_batch_bundle"] = ""

		frappe.db.set_value(self.child_doctype, self.sle.voucher_detail_no, update_values)

		frappe.db.set_value(
			"Serial and Batch Bundle",
			{"voucher_no": self.sle.voucher_no, "voucher_type": self.sle.voucher_type},
			{"is_cancelled": 1, "voucher_no": ""},
		)

	def allow_to_make_auto_bundle(self):
		if self.sle.voucher_type in ["Stock Entry", "Purchase Receipt", "Purchase Invoice"]:
			if self.sle.voucher_type == "Stock Entry":
				stock_entry_type = frappe.get_cached_value("Stock Entry", self.sle.voucher_no, "purpose")

				if stock_entry_type in ["Material Receipt", "Manufacture", "Repack"]:
					return True

			return True

		return False

	def post_process(self):
		if not self.sle.serial_and_batch_bundle:
			return

		if self.item_details.has_serial_no == 1:
			self.set_warehouse_and_status_in_serial_nos()

		if (
			self.sle.actual_qty > 0
			and self.item_details.has_serial_no == 1
			and self.item_details.has_batch_no == 1
		):
			self.set_batch_no_in_serial_nos()

	def set_warehouse_and_status_in_serial_nos(self):
		serial_nos = get_serial_nos(self.sle.serial_and_batch_bundle, check_outward=False)
		warehouse = self.warehouse if self.sle.actual_qty > 0 else None

		if not serial_nos:
			return

		sn_table = frappe.qb.DocType("Serial No")
		(
			frappe.qb.update(sn_table)
			.set(sn_table.warehouse, warehouse)
			.set(sn_table.status, "Active" if warehouse else "Inactive")
			.where(sn_table.name.isin(serial_nos))
		).run()

	def set_batch_no_in_serial_nos(self):
		entries = frappe.get_all(
			"Serial and Batch Entry",
			fields=["serial_no", "batch_no"],
			filters={"parent": self.sle.serial_and_batch_bundle},
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


def get_serial_nos(serial_and_batch_bundle, check_outward=True):
	filters = {"parent": serial_and_batch_bundle}
	if check_outward:
		filters["is_outward"] = 1

	entries = frappe.get_all("Serial and Batch Entry", fields=["serial_no"], filters=filters)

	return [d.serial_no for d in entries]


class SerialNoBundleValuation(DeprecatedSerialNoValuation):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.calculate_stock_value_change()
		self.calculate_valuation_rate()

	def calculate_stock_value_change(self):
		if self.sle.actual_qty > 0:
			self.stock_value_change = frappe.get_cached_value(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle, "total_amount"
			)

		else:
			entries = self.get_serial_no_ledgers()

			self.serial_no_incoming_rate = defaultdict(float)
			self.stock_value_change = 0.0

			for ledger in entries:
				self.stock_value_change += ledger.incoming_rate * -1
				self.serial_no_incoming_rate[ledger.serial_no] = ledger.incoming_rate

			self.calculate_stock_value_from_deprecarated_ledgers()

	def get_serial_no_ledgers(self):
		serial_nos = self.get_serial_nos()

		subquery = f"""
			SELECT
				MAX(
					TIMESTAMP(
						parent.posting_date, parent.posting_time
					)
				), child.name, child.serial_no, child.warehouse
			FROM
				`tabSerial and Batch Bundle` as parent,
				`tabSerial and Batch Entry` as child
			WHERE
				parent.name = child.parent
				AND child.serial_no IN ({', '.join([frappe.db.escape(s) for s in serial_nos])})
				AND child.is_outward = 0
				AND parent.docstatus = 1
				AND parent.is_cancelled = 0
				AND child.warehouse = {frappe.db.escape(self.sle.warehouse)}
				AND parent.item_code = {frappe.db.escape(self.sle.item_code)}
				AND (
					parent.posting_date < '{self.sle.posting_date}'
					OR (
						parent.posting_date = '{self.sle.posting_date}'
						AND parent.posting_time <= '{self.sle.posting_time}'
					)
				)
			GROUP BY
				child.serial_no
		"""

		return frappe.db.sql(
			f"""
			SELECT
				ledger.serial_no, ledger.incoming_rate, ledger.warehouse
			FROM
				`tabSerial and Batch Entry` AS ledger,
				({subquery}) AS SubQuery
			WHERE
				ledger.name = SubQuery.name
				AND ledger.serial_no = SubQuery.serial_no
				AND ledger.warehouse = SubQuery.warehouse
			GROUP BY
				ledger.serial_no
			Order By
				ledger.creation
		""",
			as_dict=1,
		)

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

		if (
			not self.wh_data.valuation_rate and self.sle.voucher_detail_no and not self.is_rejected_entry()
		):
			allow_zero_rate = self.sle_self.check_if_allow_zero_valuation_rate(
				self.sle.voucher_type, self.sle.voucher_detail_no
			)
			if not allow_zero_rate:
				self.wh_data.valuation_rate = self.sle_self.get_fallback_rate(self.sle)

		self.wh_data.qty_after_transaction += self.sle.actual_qty
		self.wh_data.stock_value = flt(self.wh_data.qty_after_transaction) * flt(
			self.wh_data.valuation_rate
		)

	def is_rejected_entry(self):
		return is_rejected(self.sle.voucher_type, self.sle.voucher_detail_no, self.sle.warehouse)

	def get_incoming_rate(self):
		return abs(flt(self.stock_value_change) / flt(self.sle.actual_qty))


def is_rejected(voucher_type, voucher_detail_no, warehouse):
	if voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
		return warehouse == frappe.get_cached_value(
			voucher_type + " Item", voucher_detail_no, "rejected_warehouse"
		)

	return False


class BatchNoBundleValuation(DeprecatedBatchNoValuation):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.batch_nos = self.get_batch_nos()
		self.calculate_avg_rate()
		self.calculate_valuation_rate()

	def calculate_avg_rate(self):
		if self.sle.actual_qty > 0:
			self.stock_value_change = frappe.get_cached_value(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle, "total_amount"
			)
		else:
			entries = self.get_batch_no_ledgers()

			self.batch_avg_rate = defaultdict(float)
			self.available_qty = defaultdict(float)
			for ledger in entries:
				self.batch_avg_rate[ledger.batch_no] += flt(ledger.incoming_rate) / flt(ledger.qty)
				self.available_qty[ledger.batch_no] += flt(ledger.qty)

			self.calculate_avg_rate_from_deprecarated_ledgers()
			self.set_stock_value_difference()

	def get_batch_no_ledgers(self) -> List[dict]:
		parent = frappe.qb.DocType("Serial and Batch Bundle")
		child = frappe.qb.DocType("Serial and Batch Entry")

		batch_nos = list(self.batch_nos.keys())

		timestamp_condition = CombineDatetime(
			parent.posting_date, parent.posting_time
		) < CombineDatetime(self.sle.posting_date, self.sle.posting_time)

		return (
			frappe.qb.from_(parent)
			.inner_join(child)
			.on(parent.name == child.parent)
			.select(
				child.batch_no,
				Sum(child.stock_value_difference).as_("incoming_rate"),
				Sum(child.qty).as_("qty"),
			)
			.where(
				(child.batch_no.isin(batch_nos))
				& (child.parent != self.sle.serial_and_batch_bundle)
				& (parent.warehouse == self.sle.warehouse)
				& (parent.item_code == self.sle.item_code)
				& (parent.docstatus == 1)
				& (parent.is_cancelled == 0)
			)
			.where(timestamp_condition)
			.groupby(child.batch_no)
		).run(as_dict=True)

	def get_batch_nos(self) -> list:
		if self.sle.get("batch_nos"):
			return self.sle.batch_nos

		entries = frappe.get_all(
			"Serial and Batch Entry",
			fields=["batch_no", "qty", "name"],
			filters={"parent": self.sle.serial_and_batch_bundle, "is_outward": 1},
		)

		return {d.batch_no: d for d in entries}

	def set_stock_value_difference(self):
		self.stock_value_change = 0
		for batch_no, ledger in self.batch_nos.items():
			stock_value_change = self.batch_avg_rate[batch_no] * ledger.qty
			self.stock_value_change += stock_value_change
			frappe.db.set_value(
				"Serial and Batch Entry", ledger.name, "stock_value_difference", stock_value_change
			)

	def calculate_valuation_rate(self):
		if not hasattr(self, "wh_data"):
			return

		self.wh_data.stock_value = round_off_if_near_zero(
			self.wh_data.stock_value + self.stock_value_change
		)

		if self.wh_data.qty_after_transaction:
			self.wh_data.valuation_rate = self.wh_data.stock_value / self.wh_data.qty_after_transaction

		self.wh_data.qty_after_transaction += self.sle.actual_qty

	def get_incoming_rate(self):
		return abs(flt(self.stock_value_change) / flt(self.sle.actual_qty))


def get_empty_batches_based_work_order(work_order, item_code):
	batches = get_batches_from_work_order(work_order)
	if not batches:
		return batches

	entries = get_batches_from_stock_entries(work_order)
	if not entries:
		return batches

	ids = [d.serial_and_batch_bundle for d in entries if d.serial_and_batch_bundle]
	if ids:
		set_batch_details_from_package(ids, batches)

	# Will be deprecated in v16
	for d in entries:
		if not d.batch_no:
			continue

		batches[d.batch_no] -= d.qty

	return batches


def get_batches_from_work_order(work_order):
	return frappe._dict(
		frappe.get_all(
			"Batch", fields=["name", "qty_to_produce"], filters={"reference_name": work_order}, as_list=1
		)
	)


def get_batches_from_stock_entries(work_order):
	entries = frappe.get_all(
		"Stock Entry",
		filters={"work_order": work_order, "docstatus": 1, "purpose": "Manufacture"},
		fields=["name"],
	)

	return frappe.get_all(
		"Stock Entry Detail",
		fields=["batch_no", "qty", "serial_and_batch_bundle"],
		filters={
			"parent": ("in", [d.name for d in entries]),
			"is_finished_item": 1,
		},
	)


def set_batch_details_from_package(ids, batches):
	entries = frappe.get_all(
		"Serial and Batch Entry",
		filters={"parent": ("in", ids), "is_outward": 0},
		fields=["batch_no", "qty"],
	)

	for d in entries:
		batches[d.batch_no] -= d.qty
