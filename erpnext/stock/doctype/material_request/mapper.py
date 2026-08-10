# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, comma_and, flt, get_link_to_form, getdate, nowdate

from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_supplier
from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	get_subcontracting_boms_for_finished_goods,
)


def set_missing_values(source, target_doc):
	if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) < getdate(nowdate()):
		target_doc.schedule_date = None
	target_doc.run_method("set_missing_values")
	target_doc.run_method("calculate_taxes_and_totals")


def get_source_item_for_qty(item, qty):
	"""Copy of the source row whose pending quantity is the requested quantity."""
	source_item = frappe._dict(item.as_dict())
	source_item.ordered_qty = 0
	source_item.received_qty = 0
	source_item.stock_qty = flt(qty) * flt(item.conversion_factor)

	return source_item


def update_item(obj, target, source_parent):
	target.conversion_factor = obj.conversion_factor

	qty = obj.ordered_qty or obj.received_qty
	target.qty = flt(flt(obj.stock_qty) - flt(qty)) / target.conversion_factor
	target.stock_qty = target.qty * target.conversion_factor
	if getdate(target.schedule_date) < getdate(nowdate()):
		target.schedule_date = None

	if target.fg_item:
		target.fg_item_qty = obj.stock_qty
		if sc_bom := get_subcontracting_boms_for_finished_goods(target.fg_item):
			target.item_code = sc_bom.service_item
			target.uom = sc_bom.service_item_uom
			target.conversion_factor = (
				frappe.db.get_value(
					"UOM Conversion Detail",
					{"parent": sc_bom.service_item, "uom": sc_bom.service_item_uom},
					"conversion_factor",
				)
				or 1
			)
			target.qty = target.fg_item_qty * sc_bom.conversion_factor
			target.stock_qty = target.qty * target.conversion_factor


@frappe.whitelist()
def make_purchase_order(
	source_name: str, target_doc: str | dict | Document | None = None, args: dict | str | None = None
):
	if args is None:
		args = frappe.flags.args or {}
	args = frappe.parse_json(args)

	is_subcontracted = (
		frappe.db.get_value("Material Request", source_name, "material_request_type") == "Subcontracting"
	)

	requested_qty = args.get("requested_qty") or {}

	def postprocess(source, target_doc):
		target_doc.is_subcontracted = is_subcontracted
		if args.get("supplier"):
			target_doc.supplier = args.get("supplier")
		set_missing_values(source, target_doc)

	def update_requested_item(obj, target, source_parent):
		if obj.name in requested_qty:
			obj = get_source_item_for_qty(obj, requested_qty[obj.name])
		update_item(obj, target, source_parent)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True

		qty = d.ordered_qty or d.received_qty

		return qty < d.stock_qty and child_filter

	def generate_field_map():
		field_map = [
			["name", "material_request_item"],
			["parent", "material_request"],
			["sales_order", "sales_order"],
			["sales_order_item", "sales_order_item"],
			["wip_composite_asset", "wip_composite_asset"],
		]

		if is_subcontracted:
			field_map.extend([["item_code", "fg_item"], ["qty", "fg_item_qty"]])
		else:
			field_map.extend([["uom", "stock_uom"], ["uom", "uom"]])

		return field_map

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Purchase Order",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["in", ["Purchase", "Subcontracting"]],
				},
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": generate_field_map(),
				"field_no_map": ["item_code", "item_name", "qty"] if is_subcontracted else [],
				"postprocess": update_requested_item,
				"condition": select_item,
			},
		},
		target_doc,
		postprocess,
	)

	doclist.set_onload("load_after_mapping", False)
	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name: str, target_doc: str | dict | Document | None = None):
	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Request for Quotation",
				"validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
			},
			"Material Request Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["project", "project_name"],
					["cost_center", "cost_center"],
				],
			},
		},
		target_doc,
	)

	return doclist


def get_default_supplier_for_item(item_code: str, company: str) -> str | None:
	return get_default_supplier(
		frappe._dict(),
		get_item_defaults(item_code, company),
		get_item_group_defaults(item_code, company),
		get_brand_defaults(item_code, company),
	)


