from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, nowdate

from erpnext.manufacturing.doctype.bom.bom import get_backflush_based_on
from erpnext.stock.serial_batch_bundle import SerialBatchCreation, get_serial_or_batch_items
from erpnext.stock.utils import get_combine_datetime

from .base import BaseStockEntry


class StockEntrySABB(BaseStockEntry):
	def make_serial_and_batch_bundle_for_outward(self):
		serial_or_batch_items = get_serial_or_batch_items(self.doc.items)
		if not serial_or_batch_items:
			return

		serial_nos, batch_nos = self.get_serial_batch_fields_for_subcontracting_inward()
		already_picked_serial_nos = []

		for row in self.doc.items:
			if row.use_serial_batch_fields or not row.s_warehouse:
				continue
			if row.item_code not in serial_or_batch_items:
				continue

			bundle_doc = self._create_or_update_bundle_for_row(
				row, serial_nos, batch_nos, already_picked_serial_nos
			)
			if not bundle_doc:
				continue

			for entry in bundle_doc.entries:
				if entry.serial_no:
					already_picked_serial_nos.append(entry.serial_no)

			row.serial_and_batch_bundle = bundle_doc.name

	def _create_or_update_bundle_for_row(self, row, serial_nos, batch_nos, already_picked_serial_nos):
		if row.serial_and_batch_bundle and abs(row.transfer_qty) != abs(
			frappe.get_cached_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "total_qty")
		):
			return SerialBatchCreation(
				{
					"item_code": row.item_code,
					"warehouse": row.s_warehouse,
					"serial_and_batch_bundle": row.serial_and_batch_bundle,
					"type_of_transaction": "Outward",
					"ignore_serial_nos": already_picked_serial_nos,
					"qty": row.transfer_qty * -1,
				}
			).update_serial_and_batch_entries(
				serial_nos=serial_nos.get(row.name), batch_nos=batch_nos.get(row.name)
			)

		if not row.serial_and_batch_bundle and frappe.get_single_value(
			"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward"
		):
			return SerialBatchCreation(
				{
					"item_code": row.item_code,
					"warehouse": row.s_warehouse,
					"posting_datetime": get_combine_datetime(self.doc.posting_date, self.doc.posting_time),
					"voucher_type": self.doc.doctype,
					"voucher_detail_no": row.name,
					"qty": row.transfer_qty * -1,
					"ignore_serial_nos": already_picked_serial_nos,
					"type_of_transaction": "Outward",
					"company": self.doc.company,
					"do_not_submit": True,
				}
			).make_serial_and_batch_bundle(
				serial_nos=serial_nos.get(row.name), batch_nos=batch_nos.get(row.name)
			)

		return None

	def get_serial_nos_and_batches_from_sres(self, scio_detail, only_pending=True):
		serial_nos, batch_nos = [], frappe._dict()

		table = frappe.qb.DocType("Stock Reservation Entry")
		child_table = frappe.qb.DocType("Serial and Batch Entry")
		query = (
			frappe.qb.from_(table)
			.join(child_table)
			.on(table.name == child_table.parent)
			.select(child_table.serial_no, child_table.batch_no, child_table.qty)
			.where((table.docstatus == 1) & (table.voucher_detail_no == scio_detail))
		)

		if only_pending:
			query = query.where(child_table.qty != child_table.delivered_qty)
		else:
			query = query.where(child_table.delivered_qty > 0)

		for d in query.run(as_dict=True):
			if d.serial_no and d.serial_no not in serial_nos:
				serial_nos.append(d.serial_no)
			if d.batch_no and d.batch_no not in batch_nos:
				batch_nos[d.batch_no] = d.qty

		return serial_nos, batch_nos

	def get_serial_batch_fields_for_subcontracting_inward(self):
		serial_nos, batch_nos = frappe._dict(), frappe._dict()
		for row in self.doc.items:
			if self.doc.purpose in [
				"Return Raw Material to Customer",
				"Subcontracting Delivery",
				"Subcontracting Return",
			]:
				if not row.serial_and_batch_bundle:
					serial_nos_list, batch_nos_list = self.get_serial_nos_and_batches_from_sres(
						row.scio_detail, only_pending=self.doc.purpose != "Subcontracting Return"
					)

					if len(batch_nos_list) > 1:
						row.use_serial_batch_fields = 0

					if row.use_serial_batch_fields:
						if serial_nos_list and not row.serial_no:
							row.serial_no = "\n".join(serial_nos_list)
						if batch_nos_list and not row.batch_no:
							row.batch_no = next(iter(batch_nos_list.keys()))

					serial_nos[row.name], batch_nos[row.name] = serial_nos_list, batch_nos_list

		return serial_nos, batch_nos

	def get_available_reserved_materials(self):
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_reserved_materials,
		)

		voucher_no = self.doc.work_order or self.doc.subcontracting_order
		reserved_entries = get_reserved_materials(voucher_no)
		if not reserved_entries:
			return {}

		itemwise_serial_batch_qty = frappe._dict()

		for d in reserved_entries:
			key = (d.item_code, d.warehouse)
			if key not in itemwise_serial_batch_qty:
				itemwise_serial_batch_qty[key] = frappe._dict(
					{
						"serial_no": [],
						"batch_no": defaultdict(float),
						"batchwise_sn": defaultdict(list),
					}
				)

			details = itemwise_serial_batch_qty[key]
			if d.batch_no:
				details.batch_no[d.batch_no] += d.qty
				if d.serial_no:
					details.batchwise_sn[d.batch_no].extend(d.serial_no.split("\n"))
			elif d.serial_no:
				details.serial_no.append(d.serial_no)

		return itemwise_serial_batch_qty

	def set_serial_batch_based_on_reservation(self):
		if self.doc.work_order and frappe.get_cached_value(
			"Work Order", self.doc.work_order, "reserve_stock"
		):
			skip_transfer = frappe.get_cached_value("Work Order", self.doc.work_order, "skip_transfer")
			backflush_based_on = get_backflush_based_on(self.doc.bom_no)

			if (
				self.doc.purpose not in ["Material Transfer for Manufacture"]
				and backflush_based_on != "BOM"
				and not skip_transfer
			):
				return

		reservation_entries = self.get_available_reserved_materials()
		if not reservation_entries:
			return

		new_items_to_add = []
		for d in self.doc.items:
			if d.serial_and_batch_bundle or d.serial_no or d.batch_no:
				continue

			key = (d.item_code, d.s_warehouse)
			if details := reservation_entries.get(key):
				self._apply_batch_reservation_to_item(d, details, new_items_to_add)
				d.use_serial_batch_fields = 1

		for new_row in new_items_to_add:
			self.doc.append("items", new_row)

		self._sort_and_reindex_items()

	def _apply_batch_reservation_to_item(self, d, details, new_items_to_add):
		original_qty = d.qty
		if batches := details.get("batch_no"):
			original_qty = self._distribute_batches_to_item(
				d, batches, details, new_items_to_add, original_qty
			)
		if details.get("serial_no"):
			d.serial_no = "\n".join(details.get("serial_no")[: cint(d.qty)])

	def _distribute_batches_to_item(self, d, batches, details, new_items_to_add, original_qty):
		for batch_no, qty in batches.items():
			if original_qty <= 0:
				break
			if qty <= 0:
				continue
			if d.batch_no:
				original_qty, _ = self._make_overflow_batch_row(
					d, batches, details, new_items_to_add, batch_no, qty, original_qty
				)
			else:
				self._assign_batch_to_item(d, batches, details, batch_no, qty)
		return original_qty

	def _make_overflow_batch_row(self, d, batches, details, new_items_to_add, batch_no, qty, original_qty):
		new_row = frappe.copy_doc(d)
		new_row.name = None
		new_row.batch_no = batch_no
		new_row.qty = qty
		new_row.idx = d.idx + 1
		if new_row.batch_no and details.get("batchwise_sn"):
			new_row.serial_no = "\n".join(details.get("batchwise_sn")[new_row.batch_no][: cint(new_row.qty)])
		new_items_to_add.append(new_row)
		batches[batch_no] -= qty
		return original_qty - qty, new_row

	def _assign_batch_to_item(self, d, batches, details, batch_no, qty):
		if qty >= d.qty:
			d.batch_no = batch_no
			batches[batch_no] -= d.qty
		else:
			d.batch_no = batch_no
			d.qty = qty
			batches[batch_no] = 0
		if d.batch_no and details.get("batchwise_sn"):
			d.serial_no = "\n".join(details.get("batchwise_sn")[d.batch_no][: cint(d.qty)])

	def _sort_and_reindex_items(self):
		sorted_items = sorted(self.doc.items, key=lambda x: x.item_code)
		if self.doc.purpose == "Manufacture":
			# ensure finished item at last
			sorted_items = sorted(sorted_items, key=lambda x: cstr(x.t_warehouse))

		for idx, row in enumerate(sorted_items, start=1):
			row.idx = idx

		self.doc.set("items", sorted_items)


