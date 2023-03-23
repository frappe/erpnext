# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import collections
from collections import defaultdict
from typing import Dict, List

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import add_days, cint, flt, get_link_to_form, today
from pypika import Case

from erpnext.stock.serial_batch_bundle import BatchNoValuation, SerialNoValuation


class SerialNoExistsInFutureTransactionError(frappe.ValidationError):
	pass


class SerialandBatchBundle(Document):
	def validate(self):
		self.validate_serial_and_batch_no()
		self.validate_duplicate_serial_and_batch_no()
		self.validate_voucher_no()

	def before_save(self):
		if self.type_of_transaction == "Maintenance":
			return

		self.check_future_entries_exists()
		self.validate_serial_nos_inventory()
		self.set_is_outward()
		self.validate_qty_and_stock_value_difference()
		self.calculate_qty_and_amount()
		self.set_warehouse()
		self.set_incoming_rate()

	def validate_serial_nos_inventory(self):
		if not (self.has_serial_no and self.type_of_transaction == "Outward"):
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		serial_no_warehouse = frappe._dict(
			frappe.get_all(
				"Serial No",
				filters={"name": ("in", serial_nos)},
				fields=["name", "warehouse"],
				as_list=1,
			)
		)

		for serial_no in serial_nos:
			if (
				not serial_no_warehouse.get(serial_no) or serial_no_warehouse.get(serial_no) != self.warehouse
			):
				frappe.throw(
					_(f"Serial No {bold(serial_no)} is not present in the warehouse {bold(self.warehouse)}.")
				)

	def set_incoming_rate(self, row=None, save=False):
		if self.type_of_transaction == "Outward":
			self.set_incoming_rate_for_outward_transaction(row, save)
		else:
			self.set_incoming_rate_for_inward_transaction(row, save)

	def validate_qty_and_stock_value_difference(self):
		if self.type_of_transaction != "Outward":
			return

		for d in self.entries:
			if d.qty and d.qty > 0:
				d.qty *= -1

			if d.stock_value_difference and d.stock_value_difference > 0:
				d.stock_value_difference *= -1

	def get_serial_nos(self):
		return [d.serial_no for d in self.entries if d.serial_no]

	def set_incoming_rate_for_outward_transaction(self, row=None, save=False):
		sle = self.get_sle_for_outward_transaction(row)
		if self.has_serial_no:
			sn_obj = SerialNoValuation(
				sle=sle,
				warehouse=self.item_code,
				item_code=self.warehouse,
			)

		else:
			sn_obj = BatchNoValuation(
				sle=sle,
				warehouse=self.item_code,
				item_code=self.warehouse,
			)

		for d in self.entries:
			available_qty = 0
			if self.has_serial_no:
				d.incoming_rate = abs(sn_obj.serial_no_incoming_rate.get(d.serial_no, 0.0))
			else:
				d.incoming_rate = abs(sn_obj.batch_avg_rate.get(d.batch_no))
				available_qty = flt(sn_obj.available_qty.get(d.batch_no)) + flt(d.qty)

				self.validate_negative_batch(d.batch_no, available_qty)

			if self.has_batch_no:
				d.stock_value_difference = flt(d.qty) * flt(d.incoming_rate)

			if save:
				d.db_set(
					{"incoming_rate": d.incoming_rate, "stock_value_difference": d.stock_value_difference}
				)

	def validate_negative_batch(self, batch_no, available_qty):
		if available_qty < 0:
			msg = f"""Batch No {bold(batch_no)} has negative stock
				of quantity {bold(available_qty)} in the
				warehouse {self.warehouse}"""

			frappe.throw(_(msg))

	def get_sle_for_outward_transaction(self, row):
		return frappe._dict(
			{
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"serial_and_batch_bundle": self.name,
				"actual_qty": self.total_qty,
				"company": self.company,
				"serial_nos": [row.serial_no for row in self.entries if row.serial_no],
				"batch_nos": {row.batch_no: row for row in self.entries if row.batch_no},
			}
		)

	def set_incoming_rate_for_inward_transaction(self, row=None, save=False):
		valuation_field = "valuation_rate"
		if self.voucher_type in ["Sales Invoice", "Delivery Note"]:
			valuation_field = "incoming_rate"

		rate = row.get(valuation_field) if row else 0.0
		precision = frappe.get_precision(self.child_table, valuation_field) or 2

		if not rate and self.voucher_detail_no and self.voucher_no:
			rate = frappe.db.get_value(self.child_table, self.voucher_detail_no, valuation_field)

		for d in self.entries:
			if self.voucher_type in ["Stock Reconciliation", "Stock Entry"] and d.incoming_rate:
				continue

			if not rate or flt(rate, precision) == flt(d.incoming_rate, precision):
				continue

			d.incoming_rate = flt(rate, precision)
			if self.has_batch_no:
				d.stock_value_difference = flt(d.qty) * flt(d.incoming_rate)

			if save:
				d.db_set(
					{"incoming_rate": d.incoming_rate, "stock_value_difference": d.stock_value_difference}
				)

	def set_serial_and_batch_values(self, parent, row):
		values_to_set = {}
		if not self.voucher_no or self.voucher_no != row.parent:
			values_to_set["voucher_no"] = row.parent

		if not self.voucher_detail_no or self.voucher_detail_no != row.name:
			values_to_set["voucher_detail_no"] = row.name

		if parent.get("posting_date") and (
			not self.posting_date or self.posting_date != parent.posting_date
		):
			values_to_set["posting_date"] = parent.posting_date

		if parent.get("posting_time") and (
			not self.posting_time or self.posting_time != parent.posting_time
		):
			values_to_set["posting_time"] = parent.posting_time

		if values_to_set:
			self.db_set(values_to_set)

		# self.validate_voucher_no()
		self.set_incoming_rate(save=True, row=row)
		self.calculate_qty_and_amount(save=True)
		self.validate_quantity(row)
		self.set_warranty_expiry_date()

	def set_warranty_expiry_date(self):
		if self.type_of_transaction != "Outward":
			return

		if not (self.docstatus == 1 and self.voucher_type == "Delivery Note" and self.has_serial_no):
			return

		warranty_period = frappe.get_cached_value("Item", self.item_code, "warranty_period")

		if not warranty_period:
			return

		warranty_expiry_date = add_days(self.posting_date, cint(warranty_period))

		serial_nos = self.get_serial_nos()
		if not serial_nos:
			return

		sn_table = frappe.qb.DocType("Serial No")
		(
			frappe.qb.update(sn_table)
			.set(sn_table.warranty_expiry_date, warranty_expiry_date)
			.where(sn_table.name.isin(serial_nos))
		).run()

	def validate_voucher_no(self):
		if not (self.voucher_type and self.voucher_no):
			return

		if self.voucher_no and not frappe.db.exists(self.voucher_type, self.voucher_no):
			frappe.throw(_(f"The {self.voucher_type} # {self.voucher_no} does not exist"))

	def check_future_entries_exists(self):
		if not self.has_serial_no:
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]

		if not serial_nos:
			return

		parent = frappe.qb.DocType("Serial and Batch Bundle")
		child = frappe.qb.DocType("Serial and Batch Entry")

		timestamp_condition = CombineDatetime(
			parent.posting_date, parent.posting_time
		) > CombineDatetime(self.posting_date, self.posting_time)

		future_entries = (
			frappe.qb.from_(parent)
			.inner_join(child)
			.on(parent.name == child.parent)
			.select(
				child.serial_no,
				parent.voucher_type,
				parent.voucher_no,
			)
			.where(
				(child.serial_no.isin(serial_nos))
				& (child.parent != self.name)
				& (parent.item_code == self.item_code)
				& (parent.docstatus == 1)
				& (parent.is_cancelled == 0)
			)
			.where(timestamp_condition)
		).run(as_dict=True)

		if future_entries:
			msg = """The serial nos has been used in the future
				transactions so you need to cancel them first.
				The list of serial nos and their respective
				transactions are as below."""

			msg += "<br><br><ul>"

			for d in future_entries:
				msg += f"<li>{d.serial_no} in {get_link_to_form(d.voucher_type, d.voucher_no)}</li>"
			msg += "</li></ul>"

			title = "Serial No Exists In Future Transaction(s)"

			frappe.throw(_(msg), title=_(title), exc=SerialNoExistsInFutureTransactionError)

	def validate_quantity(self, row):
		precision = row.precision
		qty_field = "qty"
		if self.voucher_type in ["Subcontracting Receipt"]:
			qty_field = "consumed_qty"

		if abs(flt(self.total_qty, precision)) - abs(flt(row.get(qty_field), precision)) > 0.01:
			frappe.throw(
				_(
					f"Total quantity {self.total_qty} in the Serial and Batch Bundle {self.name} does not match with the Item {self.item_code} in the {self.voucher_type} # {self.voucher_no}"
				)
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
			rate = flt(row.incoming_rate) or flt(row.outgoing_rate)
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

	def calculate_outgoing_rate(self):
		if not (self.has_serial_no and self.entries):
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

		for row in self.entries:
			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no and not row.serial_no:
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
		self.set("entries", [])

	@property
	def child_table(self):
		table = f"{self.voucher_type} Item"
		if self.voucher_type == "Stock Entry":
			table = f"{self.voucher_type} Detail"

		return table

	def delink_refernce_from_voucher(self):
		vouchers = frappe.get_all(
			self.child_table,
			fields=["name"],
			filters={"serial_and_batch_bundle": self.name, "docstatus": 0},
		)

		for voucher in vouchers:
			frappe.db.set_value(self.child_table, voucher.name, "serial_and_batch_bundle", None)

	def delink_reference_from_batch(self):
		batches = frappe.get_all(
			"Batch",
			fields=["name"],
			filters={"reference_name": self.name, "reference_doctype": "Serial and Batch Bundle"},
		)

		for batch in batches:
			frappe.db.set_value("Batch", batch.name, {"reference_name": None, "reference_doctype": None})

	def on_cancel(self):
		self.validate_voucher_no_docstatus()

	def validate_voucher_no_docstatus(self):
		if frappe.db.get_value(self.voucher_type, self.voucher_no, "docstatus") == 1:
			msg = f"""The {self.voucher_type} {bold(self.voucher_no)}
				is in submitted state, please cancel it first"""
			frappe.throw(_(msg))

	def on_trash(self):
		self.validate_voucher_no_docstatus()
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
def get_serial_batch_ledgers(item_code, docstatus=None, voucher_no=None, name=None):
	filters = get_filters_for_bundle(item_code, docstatus=docstatus, voucher_no=voucher_no, name=name)

	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=[
			"`tabSerial and Batch Bundle`.`name`",
			"`tabSerial and Batch Entry`.`qty`",
			"`tabSerial and Batch Entry`.`warehouse`",
			"`tabSerial and Batch Entry`.`batch_no`",
			"`tabSerial and Batch Entry`.`serial_no`",
		],
		filters=filters,
	)