@frappe.whitelist()
def get_item_default_suppliers(source_name: str, filtered_children: str | list | None = None) -> list[dict]:
	"""Pending items of the Material Request with their default supplier."""
	filtered_children = frappe.parse_json(filtered_children) if filtered_children else []

	material_request = frappe.get_doc("Material Request", source_name)
	material_request.check_permission("read")

	items = []
	for item in material_request.items:
		if filtered_children and item.name not in filtered_children:
			continue

		ordered_qty = flt(item.ordered_qty) or flt(item.received_qty)
		if ordered_qty >= flt(item.stock_qty):
			continue

		items.append(
			{
				"material_request_item": item.name,
				"item_code": item.item_code,
				"item_name": item.item_name,
				"pending_qty": (flt(item.stock_qty) - ordered_qty) / (flt(item.conversion_factor) or 1),
				"uom": item.uom,
				"supplier": get_default_supplier_for_item(item.item_code, material_request.company),
			}
		)

	return items


@frappe.whitelist(methods=["POST"])
def make_purchase_orders_by_supplier(source_name: str, item_suppliers: str | list) -> list[str]:
	"""Create one draft Purchase Order per supplier for the given Material Request items."""
	item_suppliers = frappe.parse_json(item_suppliers)
	if not item_suppliers:
		frappe.throw(_("Select at least one Item"))

	pending_items = {
		d["material_request_item"]: frappe._dict(d) for d in get_item_default_suppliers(source_name)
	}

	items_by_supplier = {}
	requested_items = set()
	for row in item_suppliers:
		row = frappe._dict(row)
		pending = pending_items.get(row.material_request_item) or frappe._dict()
		item_link = get_link_to_form("Item", row.item_code)

		if row.material_request_item in requested_items:
			frappe.throw(_("Item {0} cannot be ordered more than once").format(item_link))

		requested_items.add(row.material_request_item)

		if not row.supplier:
			frappe.throw(_("Select a Supplier for Item {0}").format(item_link))

		if flt(row.qty) <= 0 or flt(row.qty) > flt(pending.pending_qty):
			pending_qty = frappe.format_value(flt(pending.pending_qty), "Float")
			frappe.throw(
				_("Quantity for Item {0} must be greater than zero and cannot exceed {1}").format(
					item_link, frappe.bold(f"{pending_qty} {pending.uom or ''}".strip())
				)
			)

		items_by_supplier.setdefault(row.supplier, {})[row.material_request_item] = flt(row.qty)

	purchase_orders = []
	is_rescheduled = False
	for supplier, requested_qty in items_by_supplier.items():
		purchase_order = make_purchase_order(
			source_name,
			args={
				"supplier": supplier,
				"filtered_children": list(requested_qty),
				"requested_qty": requested_qty,
			},
		)
		for item in purchase_order.items:
			if not item.schedule_date:
				item.schedule_date = nowdate()
				is_rescheduled = True

		purchase_order.insert()
		purchase_orders.append(purchase_order.name)

	if is_rescheduled:
		frappe.toast(
			_("{0} was set to today for items whose requested date has passed").format(
				_(frappe.get_meta("Purchase Order Item").get_label("schedule_date"))
			),
			indicator="orange",
		)

	if len(purchase_orders) > 1:
		frappe.msgprint(
			_("{0} created").format(
				comma_and([get_link_to_form("Purchase Order", name) for name in purchase_orders])
			)
		)

	return purchase_orders


@frappe.whitelist()
def get_items_based_on_default_supplier(supplier: str):
	supplier_items = [
		d.parent
		for d in frappe.db.get_all(
			"Item Default", {"default_supplier": supplier, "parenttype": "Item"}, "parent"
		)
	]

	return supplier_items


@frappe.whitelist()
def make_supplier_quotation(source_name: str, target_doc: str | dict | Document | None = None):
	def postprocess(source, target_doc):
		set_missing_values(source, target_doc)

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Supplier Quotation",
				"validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
			},
			"Material Request Item": {
				"doctype": "Supplier Quotation Item",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"sales_order": "sales_order",
				},
			},
		},
		target_doc,
		postprocess,
	)

	doclist.set_onload("load_after_mapping", False)
	return doclist