def create_serial_and_batch_bundle(parent_doc, row, child, type_of_transaction=None):
	item_details = frappe.get_cached_value(
		"Item", child.item_code, ["has_serial_no", "has_batch_no"], as_dict=1
	)
	if not (item_details.has_serial_no or item_details.has_batch_no):
		return
	doc = _make_bundle_doc(parent_doc, child, type_of_transaction or "Inward")
	_populate_bundle_entries(doc, row, child)
	if not doc.entries:
		return None
	return doc.insert(ignore_permissions=True).name


def _make_bundle_doc(parent_doc, child, type_of_transaction):
	return frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": "Stock Entry",
			"item_code": child.item_code,
			"warehouse": child.warehouse,
			"type_of_transaction": type_of_transaction,
			"posting_date": parent_doc.posting_date,
			"posting_time": parent_doc.posting_time,
		}
	)


def _populate_bundle_entries(doc, row, child):
	precision = frappe.get_precision("Stock Entry Detail", "qty")
	if row.serial_nos and row.batches_to_be_consume:
		_append_serial_batch_entries(doc, row, child, precision)
	elif row.serial_nos:
		doc.has_serial_no = 1
		for serial_no in row.serial_nos:
			doc.append("entries", {"serial_no": serial_no, "warehouse": row.warehouse, "qty": -1})
	elif row.batches_to_be_consume:
		_append_batch_entries(doc, row)