def get_filters_for_bundle(item_code, docstatus=None, voucher_no=None, name=None):
	filters = [
		["Serial and Batch Bundle", "item_code", "=", item_code],
		["Serial and Batch Bundle", "is_cancelled", "=", 0],
	]

	if not docstatus:
		docstatus = [0, 1]

	if isinstance(docstatus, list):
		filters.append(["Serial and Batch Bundle", "docstatus", "in", docstatus])
	else:
		filters.append(["Serial and Batch Bundle", "docstatus", "=", docstatus])

	if voucher_no:
		filters.append(["Serial and Batch Bundle", "voucher_no", "=", voucher_no])

	if name:
		if isinstance(name, list):
			filters.append(["Serial and Batch Entry", "parent", "in", name])
		else:
			filters.append(["Serial and Batch Entry", "parent", "=", name])

	return filters


@frappe.whitelist()
def add_serial_batch_ledgers(entries, child_row, doc) -> object:
	if isinstance(child_row, str):
		child_row = frappe._dict(frappe.parse_json(child_row))

	if isinstance(entries, str):
		entries = frappe.parse_json(entries)

	if doc and isinstance(doc, str):
		parent_doc = frappe.parse_json(doc)

	if frappe.db.exists("Serial and Batch Bundle", child_row.serial_and_batch_bundle):
		doc = update_serial_batch_no_ledgers(entries, child_row, parent_doc)
	else:
		doc = create_serial_batch_no_ledgers(entries, child_row, parent_doc)

	return doc


