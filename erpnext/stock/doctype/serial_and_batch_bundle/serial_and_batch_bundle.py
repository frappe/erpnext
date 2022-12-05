# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import collections

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, today
from pypika import Case


class SerialandBatchBundle(Document):
	def validate(self):
		self.validate_serial_and_batch_no()
		self.validate_duplicate_serial_and_batch_no()

	def before_save(self):
		self.set_outgoing_rate()

		if self.ledgers:
			self.set_total_qty()
			self.set_avg_rate()

	@frappe.whitelist()
	def set_warehouse(self):
		for row in self.ledgers:
			row.warehouse = self.warehouse

	def set_total_qty(self):
		self.total_qty = sum([row.qty for row in self.ledgers])

	def set_avg_rate(self):
		self.total_amount = 0.0

		for row in self.ledgers:
			rate = flt(row.incoming_rate) or flt(row.outgoing_rate)
			self.total_amount += flt(row.qty) * rate

		if self.total_qty:
			self.avg_rate = flt(self.total_amount) / flt(self.total_qty)

	def set_outgoing_rate(self, update_rate=False):
		if not self.calculate_outgoing_rate():
			return

		serial_nos = [row.serial_no for row in self.ledgers]
		data = get_serial_and_batch_ledger(
			item_code=self.item_code,
			warehouse=self.ledgers[0].warehouse,
			serial_nos=serial_nos,
			fetch_incoming_rate=True,
		)

		if not data:
			return

		serial_no_details = {row.serial_no: row for row in data}

		for ledger in self.ledgers:
			if sn_details := serial_no_details.get(ledger.serial_no):
				if ledger.outgoing_rate and ledger.outgoing_rate == sn_details.incoming_rate:
					continue

				ledger.outgoing_rate = sn_details.incoming_rate or 0.0
				if update_rate:
					ledger.db_set("outgoing_rate", ledger.outgoing_rate)

	def calculate_outgoing_rate(self):
		if not (self.has_serial_no and self.ledgers):
			return

		if not (self.voucher_type and self.voucher_no):
			return False

		if self.voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
			return frappe.get_cached_value(self.voucher_type, self.voucher_no, "is_return")
		elif self.voucher_type in ["Sales Invoice", "Delivery Note"]:
			return not frappe.get_cached_value(self.voucher_type, self.voucher_no, "is_return")
		elif self.voucher_type == "Stock Entry":
			return frappe.get_cached_value(self.voucher_type, self.voucher_no, "purpose") in [
				"Material Receipt"
			]

	def validate_serial_and_batch_no(self):
		if self.item_code and not self.has_serial_no and not self.has_batch_no:
			msg = f"The Item {self.item_code} does not have Serial No or Batch No"
			frappe.throw(_(msg))

	def validate_duplicate_serial_and_batch_no(self):
		serial_nos = []
		batch_nos = []

		for row in self.ledgers:
			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no:
				batch_nos.append(row.batch_no)

		if serial_nos:
			for key, value in collections.Counter(serial_nos).items():
				if value > 1:
					frappe.throw(_(f"Duplicate Serial No {key} found"))

		if batch_nos:
			for key, value in collections.Counter(batch_nos).items():
				if value > 1:
					frappe.throw(_(f"Duplicate Batch No {key} found"))

	def before_cancel(self):
		self.delink_serial_and_batch_bundle()
		self.clear_table()

	def delink_serial_and_batch_bundle(self):
		self.voucher_no = None

		sles = frappe.get_all("Stock Ledger Entry", filters={"serial_and_batch_bundle": self.name})

		for sle in sles:
			frappe.db.set_value("Stock Ledger Entry", sle.name, "serial_and_batch_bundle", None)

	def clear_table(self):
		self.set("ledgers", [])

	def delink_refernce_from_voucher(self):
		child_table = f"{self.voucher_type} Item"
		if self.voucher_type == "Stock Entry":
			child_table = f"{self.voucher_type} Detail"

		vouchers = frappe.get_all(
			child_table,
			fields=["name"],
			filters={"serial_and_batch_bundle": self.name, "docstatus": 0},
		)

		for voucher in vouchers:
			frappe.db.set_value(child_table, voucher.name, "serial_and_batch_bundle", None)

	def delink_reference_from_batch(self):
		batches = frappe.get_all(
			"Batch",
			fields=["name"],
			filters={"reference_name": self.name, "reference_doctype": "Serial and Batch Bundle"},
		)

		for batch in batches:
			frappe.db.set_value("Batch", batch.name, {"reference_name": None, "reference_doctype": None})

	def on_trash(self):
		self.delink_refernce_from_voucher()
		self.delink_reference_from_batch()
		self.clear_table()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
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


@frappe.whitelist()
def get_serial_batch_ledgers(item_code, voucher_no, name=None):
	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=[
			"`tabSerial and Batch Ledger`.`name`",
			"`tabSerial and Batch Ledger`.`qty`",
			"`tabSerial and Batch Ledger`.`warehouse`",
			"`tabSerial and Batch Ledger`.`batch_no`",
			"`tabSerial and Batch Ledger`.`serial_no`",
		],
		filters=[
			["Serial and Batch Bundle", "item_code", "=", item_code],
			["Serial and Batch Ledger", "parent", "=", name],
			["Serial and Batch Bundle", "voucher_no", "=", voucher_no],
			["Serial and Batch Bundle", "docstatus", "!=", 2],
		],
	)


