from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from erpnext.stock.utils import get_combine_datetime

from .base import BaseStockEntry
from .manufacturing import (
	ceil_qty_if_uom_has_whole_number,
	get_bom_items,
	get_production_item_details,
	get_secondary_items,
)


class DisassembleStockEntry(BaseStockEntry):
	def validate(self):
		self.validate_warehouse()

	def validate_warehouse(self):
		for row in self.doc.items:
			if not row.s_warehouse and not row.t_warehouse:
				frappe.throw(_("Source or Target Warehouse is required for item {0}").format(row.item_code))

	def validate_fg_completed_qty(self):
		if not self.doc.source_stock_entry:
			return

		from erpnext.manufacturing.doctype.work_order.work_order import get_disassembly_available_qty

		available_qty = get_disassembly_available_qty(self.doc.source_stock_entry, self.doc.name)

		if flt(self.doc.fg_completed_qty) > available_qty:
			frappe.throw(
				_(
					"Cannot disassemble {0} qty against Stock Entry {1}. Only {2} qty available to disassemble."
				).format(
					self.doc.fg_completed_qty,
					self.doc.source_stock_entry,
					available_qty,
				),
				title=_("Excess Disassembly"),
			)

	def add_items(self):
		"""
		Priority:
		1. From a specific Manufacture Stock Entry (exact reversal)
		2. From Work Order Manufacture Stock Entries (averaged reversal)
		3. From BOM (standalone disassembly)
		"""

		# Auto-set source_stock_entry if WO has exactly one manufacture entry
		if not self.doc.get("source_stock_entry") and self.doc.work_order:
			manufacture_entries = frappe.get_all(
				"Stock Entry",
				filters={
					"work_order": self.doc.work_order,
					"purpose": "Manufacture",
					"docstatus": 1,
				},
				pluck="name",
			)
			if len(manufacture_entries) == 1:
				self.doc.source_stock_entry = manufacture_entries[0]

		if self.doc.get("source_stock_entry"):
			return self._add_items_for_disassembly_from_stock_entry()

		if self.doc.work_order:
			return self._add_items_for_disassembly_from_work_order()

		return self._add_items_for_disassembly_from_bom()

	def _add_items_for_disassembly_from_stock_entry(self):
		source_fg_qty = frappe.db.get_value("Stock Entry", self.doc.source_stock_entry, "fg_completed_qty")
		if not source_fg_qty:
			frappe.throw(
				_("Source Stock Entry {0} has no finished goods quantity").format(self.doc.source_stock_entry)
			)

		disassemble_qty = flt(self.doc.fg_completed_qty)
		scale_factor = disassemble_qty / flt(source_fg_qty)

		self._append_disassembly_row_from_source(
			disassemble_qty=disassemble_qty,
			scale_factor=scale_factor,
		)

	def _add_items_for_disassembly_from_work_order(self):
		wo_produced_qty = frappe.db.get_value("Work Order", self.doc.work_order, "produced_qty")

		wo_produced_qty = flt(wo_produced_qty)
		if wo_produced_qty <= 0:
			frappe.throw(_("Work Order {0} has no produced qty").format(self.doc.work_order))

		disassemble_qty = flt(self.doc.fg_completed_qty)
		if disassemble_qty <= 0:
			frappe.throw(_("Disassemble Qty cannot be less than or equal to 0."))

		scale_factor = disassemble_qty / wo_produced_qty

		self._append_disassembly_row_from_source(
			disassemble_qty=disassemble_qty,
			scale_factor=scale_factor,
		)

	def _append_disassembly_row_from_source(self, disassemble_qty, scale_factor):
		for source_row in self.get_items_from_manufacture_stock_entry():
			self._append_disassembly_item(source_row, disassemble_qty, scale_factor)

	def _get_disassembly_warehouses(self, source_row, disassemble_qty, scale_factor):
		if source_row.is_finished_item:
			return disassemble_qty, self.doc.from_warehouse or source_row.t_warehouse, ""
		elif source_row.s_warehouse:
			return flt(source_row.qty * scale_factor), "", self.doc.to_warehouse or source_row.s_warehouse
		else:
			return flt(source_row.qty * scale_factor), source_row.t_warehouse, ""

	def _build_disassembly_item_dict(self, source_row, qty, s_warehouse, t_warehouse):
		return {
			"item_code": source_row.item_code,
			"item_name": source_row.item_name,
			"description": source_row.description,
			"stock_uom": source_row.stock_uom,
			"uom": source_row.uom,
			"conversion_factor": source_row.conversion_factor,
			"basic_rate": source_row.basic_rate,
			"qty": qty,
			"s_warehouse": s_warehouse,
			"t_warehouse": t_warehouse,
			"is_finished_item": source_row.is_finished_item,
			"secondary_item_type": source_row.secondary_item_type,
			"is_legacy_scrap_item": source_row.is_legacy_scrap_item,
			"bom_secondary_item": source_row.bom_secondary_item,
			"bom_no": source_row.bom_no,
			"use_serial_batch_fields": 1 if (source_row.batch_no or source_row.serial_no) else 0,
		}

	def _append_disassembly_item(self, source_row, disassemble_qty, scale_factor):
		qty, s_warehouse, t_warehouse = self._get_disassembly_warehouses(
			source_row, disassemble_qty, scale_factor
		)
		item = self._build_disassembly_item_dict(source_row, qty, s_warehouse, t_warehouse)
		if self.doc.source_stock_entry:
			item.update({"against_stock_entry": self.doc.source_stock_entry, "ste_detail": source_row.name})
		self.doc.append("items", item)

	def _add_items_for_disassembly_from_bom(self):
		if not self.doc.bom_no or not self.doc.fg_completed_qty:
			frappe.throw(_("BOM and Finished Good Quantity is mandatory for Disassembly"))

		self.add_raw_materials()
		self.add_secondary_items()
		self.add_finished_goods()

	def add_raw_materials(self):
		# Raw materials will be available after disassembly in target warehouse
		items = get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom)

		for row in items:
			row["t_warehouse"] = self.doc.to_warehouse
			row["from_warehouse"] = ""
			row["is_finished_item"] = 0
			row["qty"] = flt(row["qty"]) * flt(self.doc.fg_completed_qty)
			row["uom"] = row.get("uom") or row.get("stock_uom")
			self.doc.append("items", row)

	def add_secondary_items(self):
		# Secondary items will be removed from source warehouse

		secondary_items = get_secondary_items(self.doc.bom_no, self.doc.work_order)
		for row in secondary_items:
			item_args = {}
			fields = [
				"item_code",
				"item_name",
				"uom",
				"stock_uom",
				"conversion_factor",
				"item_group",
				"description",
				"secondary_item_type",
			]
			for field in fields:
				item_args[field] = row.get(field)

			item_args["is_legacy_scrap_item"] = row.get("is_legacy")
			item_args["s_warehouse"] = self.doc.from_warehouse
			item_args["uom"] = item_args.get("uom") or item_args.get("stock_uom")
			item_args["bom_secondary_item"] = row.get("name")

			row.qty = row.qty * self.doc.fg_completed_qty
			if row.get("process_loss_per"):
				row.qty -= flt(row.qty * row.get("process_loss_per") / 100)
			item_args["qty"] = ceil_qty_if_uom_has_whole_number(row.qty, item_args["uom"])

			self.doc.append("items", item_args)

	def add_finished_goods(self):
		item_details = get_production_item_details(self.doc.work_order, self.doc.bom_no)

		item_details.update(
			{
				"conversion_factor": 1,
				"uom": item_details.stock_uom,
				"qty": self.doc.fg_completed_qty,
				"t_warehouse": None,
				"s_warehouse": self.doc.from_warehouse,
				"is_finished_item": 1,
			}
		)

		item_details["item_code"] = item_details["name"]
		del item_details["name"]

		self.doc.append("items", item_details)

	def get_items_from_manufacture_stock_entry(self):
		SE = frappe.qb.DocType("Stock Entry")
		SED = frappe.qb.DocType("Stock Entry Detail")
		query = frappe.qb.from_(SED).join(SE).on(SED.parent == SE.name).where(SE.docstatus == 1)

		common_fields = [
			SED.item_code,
			SED.item_name,
			SED.description,
			SED.stock_uom,
			SED.uom,
			SED.basic_rate,
			SED.conversion_factor,
			SED.is_finished_item,
			SED.secondary_item_type,
			SED.is_legacy_scrap_item,
			SED.bom_secondary_item,
			SED.batch_no,
			SED.serial_no,
			SED.use_serial_batch_fields,
			SED.s_warehouse,
			SED.t_warehouse,
			SED.bom_no,
		]

		if self.doc.source_stock_entry:
			return (
				query.select(SED.name, SED.qty, SED.transfer_qty, *common_fields)
				.where(SE.name == self.doc.source_stock_entry)
				.orderby(SED.idx)
				.run(as_dict=True)
			)

		return (
			query.select(Sum(SED.qty).as_("qty"), Sum(SED.transfer_qty).as_("transfer_qty"), *common_fields)
			.where(SE.purpose == "Manufacture")
			.where(SE.work_order == self.doc.work_order)
			.groupby(SED.item_code)
			.orderby(SED.idx)
			.run(as_dict=True)
		)

	def on_submit(self):
		self.set_serial_batch_for_disassembly()
		self.update_disassembled_order()

	def on_cancel(self):
		self.update_disassembled_order()

	def set_serial_batch_for_disassembly(self):
		if self.doc.get("source_stock_entry"):
			self._set_serial_batch_for_disassembly_from_stock_entry()
		else:
			self._set_serial_batch_for_disassembly_from_available_materials()

	def _set_serial_batch_for_disassembly_from_stock_entry(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			get_voucher_wise_serial_batch_from_bundle,
		)

		source_fg_qty = flt(
			frappe.db.get_value("Stock Entry", self.doc.source_stock_entry, "fg_completed_qty")
		)
		scale_factor = flt(self.doc.fg_completed_qty) / source_fg_qty if source_fg_qty else 0
		bundle_data = get_voucher_wise_serial_batch_from_bundle(voucher_no=[self.doc.source_stock_entry])
		source_rows_by_name = {r.name: r for r in self.get_items_from_manufacture_stock_entry()}
		for row in self.doc.items:
			if not row.ste_detail:
				continue
			source_row = source_rows_by_name.get(row.ste_detail)
			if source_row:
				self._apply_bundle_to_disassembly_row(row, source_row, bundle_data, scale_factor)

	def _apply_bundle_to_disassembly_row(self, row, source_row, bundle_data, scale_factor):
		source_warehouse = source_row.s_warehouse or source_row.t_warehouse
		key = (source_row.item_code, source_warehouse, self.doc.source_stock_entry)
		source_bundle = bundle_data.get(key, {})
		batches = self._extract_batches(source_row, source_bundle, row, scale_factor)
		serial_nos = self._extract_serial_nos(source_row, source_bundle, row)
		self._set_serial_batch_bundle_for_disassembly_row(row, serial_nos, batches)

	def _extract_batches(self, source_row, source_bundle, row, scale_factor):
		batches = defaultdict(float)
		if source_bundle.get("batch_nos"):
			self._allocate_batches(batches, source_bundle["batch_nos"], row.transfer_qty, scale_factor)
		elif source_row.batch_no:
			batches[source_row.batch_no] = row.transfer_qty
		return batches

	def _allocate_batches(self, batches, batch_nos, transfer_qty, scale_factor):
		qty_remaining = transfer_qty
		for batch_no, batch_qty in batch_nos.items():
			if qty_remaining <= 0:
				break
			alloc = min(abs(flt(batch_qty)) * scale_factor, qty_remaining)
			batches[batch_no] = alloc
			qty_remaining -= alloc

	def _extract_serial_nos(self, source_row, source_bundle, row):
		if source_bundle.get("serial_nos"):
			return get_serial_nos(source_bundle["serial_nos"])[: int(row.transfer_qty)]
		elif source_row.serial_no:
			return get_serial_nos(source_row.serial_no)[: int(row.transfer_qty)]
		return []

	def _set_serial_batch_for_disassembly_from_available_materials(self):
		available_materials = get_available_materials(self.doc.work_order, self.doc)
		for row in self.doc.items:
			warehouse = row.s_warehouse or row.t_warehouse
			materials = available_materials.get((row.item_code, warehouse))
			if materials:
				self._apply_available_material_bundle(row, materials)

	def _apply_available_material_bundle(self, row, materials):
		batches = self._collect_available_batches(materials.batch_details, row.transfer_qty)
		serial_nos = materials.serial_nos[: int(row.transfer_qty)] if materials.serial_nos else []
		self._set_serial_batch_bundle_for_disassembly_row(row, serial_nos, batches)

	def _collect_available_batches(self, batch_details, transfer_qty):
		batches, qty = defaultdict(float), transfer_qty
		for batch_no, batch_qty in batch_details.items():
			if qty <= 0:
				break
			batch_qty = abs(batch_qty)
			if batch_qty <= qty:
				batches[batch_no], qty = batch_qty, qty - batch_qty
			else:
				batches[batch_no], qty = qty, 0
		return batches

	def _set_serial_batch_bundle_for_disassembly_row(self, row, serial_nos, batches):
		if not serial_nos and not batches:
			return

		warehouse = row.s_warehouse or row.t_warehouse
		bundle_doc = SerialBatchCreation(
			{
				"item_code": row.item_code,
				"warehouse": warehouse,
				"posting_datetime": get_combine_datetime(self.doc.posting_date, self.doc.posting_time),
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"voucher_detail_no": row.name,
				"qty": row.transfer_qty,
				"type_of_transaction": "Inward" if row.t_warehouse else "Outward",
				"company": self.doc.company,
				"do_not_submit": True,
			}
		).make_serial_and_batch_bundle(serial_nos=serial_nos, batch_nos=batches)

		row.serial_and_batch_bundle = bundle_doc.name
		row.use_serial_batch_fields = 0

	def update_disassembled_order(self):
		if not self.doc.work_order:
			return

		if self.doc.fg_completed_qty:
			pro_doc = frappe.get_doc("Work Order", self.doc.work_order)
			pro_doc.run_method(
				"update_disassembled_qty", self.doc.fg_completed_qty, self.doc._action == "cancel"
			)