def create_serial_batch_no_ledgers(entries, child_row, parent_doc) -> object:

	warehouse = child_row.rejected_warhouse if child_row.is_rejected else child_row.warehouse

	type_of_transaction = child_row.type_of_transaction
	if parent_doc.get("doctype") == "Stock Entry":
		type_of_transaction = "Outward" if child_row.s_warehouse else "Inward"
		warehouse = child_row.s_warehouse or child_row.t_warehouse

	doc = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": child_row.parenttype,
			"item_code": child_row.item_code,
			"warehouse": warehouse,
			"is_rejected": child_row.is_rejected,
			"type_of_transaction": type_of_transaction,
			"posting_date": parent_doc.get("posting_date"),
			"posting_time": parent_doc.get("posting_time"),
		}
	)

	for row in entries:
		row = frappe._dict(row)
		doc.append(
			"entries",
			{
				"qty": (row.qty or 1.0) * (1 if type_of_transaction == "Inward" else -1),
				"warehouse": warehouse,
				"batch_no": row.batch_no,
				"serial_no": row.serial_no,
			},
		)

	doc.save()

	frappe.db.set_value(child_row.doctype, child_row.name, "serial_and_batch_bundle", doc.name)

	frappe.msgprint(_("Serial and Batch Bundle created"), alert=True)

	return doc