@frappe.whitelist()
def make_stock_entry(source_name: str, target_doc: str | dict | Document | None = None):
	def update_item(obj, target, source_parent):
		qty = (
			flt(flt(obj.stock_qty) - flt(obj.ordered_qty)) / target.conversion_factor
			if flt(obj.stock_qty) > flt(obj.ordered_qty)
			else 0
		)
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		if (
			source_parent.material_request_type == "Material Transfer"
			or source_parent.material_request_type == "Customer Provided"
		):
			target.t_warehouse = obj.warehouse
		else:
			target.s_warehouse = obj.warehouse

		if source_parent.material_request_type == "Customer Provided":
			target.allow_zero_valuation_rate = 1

		if source_parent.material_request_type == "Material Transfer":
			target.s_warehouse = obj.from_warehouse

	def set_missing_values(source, target):
		target.purpose = source.material_request_type
		target.from_warehouse = source.set_from_warehouse
		target.to_warehouse = source.set_warehouse
		if source.material_request_type == "Material Issue":
			target.from_warehouse = source.set_warehouse
			target.to_warehouse = None

		if source.job_card:
			target.purpose = "Material Transfer for Manufacture"

		if source.work_order:
			target.purpose = "Material Transfer for Manufacture"

		if source.material_request_type == "Customer Provided":
			target.purpose = "Material Receipt"

		target.set_transfer_qty()
		target.set_actual_qty()
		target.calculate_rate_and_amount(raise_error_if_no_rate=False)
		target.stock_entry_type = target.purpose

		if source.job_card:
			job_card_details = frappe.get_all(
				"Job Card", filters={"name": source.job_card}, fields=["bom_no", "for_quantity"]
			)

			if job_card_details and job_card_details[0]:
				target.bom_no = job_card_details[0].bom_no
				target.fg_completed_qty = job_card_details[0].for_quantity
				target.from_bom = 1

		if source.work_order:
			work_order_details = frappe.db.get_value(
				"Work Order", source.work_order, ["bom_no", "use_multi_level_bom"], as_dict=True
			)

			if work_order_details:
				target.bom_no = work_order_details.bom_no
				target.use_multi_level_bom = work_order_details.use_multi_level_bom
				target.from_bom = 1
				# not fg-qty-driven, mirrors the Pick List -> Stock Entry transfer for this Work Order
				target.fg_completed_qty = 0

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": [
						"in",
						["Material Transfer", "Material Issue", "Customer Provided"],
					],
				},
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom",
					"job_card_item": "job_card_item",
				},
				"field_no_map": ["expense_account"],
				"postprocess": update_item,
				"condition": lambda doc: (
					flt(doc.ordered_qty, doc.precision("ordered_qty"))
					< flt(doc.stock_qty, doc.precision("ordered_qty"))
				),
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def create_pick_list(source_name: str, target_doc: str | dict | Document | None = None):
	def update_item(obj, target, source_parent):
		qty = flt((obj.stock_qty - obj.picked_qty) / target.conversion_factor, obj.precision("qty"))
		target.qty = qty
		target.stock_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

	doc = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Pick List",
				"field_map": {"material_request_type": "purpose"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Material Request Item": {
				"doctype": "Pick List Item",
				"field_map": {
					"name": "material_request_item",
					"stock_qty": "stock_qty",
					"from_warehouse": "warehouse",
				},
				"postprocess": update_item,
				"condition": lambda doc: (
					flt(doc.picked_qty, doc.precision("picked_qty"))
					< flt(doc.stock_qty, doc.precision("stock_qty"))
				),
			},
		},
		target_doc,
	)

	doc.set_item_locations()

	return doc


@frappe.whitelist()
def make_in_transit_stock_entry(source_name: str, in_transit_warehouse: str):
	ste_doc = make_stock_entry(source_name)
	ste_doc.add_to_transit = 1
	ste_doc.to_warehouse = in_transit_warehouse

	for row in ste_doc.items:
		row.t_warehouse = in_transit_warehouse

	return ste_doc