def get_available_materials(work_order, stock_entry_doc=None) -> dict:
	data = get_stock_entry_data(work_order, stock_entry_doc=stock_entry_doc)
	available_materials = {}
	for row in data:
		key = _get_material_key(row, stock_entry_doc)
		if key not in available_materials:
			available_materials[key] = frappe._dict(
				{"item_details": row, "batch_details": defaultdict(float), "qty": 0, "serial_nos": []}
			)
		_update_material_qty(available_materials[key], row, stock_entry_doc)
	return available_materials


def _get_material_key(row, stock_entry_doc):
	if stock_entry_doc and stock_entry_doc.purpose == "Disassemble":
		return (row.item_code, row.s_warehouse or row.warehouse)
	if row.purpose != "Material Transfer for Manufacture":
		return (row.item_code, row.s_warehouse)
	return (row.item_code, row.warehouse)


def _update_material_qty(item_data, row, stock_entry_doc):
	is_inward = row.purpose == "Material Transfer for Manufacture" or (
		stock_entry_doc and stock_entry_doc.purpose == "Disassemble" and row.purpose == "Manufacture"
	)
	if is_inward:
		_add_inward_material_qty(item_data, row)
	else:
		_deduct_consumed_material_qty(item_data, row)


def _add_inward_material_qty(item_data, row):
	item_data.qty += row.qty
	if row.batch_no:
		item_data.batch_details[row.batch_no] += row.qty
	elif row.batch_nos:
		for batch_no, qty in row.batch_nos.items():
			item_data.batch_details[batch_no] += qty
	_extend_serial_nos_from_row(item_data, row)