def update_serial_batch_no_ledgers(entries, child_row, parent_doc) -> object:
	doc = frappe.get_doc("Serial and Batch Bundle", child_row.serial_and_batch_bundle)
	doc.voucher_detail_no = child_row.name
	doc.posting_date = parent_doc.posting_date
	doc.posting_time = parent_doc.posting_time
	doc.set("entries", [])

	for d in entries:
		doc.append(
			"entries",
			{
				"qty": 1 if doc.type_of_transaction == "Inward" else -1,
				"warehouse": d.get("warehouse"),
				"batch_no": d.get("batch_no"),
				"serial_no": d.get("serial_no"),
			},
		)

	doc.save(ignore_permissions=True)

	frappe.msgprint(_("Serial and Batch Bundle updated"), alert=True)

	return doc


def get_serial_and_batch_ledger(**kwargs):
	kwargs = frappe._dict(kwargs)

	sle_table = frappe.qb.DocType("Stock Ledger Entry")
	serial_batch_table = frappe.qb.DocType("Serial and Batch Entry")

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
			serial_batch_table.voucher_detail_no,
		)
		.where(
			(sle_table.item_code == kwargs.item_code)
			& (sle_table.warehouse == kwargs.warehouse)
			& (serial_batch_table.is_outward == 0)
		)
	)

	if kwargs.serial_nos:
		query = query.where(serial_batch_table.serial_no.isin(kwargs.serial_nos))

	if kwargs.batch_nos:
		query = query.where(serial_batch_table.batch_no.isin(kwargs.batch_nos))

	if kwargs.fetch_incoming_rate:
		query = query.where(sle_table.actual_qty > 0)

	return query.run(as_dict=True)


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

	ignore_serial_nos = get_reserved_serial_nos_for_pos(kwargs)

	return frappe.get_all(
		"Serial No",
		fields=fields,
		filters={
			"item_code": kwargs.item_code,
			"warehouse": kwargs.warehouse,
			"name": ("not in", ignore_serial_nos),
		},
		limit=cint(kwargs.qty),
		order_by=order_by,
	)