@frappe.whitelist()
def add_serial_batch_ledgers(ledgers, child_row) -> object:
	if isinstance(child_row, str):
		child_row = frappe._dict(frappe.parse_json(child_row))

	if isinstance(ledgers, str):
		ledgers = frappe.parse_json(ledgers)

	if frappe.db.exists("Serial and Batch Bundle", child_row.serial_and_batch_bundle):
		doc = update_serial_batch_no_ledgers(ledgers, child_row)
	else:
		doc = create_serial_batch_no_ledgers(ledgers, child_row)

	return doc


def create_serial_batch_no_ledgers(ledgers, child_row) -> object:
	doc = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": child_row.parenttype,
			"voucher_no": child_row.parent,
			"item_code": child_row.item_code,
			"voucher_detail_no": child_row.name,
		}
	)

	for row in ledgers:
		row = frappe._dict(row)
		doc.append(
			"ledgers",
			{
				"qty": row.qty or 1.0,
				"warehouse": child_row.warehouse,
				"batch_no": row.batch_no,
				"serial_no": row.serial_no,
			},
		)

	doc.save()

	frappe.db.set_value(child_row.doctype, child_row.name, "serial_and_batch_bundle", doc.name)

	frappe.msgprint(_("Serial and Batch Bundle created"), alert=True)

	return doc


def update_serial_batch_no_ledgers(ledgers, child_row) -> object:
	doc = frappe.get_doc("Serial and Batch Bundle", child_row.serial_and_batch_bundle)
	doc.voucher_detail_no = child_row.name
	doc.set("ledgers", [])
	doc.set("ledgers", ledgers)
	doc.save()

	frappe.msgprint(_("Serial and Batch Bundle updated"), alert=True)

	return doc


def get_serial_and_batch_ledger(**kwargs):
	kwargs = frappe._dict(kwargs)

	sle_table = frappe.qb.DocType("Stock Ledger Entry")
	serial_batch_table = frappe.qb.DocType("Serial and Batch Ledger")

	query = (
		frappe.qb.from_(sle_table)
		.inner_join(serial_batch_table)
		.on(sle_table.serial_and_batch_bundle == serial_batch_table.parent)
		.select(
			serial_batch_table.serial_no,
			serial_batch_table.warehouse,
			serial_batch_table.batch_no,
			serial_batch_table.qty,
			serial_batch_table.incoming_rate,
		)
		.where((sle_table.item_code == kwargs.item_code) & (sle_table.warehouse == kwargs.warehouse))
	)

	if kwargs.serial_nos:
		query = query.where(serial_batch_table.serial_no.isin(kwargs.serial_nos))

	if kwargs.batch_nos:
		query = query.where(serial_batch_table.batch_no.isin(kwargs.batch_nos))

	if kwargs.fetch_incoming_rate:
		query = query.where(sle_table.actual_qty > 0)

	return query.run(as_dict=True)


def get_copy_of_serial_and_batch_bundle(serial_and_batch_bundle, warehouse):
	bundle_doc = frappe.copy_doc(serial_and_batch_bundle)
	for row in bundle_doc.ledgers:
		row.warehouse = warehouse
		row.incoming_rate = row.outgoing_rate
		row.outgoing_rate = 0.0

	return bundle_doc.submit(ignore_permissions=True)


@frappe.whitelist()
def get_auto_data(**kwargs):
	kwargs = frappe._dict(kwargs)

	if cint(kwargs.has_serial_no):
		return get_auto_serial_nos(kwargs)

	elif cint(kwargs.has_batch_no):
		return get_auto_batch_nos(kwargs)


def get_auto_serial_nos(kwargs):
	fields = ["name as serial_no"]
	if kwargs.has_batch_no:
		fields.append("batch_no")

	order_by = "creation"
	if kwargs.based_on == "LIFO":
		order_by = "creation desc"
	elif kwargs.based_on == "Expiry":
		order_by = "amc_expiry_date asc"

	return frappe.get_all(
		"Serial No",
		fields=fields,
		filters={"item_code": kwargs.item_code, "warehouse": kwargs.warehouse},
		limit=cint(kwargs.qty),
		order_by=order_by,
	)


def get_auto_batch_nos(kwargs):
	available_batches = get_available_batches(kwargs)

	qty = flt(kwargs.qty)

	batches = []

	for batch in available_batches:
		if qty > 0:
			batch_qty = flt(batch.qty)
			if qty > batch_qty:
				batches.append(
					{
						"batch_no": batch.batch_no,
						"qty": batch_qty,
					}
				)
				qty -= batch_qty
			else:
				batches.append(
					{
						"batch_no": batch.batch_no,
						"qty": qty,
					}
				)
				qty = 0

	return batches


def get_available_batches(kwargs):
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_ledger = frappe.qb.DocType("Serial and Batch Ledger")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.inner_join(batch_ledger)
		.on(stock_ledger_entry.serial_and_batch_bundle == batch_ledger.parent)
		.inner_join(batch_table)
		.on(batch_ledger.batch_no == batch_table.name)
		.select(
			batch_ledger.batch_no,
			Sum(
				Case().when(stock_ledger_entry.actual_qty > 0, batch_ledger.qty).else_(batch_ledger.qty * -1)
			).as_("qty"),
		)
		.where(
			(stock_ledger_entry.item_code == kwargs.item_code)
			& (stock_ledger_entry.warehouse == kwargs.warehouse)
			& ((batch_table.expiry_date >= today()) | (batch_table.expiry_date.isnull()))
		)
		.groupby(batch_ledger.batch_no)
	)

	if kwargs.based_on == "LIFO":
		query = query.orderby(batch_table.creation, order=frappe.qb.desc)
	elif kwargs.based_on == "Expiry":
		query = query.orderby(batch_table.expiry_date)
	else:
		query = query.orderby(batch_table.creation)

	data = query.run(as_dict=True)
	data = list(filter(lambda x: x.qty > 0, data))

	return data