def _extend_serial_nos_from_row(item_data, row):
	sn = row.serial_no or row.serial_nos
	if sn:
		item_data.serial_nos.extend(get_serial_nos(sn))
		item_data.serial_nos.sort()


def _deduct_consumed_material_qty(item_data, row):
	item_data.qty -= row.qty
	if row.batch_no:
		item_data.batch_details[row.batch_no] -= row.qty
	elif row.batch_nos:
		for batch_no, qty in row.batch_nos.items():
			item_data.batch_details[batch_no] += qty
	_remove_serial_nos_from_available(item_data, row)


def _remove_serial_nos_from_available(item_data, row):
	sn = row.serial_no or row.serial_nos
	if not sn:
		return
	for serial_no in get_serial_nos(sn):
		if serial_no in item_data.serial_nos:
			item_data.serial_nos.remove(serial_no)


def get_stock_entry_data(work_order, stock_entry_doc=None):
	data = _run_stock_entry_query(work_order, stock_entry_doc)
	if not data:
		return []
	_enrich_with_bundle_data(data, stock_entry_doc)
	return data


def _run_stock_entry_query(work_order, stock_entry_doc):
	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	query = _build_stock_entry_base_query(se, sed, work_order)
	query = _apply_stock_entry_purpose_filter(query, se, sed, stock_entry_doc)
	return query.run(as_dict=1)