def get_reserved_serial_nos_for_pos(kwargs):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	ignore_serial_nos = []
	pos_invoices = frappe.get_all(
		"POS Invoice",
		fields=["`tabPOS Invoice Item`.serial_no", "`tabPOS Invoice Item`.serial_and_batch_bundle"],
		filters=[
			["POS Invoice", "consolidated_invoice", "is", "not set"],
			["POS Invoice", "docstatus", "=", 1],
			["POS Invoice Item", "item_code", "=", kwargs.item_code],
		],
	)

	ids = [
		pos_invoice.serial_and_batch_bundle
		for pos_invoice in pos_invoices
		if pos_invoice.serial_and_batch_bundle
	]

	for d in get_serial_batch_ledgers(ids, docstatus=1, name=ids):
		ignore_serial_nos.append(d.serial_no)

	# Will be deprecated in v16
	for pos_invoice in pos_invoices:
		if pos_invoice.serial_no:
			ignore_serial_nos.extend(get_serial_nos(pos_invoice.serial_no))

	return ignore_serial_nos


def get_auto_batch_nos(kwargs):
	available_batches = get_available_batches(kwargs)

	qty = flt(kwargs.qty)

	batches = []

	reserved_batches = get_reserved_batches_for_pos(kwargs)
	if reserved_batches:
		remove_batches_reserved_for_pos(available_batches, reserved_batches)

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


def get_reserved_batches_for_pos(kwargs):
	reserved_batches = defaultdict(float)

	pos_invoices = frappe.get_all(
		"POS Invoice",
		fields=[
			"`tabPOS Invoice Item`.batch_no",
			"`tabPOS Invoice Item`.qty",
			"`tabPOS Invoice Item`.serial_and_batch_bundle",
		],
		filters=[
			["POS Invoice", "consolidated_invoice", "is", "not set"],
			["POS Invoice", "docstatus", "=", 1],
			["POS Invoice Item", "item_code", "=", kwargs.item_code],
		],
	)

	ids = [
		pos_invoice.serial_and_batch_bundle
		for pos_invoice in pos_invoices
		if pos_invoice.serial_and_batch_bundle
	]

	for d in get_serial_batch_ledgers(ids, docstatus=1, name=ids):
		if not d.batch_no:
			continue

		reserved_batches[d.batch_no] += flt(d.qty)

	# Will be deprecated in v16
	for pos_invoice in pos_invoices:
		if not pos_invoice.batch_no:
			continue

		reserved_batches[pos_invoice.batch_no] += flt(pos_invoice.qty)

	return reserved_batches


def remove_batches_reserved_for_pos(available_batches, reserved_batches):
	for batch in available_batches:
		if batch.batch_no in reserved_batches:
			available_batches[batch.batch_no] -= reserved_batches[batch.batch_no]


