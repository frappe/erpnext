from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.model.naming import make_autoname
from frappe.query_builder.functions import CombineDatetime, Sum, Timestamp
from frappe.utils import cint, cstr, flt, get_link_to_form, now, nowtime, today
from pypika import Order

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
			and self.item_details.has_serial_no == 1
		):
			self.make_serial_batch_no_bundle()
		elif not self.sle.is_cancelled:
			self.validate_item_and_warehouse()

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

	def make_serial_batch_no_bundle_for_material_transfer(self):
		from erpnext.controllers.stock_controller import make_bundle_for_material_transfer

		bundle = frappe.db.get_value(
			"Stock Entry Detail", self.sle.voucher_detail_no, "serial_and_batch_bundle"
		)

		if bundle:
			new_bundle_id = make_bundle_for_material_transfer(
				is_new=False,
				docstatus=1,
				voucher_type=self.sle.voucher_type,
				voucher_no=self.sle.voucher_no,
				serial_and_batch_bundle=bundle,
				warehouse=self.sle.warehouse,
				type_of_transaction="Inward" if self.sle.actual_qty > 0 else "Outward",
				do_not_submit=0,
			)
			self.sle.db_set({"serial_and_batch_bundle": new_bundle_id})

	def make_serial_batch_no_bundle(self):
		self.validate_item()
		if self.sle.actual_qty > 0 and self.is_material_transfer():
			self.make_serial_batch_no_bundle_for_material_transfer()
			return

		sn_doc = SerialBatchCreation(
			{
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"posting_date": self.sle.posting_date,
				"posting_time": self.sle.posting_time,
				"voucher_type": self.sle.voucher_type,
				"voucher_no": self.sle.voucher_no,
				"voucher_detail_no": self.sle.voucher_detail_no,
				"qty": self.sle.actual_qty,
				"avg_rate": self.sle.incoming_rate,
				"total_amount": flt(self.sle.actual_qty) * flt(self.sle.incoming_rate),
				"type_of_transaction": "Inward" if self.sle.actual_qty > 0 else "Outward",
				"company": self.company,
				"is_rejected": self.is_rejected_entry(),
			}
		).make_serial_and_batch_bundle()

		self.set_serial_and_batch_bundle(sn_doc)

	def validate_actual_qty(self, sn_doc):
		link = get_link_to_form("Serial and Batch Bundle", sn_doc.name)

		condition = {
			"Inward": self.sle.actual_qty > 0,
			"Outward": self.sle.actual_qty < 0,
		}.get(sn_doc.type_of_transaction)

		if not condition:
			correct_type = "Inward"
			if sn_doc.type_of_transaction == "Inward":
				correct_type = "Outward"

			msg = f"The type of transaction of Serial and Batch Bundle {link} is {bold(sn_doc.type_of_transaction)} but as per the Actual Qty {self.sle.actual_qty} for the item {bold(self.sle.item_code)} in the {self.sle.voucher_type} {self.sle.voucher_no} the type of transaction should be {bold(correct_type)}"
			frappe.throw(_(msg), title=_("Incorrect Type of Transaction"))

		precision = sn_doc.precision("total_qty")
		if flt(sn_doc.total_qty, precision) != flt(self.sle.actual_qty, precision):
			msg = f"Total qty {flt(sn_doc.total_qty, precision)} of Serial and Batch Bundle {link} is not equal to Actual Qty {flt(self.sle.actual_qty, precision)} in the {self.sle.voucher_type} {self.sle.voucher_no}"
			frappe.throw(_(msg))

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
				and not frappe.db.get_single_value("Stock Settings", "naming_series_prefix")
			):
				msg += f". If you want auto pick batch bundle, then kindly set Batch Number Series in Item {self.item_code}"

		elif self.sle.actual_qty < 0:
			if not frappe.db.get_single_value(
				"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward"
			):
				msg += ". If you want auto pick serial/batch bundle, then kindly enable 'Auto Create Serial and Batch Bundle' in Stock Settings."

		if msg:
			error_msg = (
				f"Serial and Batch Bundle not set for item {self.item_code} in warehouse {self.warehouse}."
				+ msg
			)
			frappe.throw(_(error_msg))

	def set_serial_and_batch_bundle(self, sn_doc):
		self.sle.db_set({"serial_and_batch_bundle": sn_doc.name, "auto_created_serial_and_batch_bundle": 1})

		if sn_doc.is_rejected:
			frappe.db.set_value(
				self.child_doctype,
				self.sle.voucher_detail_no,
				"rejected_serial_and_batch_bundle",
				sn_doc.name,
			)
		else:
			values_to_update = {
				"serial_and_batch_bundle": sn_doc.name,
			}

			if self.sle.actual_qty < 0 and self.is_material_transfer():
				values_to_update["valuation_rate"] = sn_doc.avg_rate

			if not frappe.db.get_single_value(
				"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle"
			):
				if sn_doc.has_serial_no:
					values_to_update["serial_no"] = ",".join(cstr(d.serial_no) for d in sn_doc.entries)
				elif sn_doc.has_batch_no and len(sn_doc.entries) == 1:
					values_to_update["batch_no"] = sn_doc.entries[0].batch_no

			frappe.db.set_value(self.child_doctype, self.sle.voucher_detail_no, values_to_update)

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

	def process_batch_no(self):
		if (
			not self.sle.is_cancelled
			and not self.sle.serial_and_batch_bundle
			and self.item_details.has_batch_no == 1
			and self.item_details.create_new_batch
		):
			self.make_serial_batch_no_bundle()
		elif not self.sle.is_cancelled:
			self.validate_item_and_warehouse()

	def validate_item_and_warehouse(self):
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
			{"is_cancelled": 1},
		)

		if self.sle.serial_and_batch_bundle:
			frappe.get_cached_doc(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle
			).validate_serial_and_batch_inventory()

	def post_process(self):
		if not self.sle.serial_and_batch_bundle and not self.sle.serial_no and not self.sle.batch_no:
			return

		if self.sle.serial_and_batch_bundle:
			docstatus = frappe.get_cached_value(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle, "docstatus"
			)

			if docstatus != 1:
				self.submit_serial_and_batch_bundle()

		if self.item_details.has_serial_no == 1:
			self.set_warehouse_and_status_in_serial_nos()

		if (
			self.sle.actual_qty > 0
			and self.item_details.has_serial_no == 1
			and self.item_details.has_batch_no == 1
		):
			self.set_batch_no_in_serial_nos()

		if self.item_details.has_batch_no == 1:
			self.update_batch_qty()

		if self.sle.is_cancelled and self.sle.serial_and_batch_bundle:
			self.cancel_serial_and_batch_bundle()

	def cancel_serial_and_batch_bundle(self):
		frappe.get_cached_doc("Serial and Batch Bundle", self.sle.serial_and_batch_bundle).cancel()

	def submit_serial_and_batch_bundle(self):
		doc = frappe.get_doc("Serial and Batch Bundle", self.sle.serial_and_batch_bundle)
		self.validate_actual_qty(doc)

		doc.flags.ignore_voucher_validation = True
		doc.submit()

	def set_warehouse_and_status_in_serial_nos(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as get_parsed_serial_nos

		serial_nos = get_serial_nos(self.sle.serial_and_batch_bundle)
		if not self.sle.serial_and_batch_bundle and self.sle.serial_no:
			serial_nos = get_parsed_serial_nos(self.sle.serial_no)

		warehouse = self.warehouse if self.sle.actual_qty > 0 else None

		if not serial_nos:
			return

		status = "Inactive"
		if self.sle.actual_qty < 0:
			status = "Delivered"

		sn_table = frappe.qb.DocType("Serial No")
		(
			frappe.qb.update(sn_table)
			.set(sn_table.warehouse, warehouse)
			.set(
				sn_table.status,
				"Active"
				if warehouse
				else status
				if (sn_table.purchase_document_no != self.sle.voucher_no and self.sle.is_cancelled != 1)
				else "Inactive",
			)
			.set(sn_table.company, self.sle.company)
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

	def update_batch_qty(self):
		from erpnext.stock.doctype.batch.batch import get_available_batches

		batches = get_batch_nos(self.sle.serial_and_batch_bundle)
		if not self.sle.serial_and_batch_bundle and self.sle.batch_no:
			batches = frappe._dict({self.sle.batch_no: self.sle.actual_qty})

		batches_qty = get_available_batches(
			frappe._dict({"item_code": self.item_code, "batch_no": list(batches.keys())})
		)

		for batch_no in batches:
			frappe.db.set_value("Batch", batch_no, "batch_qty", batches_qty.get(batch_no, 0))


def get_serial_nos(serial_and_batch_bundle, serial_nos=None):
	if not serial_and_batch_bundle:
		return []

	filters = {"parent": serial_and_batch_bundle, "serial_no": ("is", "set")}
	if isinstance(serial_and_batch_bundle, list):
		filters = {"parent": ("in", serial_and_batch_bundle)}

	if serial_nos:
		filters["serial_no"] = ("in", serial_nos)

	serial_nos = frappe.get_all("Serial and Batch Entry", filters=filters, order_by="idx", pluck="serial_no")

	return serial_nos


def get_batches_from_bundle(serial_and_batch_bundle, batches=None):
	if not serial_and_batch_bundle:
		return []

	filters = {"parent": serial_and_batch_bundle, "batch_no": ("is", "set")}
	if isinstance(serial_and_batch_bundle, list):
		filters = {"parent": ("in", serial_and_batch_bundle)}

	if batches:
		filters["batch_no"] = ("in", batches)

	entries = frappe.get_all(
		"Serial and Batch Entry", fields=["batch_no", "qty"], filters=filters, order_by="idx", as_list=1
	)
	if not entries:
		return frappe._dict({})

	return frappe._dict(entries)


def get_serial_nos_from_bundle(serial_and_batch_bundle, serial_nos=None):
	return get_serial_nos(serial_and_batch_bundle, serial_nos=serial_nos)


def get_serial_or_batch_nos(bundle):
	# For print format

	bundle_data = frappe.get_cached_value(
		"Serial and Batch Bundle", bundle, ["has_serial_no", "has_batch_no"], as_dict=True
	)

	fields = []
	if bundle_data.has_serial_no:
		fields.append("serial_no")

	if bundle_data.has_batch_no:
		fields.extend(["batch_no", "qty"])

	data = frappe.get_all("Serial and Batch Entry", fields=fields, filters={"parent": bundle})

	if bundle_data.has_serial_no and not bundle_data.has_batch_no:
		return ", ".join([d.serial_no for d in data])

	elif bundle_data.has_batch_no:
		html = "<table class= 'table table-borderless' style='margin-top: 0px;margin-bottom: 0px;'>"
		for d in data:
			if d.serial_no:
				html += f"<tr><td>{d.batch_no}</th><th>{d.serial_no}</th	><th>{abs(d.qty)}</th></tr>"
			else:
				html += f"<tr><td>{d.batch_no}</td><td>{abs(d.qty)}</td></tr>"

		html += "</table>"

		return html


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

			serial_nos = self.get_serial_nos()
			for serial_no in serial_nos:
				incoming_rate = self.get_incoming_rate_from_bundle(serial_no)
				if not incoming_rate:
					continue

				self.stock_value_change += incoming_rate
				self.serial_no_incoming_rate[serial_no] += incoming_rate

			self.calculate_stock_value_from_deprecarated_ledgers()

	def get_incoming_rate_from_bundle(self, serial_no) -> float:
		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		bundle_child = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(bundle)
			.inner_join(bundle_child)
			.on(bundle.name == bundle_child.parent)
			.select((bundle_child.incoming_rate * bundle_child.qty).as_("incoming_rate"))
			.where(
				(bundle.is_cancelled == 0)
				& (bundle.docstatus == 1)
				& (bundle_child.serial_no == serial_no)
				& (bundle.type_of_transaction == "Inward")
				& (bundle_child.qty > 0)
				& (bundle.item_code == self.sle.item_code)
				& (bundle_child.warehouse == self.sle.warehouse)
			)
			.orderby(Timestamp(bundle.posting_date, bundle.posting_time), order=Order.desc)
			.limit(1)
		)

		# Important to exclude the current voucher to calculate correct the stock value difference
		if self.sle.voucher_no:
			query = query.where(bundle.voucher_no != self.sle.voucher_no)

		if self.sle.posting_date:
			if self.sle.posting_time is None:
				self.sle.posting_time = nowtime()

			timestamp_condition = CombineDatetime(
				bundle.posting_date, bundle.posting_time
			) <= CombineDatetime(self.sle.posting_date, self.sle.posting_time)

			query = query.where(timestamp_condition)

		incoming_rate = query.run()
		return flt(incoming_rate[0][0]) if incoming_rate else 0.0

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
		return abs(flt(self.stock_value_change) / flt(self.sle.actual_qty))

	def get_incoming_rate_of_serial_no(self, serial_no):
		return self.serial_no_incoming_rate.get(serial_no, 0.0)


def is_rejected(voucher_type, voucher_detail_no, warehouse):
	if voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
		return warehouse == frappe.get_cached_value(
			voucher_type + " Item", voucher_detail_no, "rejected_warehouse"
		)

	return False


class BatchNoValuation(DeprecatedBatchNoValuation):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

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
			entries = self.get_batch_no_ledgers()
			self.stock_value_change = 0.0
			self.batch_avg_rate = defaultdict(float)
			self.available_qty = defaultdict(float)
			self.stock_value_differece = defaultdict(float)

			for ledger in entries:
				self.stock_value_differece[ledger.batch_no] += flt(ledger.incoming_rate)
				self.available_qty[ledger.batch_no] += flt(ledger.qty)

			self.calculate_avg_rate_from_deprecarated_ledgers()
			self.calculate_avg_rate_for_non_batchwise_valuation()
			self.set_stock_value_difference()

	def get_batch_no_ledgers(self) -> list[dict]:
		if not self.batchwise_valuation_batches:
			return []

		parent = frappe.qb.DocType("Serial and Batch Bundle")
		child = frappe.qb.DocType("Serial and Batch Entry")

		timestamp_condition = ""
		if self.sle.posting_date and self.sle.posting_time:
			timestamp_condition = CombineDatetime(
				parent.posting_date, parent.posting_time
			) <= CombineDatetime(self.sle.posting_date, self.sle.posting_time)

		query = (
			frappe.qb.from_(parent)
			.inner_join(child)
			.on(parent.name == child.parent)
			.select(
				child.batch_no,
				Sum(child.stock_value_difference).as_("incoming_rate"),
				Sum(child.qty).as_("qty"),
			)
			.where(
				(child.batch_no.isin(self.batchwise_valuation_batches))
				& (parent.warehouse == self.sle.warehouse)
				& (parent.item_code == self.sle.item_code)
				& (parent.docstatus == 1)
				& (parent.is_cancelled == 0)
				& (parent.type_of_transaction.isin(["Inward", "Outward"]))
			)
			.groupby(child.batch_no)
		)

		# Important to exclude the current voucher detail no / voucher no to calculate the correct stock value difference
		if self.sle.voucher_detail_no:
			query = query.where(parent.voucher_detail_no != self.sle.voucher_detail_no)
		elif self.sle.voucher_no:
			query = query.where(parent.voucher_no != self.sle.voucher_no)

		query = query.where(parent.voucher_type != "Pick List")
		if timestamp_condition:
			query = query.where(timestamp_condition)

		return query.run(as_dict=True)

	def prepare_batches(self):
		self.batches = self.batch_nos
		if isinstance(self.batch_nos, dict):
			self.batches = list(self.batch_nos.keys())

		self.batchwise_valuation_batches = []
		self.non_batchwise_valuation_batches = []

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

			frappe.db.set_value(
				"Serial and Batch Entry",
				ledger.name,
				{
					"stock_value_difference": stock_value_change,
					"incoming_rate": self.batch_avg_rate[batch_no],
				},
			)

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

		return abs(flt(self.stock_value_change) / flt(self.sle.actual_qty))

	def get_actual_qty(self):
		total_qty = 0.0
		for batch_no in self.available_qty:
			total_qty += self.available_qty[batch_no]

		return total_qty


def get_batch_nos(serial_and_batch_bundle):
	if not serial_and_batch_bundle:
		return frappe._dict({})

	entries = frappe.get_all(
		"Serial and Batch Entry",
		fields=["batch_no", "qty", "name"],
		filters={"parent": serial_and_batch_bundle, "batch_no": ("is", "set")},
		order_by="idx",
	)

	if not entries:
		return frappe._dict({})

	return {d.batch_no: d for d in entries}


def get_empty_batches_based_work_order(work_order, item_code):
	batches = get_batches_from_work_order(work_order, item_code)
	if not batches:
		return batches

	entries = get_batches_from_stock_entries(work_order, item_code)
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
		fields=["batch_no", "qty", "serial_and_batch_bundle"],
		filters={
			"parent": ("in", [d.name for d in entries]),
			"is_finished_item": 1,
			"item_code": item_code,
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
		if not self.get("posting_date"):
			self.posting_date = today()
			self.__dict__["posting_date"] = self.posting_date

		if not self.get("actual_qty"):
			qty = self.get("qty") or self.get("total_qty")

			self.actual_qty = qty
			self.__dict__["actual_qty"] = self.actual_qty

		if not hasattr(self, "use_serial_batch_fields"):
			self.use_serial_batch_fields = 0

	def duplicate_package(self):
		if not self.serial_and_batch_bundle:
			return

		id = self.serial_and_batch_bundle
		package = frappe.get_doc("Serial and Batch Bundle", id)
		new_package = frappe.copy_doc(package)

		if self.get("returned_serial_nos"):
			self.remove_returned_serial_nos(new_package)

		new_package.docstatus = 0
		new_package.warehouse = self.warehouse
		new_package.voucher_no = ""
		new_package.posting_date = self.posting_date if hasattr(self, "posting_date") else today()
		new_package.posting_time = self.posting_time if hasattr(self, "posting_time") else nowtime()
		new_package.type_of_transaction = self.type_of_transaction
		new_package.returned_against = self.get("returned_against")

		if self.get("do_not_save"):
			return new_package

		new_package.save()

		self.serial_and_batch_bundle = new_package.name

	def remove_returned_serial_nos(self, package):
		remove_list = []
		for d in package.entries:
			if d.serial_no in self.returned_serial_nos:
				remove_list.append(d)

		for d in remove_list:
			package.remove(d)

	def make_serial_and_batch_bundle(self):
		doc = frappe.new_doc("Serial and Batch Bundle")
		valid_columns = doc.meta.get_valid_columns()
		for key, value in self.__dict__.items():
			if key in valid_columns:
				doc.set(key, value)

		if self.type_of_transaction == "Outward":
			self.set_auto_serial_batch_entries_for_outward()
		elif self.type_of_transaction == "Inward":
			self.set_auto_serial_batch_entries_for_inward()
			self.add_serial_nos_for_batch_item()

		if hasattr(self, "via_landed_cost_voucher") and self.via_landed_cost_voucher:
			doc.flags.via_landed_cost_voucher = self.via_landed_cost_voucher

		self.set_serial_batch_entries(doc)
		if not doc.get("entries"):
			return frappe._dict({})

		if doc.voucher_no and frappe.get_cached_value(doc.voucher_type, doc.voucher_no, "docstatus") == 2:
			doc.voucher_no = ""

		doc.save()
		self.validate_qty(doc)

		if not hasattr(self, "do_not_submit") or not self.do_not_submit:
			doc.flags.ignore_voucher_validation = True
			doc.submit()

		return doc

	def add_serial_nos_for_batch_item(self):
		if not (self.has_serial_no and self.has_batch_no):
			return

		if not self.get("serial_nos") and self.get("batches"):
			batches = list(self.get("batches").keys())
			if len(batches) == 1:
				self.batch_no = batches[0]
				self.serial_nos = self.get_auto_created_serial_nos()

	def update_serial_and_batch_entries(self):
		doc = frappe.get_doc("Serial and Batch Bundle", self.serial_and_batch_bundle)
		doc.type_of_transaction = self.type_of_transaction
		doc.set("entries", [])
		self.set_auto_serial_batch_entries_for_outward()
		self.set_serial_batch_entries(doc)
		if not doc.get("entries"):
			return frappe._dict({})

		doc.save()
		return doc

	def validate_qty(self, doc):
		if doc.type_of_transaction == "Outward" and self.actual_qty and doc.total_qty:
			precision = doc.precision("total_qty")

			total_qty = flt(abs(doc.total_qty), precision)
			required_qty = flt(abs(self.actual_qty), precision)

			if required_qty - total_qty > 0:
				msg = f"For the item {bold(doc.item_code)}, the Avaliable qty {bold(total_qty)} is less than the Required Qty {bold(required_qty)} in the warehouse {bold(doc.warehouse)}. Please add sufficient qty in the warehouse."
				frappe.throw(msg, title=_("Insufficient Stock"))

	def set_auto_serial_batch_entries_for_outward(self):
		from erpnext.stock.doctype.batch.batch import get_available_batches
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos_for_outward

		kwargs = frappe._dict(
			{
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"qty": abs(self.actual_qty) if self.actual_qty else 0,
				"based_on": frappe.db.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
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

	def set_serial_batch_entries(self, doc):
		if self.get("serial_nos"):
			serial_no_wise_batch = frappe._dict({})
			if self.has_batch_no:
				serial_no_wise_batch = get_serial_nos_batch(self.serial_nos)

			qty = -1 if self.type_of_transaction == "Outward" else 1
			for serial_no in self.serial_nos:
				doc.append(
					"entries",
					{
						"serial_no": serial_no,
						"qty": qty,
						"batch_no": serial_no_wise_batch.get(serial_no) or self.get("batch_no"),
						"incoming_rate": self.get("incoming_rate"),
					},
				)

		elif self.get("batches"):
			for batch_no, batch_qty in self.batches.items():
				doc.append(
					"entries",
					{
						"batch_no": batch_no,
						"qty": batch_qty * (-1 if self.type_of_transaction == "Outward" else 1),
						"incoming_rate": self.get("incoming_rate"),
					},
				)

	def create_batch(self):
		from erpnext.stock.doctype.batch.batch import make_batch

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
			msg = f"Please set Serial No Series in the item {self.item_code} or create Serial and Batch Bundle manually."
			frappe.throw(_(msg))

		for _i in range(abs(cint(self.actual_qty))):
			serial_no = make_autoname(self.serial_no_series, "Serial No")
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
				"batch_no",
			]

			frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

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