def _build_stock_entry_base_query(se, sed, work_order):
	return (
		frappe.qb.from_(se)
		.from_(sed)
		.select(
			sed.item_name,
			sed.original_item,
			sed.item_code,
			sed.qty,
			sed.t_warehouse.as_("warehouse"),
			sed.s_warehouse.as_("s_warehouse"),
			sed.description,
			sed.stock_uom,
			sed.expense_account,
			sed.cost_center,
			sed.serial_and_batch_bundle,
			sed.batch_no,
			sed.serial_no,
			se.purpose,
			se.name,
		)
		.where((se.name == sed.parent) & (se.work_order == work_order) & (se.docstatus == 1))
		.orderby(se.creation, sed.item_code, sed.idx)
	)


def _apply_stock_entry_purpose_filter(query, se, sed, stock_entry_doc):
	if stock_entry_doc and stock_entry_doc.purpose == "Disassemble":
		query = query.where(se.purpose.isin(["Disassemble", "Manufacture"]))
		return query.where(se.name != stock_entry_doc.name)
	query = query.where(
		se.purpose.isin(
			["Manufacture", "Material Consumption for Manufacture", "Material Transfer for Manufacture"]
		)
	)
	return query.where(sed.s_warehouse.isnotnull())


def _enrich_with_bundle_data(data, stock_entry_doc):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_voucher_wise_serial_batch_from_bundle,
	)

	voucher_nos = [row.get("name") for row in data if row.get("name")]
	if not voucher_nos:
		return
	bundle_data = get_voucher_wise_serial_batch_from_bundle(voucher_no=voucher_nos)
	for row in data:
		key = _get_bundle_key(row, stock_entry_doc)
		if bundle_data.get(key):
			row.update(bundle_data.get(key))


def _get_bundle_key(row, stock_entry_doc):
	if stock_entry_doc and stock_entry_doc.purpose == "Disassemble":
		return (row.item_code, row.s_warehouse or row.warehouse, row.name)
	if row.purpose != "Material Transfer for Manufacture":
		return (row.item_code, row.s_warehouse, row.name)
	return (row.item_code, row.warehouse, row.name)