def get_available_batches(kwargs):
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_ledger = frappe.qb.DocType("Serial and Batch Entry")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.inner_join(batch_ledger)
		.on(stock_ledger_entry.serial_and_batch_bundle == batch_ledger.parent)
		.inner_join(batch_table)
		.on(batch_ledger.batch_no == batch_table.name)
		.select(
			batch_ledger.batch_no,
			Sum(batch_ledger.qty).as_("qty"),
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


def get_voucher_wise_serial_batch_from_bundle(**kwargs) -> Dict[str, Dict]:
	data = get_ledgers_from_serial_batch_bundle(**kwargs)
	if not data:
		return {}

	group_by_voucher = {}

	for row in data:
		key = (row.item_code, row.warehouse, row.voucher_no)
		if kwargs.get("get_subcontracted_item"):
			# get_subcontracted_item = ("doctype", "field_name")
			doctype, field_name = kwargs.get("get_subcontracted_item")

			subcontracted_item_code = frappe.get_cached_value(doctype, row.voucher_detail_no, field_name)
			key = (row.item_code, subcontracted_item_code, row.warehouse, row.voucher_no)

		if key not in group_by_voucher:
			group_by_voucher.setdefault(
				key,
				frappe._dict({"serial_nos": [], "batch_nos": defaultdict(float), "item_row": row}),
			)

		child_row = group_by_voucher[key]
		if row.serial_no:
			child_row["serial_nos"].append(row.serial_no)

		if row.batch_no:
			child_row["batch_nos"][row.batch_no] += row.qty

	return group_by_voucher


def get_ledgers_from_serial_batch_bundle(**kwargs) -> List[frappe._dict]:
	bundle_table = frappe.qb.DocType("Serial and Batch Bundle")
	serial_batch_table = frappe.qb.DocType("Serial and Batch Entry")

	query = (
		frappe.qb.from_(bundle_table)
		.inner_join(serial_batch_table)
		.on(bundle_table.name == serial_batch_table.parent)
		.select(
			serial_batch_table.serial_no,
			bundle_table.warehouse,
			bundle_table.item_code,
			serial_batch_table.batch_no,
			serial_batch_table.qty,
			serial_batch_table.incoming_rate,
			bundle_table.voucher_detail_no,
			bundle_table.voucher_no,
			bundle_table.posting_date,
			bundle_table.posting_time,
		)
		.where((bundle_table.docstatus == 1) & (bundle_table.is_cancelled == 0))
	)

	for key, val in kwargs.items():
		if key in ["get_subcontracted_item"]:
			continue

		if key in ["name", "item_code", "warehouse", "voucher_no", "company", "voucher_detail_no"]:
			if isinstance(val, list):
				query = query.where(bundle_table[key].isin(val))
			else:
				query = query.where(bundle_table[key] == val)
		elif key in ["posting_date", "posting_time"]:
			query = query.where(bundle_table[key] >= val)
		else:
			if isinstance(val, list):
				query = query.where(serial_batch_table[key].isin(val))
			else:
				query = query.where(serial_batch_table[key] == val)

	return query.run(as_dict=True)


def get_available_serial_nos(item_code, warehouse):
	filters = {
		"item_code": item_code,
		"warehouse": ("is", "set"),
	}

	fields = ["name as serial_no", "warehouse", "batch_no"]

	if warehouse:
		filters["warehouse"] = warehouse

	return frappe.get_all("Serial No", filters=filters, fields=fields)


def get_available_batch_nos(item_code, warehouse):
	sl_entries = get_stock_ledger_entries(item_code, warehouse)
	batchwise_qty = defaultdict(float)

	precision = frappe.get_precision("Stock Ledger Entry", "qty")
	for entry in sl_entries:
		batchwise_qty[entry.batch_no] += flt(entry.qty, precision)

	return batchwise_qty


def get_stock_ledger_entries(item_code, warehouse):
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_ledger = frappe.qb.DocType("Serial and Batch Entry")

	return (
		frappe.qb.from_(stock_ledger_entry)
		.left_join(batch_ledger)
		.on(stock_ledger_entry.serial_and_batch_bundle == batch_ledger.parent)
		.select(
			stock_ledger_entry.warehouse,
			stock_ledger_entry.item_code,
			Sum(
				Case()
				.when(stock_ledger_entry.serial_and_batch_bundle, batch_ledger.qty)
				.else_(stock_ledger_entry.actual_qty)
				.as_("qty")
			),
			Case()
			.when(stock_ledger_entry.serial_and_batch_bundle, batch_ledger.batch_no)
			.else_(stock_ledger_entry.batch_no)
			.as_("batch_no"),
		)
		.where(
			(stock_ledger_entry.item_code == item_code)
			& (stock_ledger_entry.warehouse == warehouse)
			& (stock_ledger_entry.is_cancelled == 0)
		)
	).run(as_dict=True)