def _append_serial_batch_entries(doc, row, child, precision):
	doc.has_serial_no = 1
	doc.has_batch_no = 1
	batchwise_serial_nos = get_batchwise_serial_nos(child.item_code, row)
	for batch_no, qty in row.batches_to_be_consume.items():
		while flt(qty, precision) > 0:
			qty -= 1
			doc.append(
				"entries",
				{
					"batch_no": batch_no,
					"serial_no": batchwise_serial_nos.get(batch_no).pop(0),
					"warehouse": row.warehouse,
					"qty": -1,
				},
			)


def _append_batch_entries(doc, row):
	precision = frappe.get_precision("Serial and Batch Entry", "qty")
	doc.has_batch_no = 1
	for batch_no, qty in row.batches_to_be_consume.items():
		if flt(qty, precision) > 0:
			doc.append(
				"entries", {"batch_no": batch_no, "warehouse": row.warehouse, "qty": flt(qty, precision) * -1}
			)


def get_batchwise_serial_nos(item_code, row):
	batchwise_serial_nos = {}

	for batch_no in row.batches_to_be_consume:
		serial_nos = frappe.get_all(
			"Serial No",
			filters={"item_code": item_code, "batch_no": batch_no, "name": ("in", row.serial_nos)},
		)

		if serial_nos:
			batchwise_serial_nos[batch_no] = sorted([serial_no.name for serial_no in serial_nos])

	return batchwise_serial_nos


@frappe.whitelist()
def get_expired_batch_items():
	expired_batches = get_expired_batches()
	if not expired_batches:
		return []
	return _enrich_expired_batches_with_stock(expired_batches)


def _enrich_expired_batches_with_stock(expired_batches):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_auto_batch_nos

	expired_batches_stock = get_auto_batch_nos(
		frappe._dict({"batch_no": list(expired_batches.keys()), "for_stock_levels": True})
	)
	for row in expired_batches_stock:
		row.update(expired_batches.get(row.batch_no))
	return expired_batches_stock


def get_expired_batches():
	batch = frappe.qb.DocType("Batch")

	data = (
		frappe.qb.from_(batch)
		.select(batch.item, batch.name.as_("batch_no"), batch.stock_uom)
		.where((batch.expiry_date <= nowdate()) & (batch.expiry_date.isnotnull()))
	).run(as_dict=True)

	if not data:
		return []

	expired_batches = frappe._dict()
	for row in data:
		expired_batches[row.batch_no] = row

	return expired_batches
