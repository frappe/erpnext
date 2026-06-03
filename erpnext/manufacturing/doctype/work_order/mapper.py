# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt


@frappe.whitelist()
def make_stock_entry(
	work_order_id: str,
	purpose: str,
	qty: float | None = None,
	target_warehouse: str | None = None,
	is_additional_transfer_entry: bool = False,
	source_stock_entry: str | None = None,
):
	work_order = frappe.get_doc("Work Order", work_order_id)
	if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.work_order = work_order_id
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	if purpose in ["Material Transfer for Manufacture", "Manufacture"]:
		stock_entry.subcontracting_inward_order = work_order.subcontracting_inward_order
	# accept 0 qty as well
	stock_entry.fg_completed_qty = (
		qty if qty is not None else (flt(work_order.qty) - flt(work_order.produced_qty))
	)

	if purpose == "Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
		stock_entry.project = work_order.project
	else:
		stock_entry.from_warehouse = (
			work_order.source_warehouse
			if work_order.skip_transfer and not work_order.from_wip_warehouse
			else wip_warehouse
		)
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.project = work_order.project
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)

	if purpose == "Disassemble":
		stock_entry.from_warehouse = work_order.fg_warehouse
		stock_entry.to_warehouse = target_warehouse or work_order.source_warehouse
		if source_stock_entry:
			stock_entry.source_stock_entry = source_stock_entry

	stock_entry.set_stock_entry_type()
	stock_entry.is_additional_transfer_entry = is_additional_transfer_entry
	stock_entry.get_items()

	return stock_entry.as_dict()


@frappe.whitelist()
def create_pick_list(source_name: str, target_doc: str | None = None, for_qty: float | None = None):
	for_qty = for_qty or json.loads(target_doc).get("for_qty")
	max_finished_goods_qty = frappe.db.get_value("Work Order", source_name, "qty")

	def update_item_quantity(source, target, source_parent):
		pending_to_issue = flt(source.required_qty) - flt(source.transferred_qty)
		desire_to_transfer = flt(source.required_qty) / max_finished_goods_qty * flt(for_qty)

		qty = 0
		if desire_to_transfer <= pending_to_issue:
			qty = desire_to_transfer
		elif pending_to_issue > 0:
			qty = pending_to_issue

		if qty:
			target.qty = qty
			target.stock_qty = qty
			target.uom = frappe.get_value("Item", source.item_code, "stock_uom")
			target.stock_uom = target.uom
			target.conversion_factor = 1
		else:
			target.delete()

	doc = get_mapped_doc(
		"Work Order",
		source_name,
		{
			"Work Order": {"doctype": "Pick List", "validation": {"docstatus": ["=", 1]}},
			"Work Order Item": {
				"doctype": "Pick List Item",
				"postprocess": update_item_quantity,
				"condition": lambda doc: abs(doc.transferred_qty) < abs(doc.required_qty),
			},
		},
		target_doc,
	)

	doc.purpose = "Material Transfer for Manufacture"
	doc.for_qty = for_qty

	doc.set_item_locations()

	return doc


@frappe.whitelist()
def make_stock_return_entry(work_order: str):
	from erpnext.stock.doctype.stock_entry.stock_entry_handler.manufacturing import (
		ManufactureStockEntry,
	)

	wo_doc = frappe.get_cached_doc("Work Order", work_order)

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.from_bom = 1
	stock_entry.is_return = 1
	stock_entry.work_order = work_order
	stock_entry.purpose = "Material Transfer for Manufacture"
	stock_entry.bom_no = wo_doc.bom_no
	stock_entry.set_stock_entry_type()

	ste_cls = ManufactureStockEntry(stock_entry)
	ste_cls.add_raw_materials_based_on_transfer()
	ste_cls.return_available_materials_in_source_wh()
	return stock_entry
