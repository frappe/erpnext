# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, getdate, nowdate

from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	get_subcontracting_boms_for_finished_goods,
)


def set_missing_values(source, target_doc):
	if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) < getdate(nowdate()):
		target_doc.schedule_date = None
	target_doc.run_method("set_missing_values")
	target_doc.run_method("calculate_taxes_and_totals")


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
	source_name: str, target_doc: str | Document | None = None, args: dict | str | None = None
):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	is_subcontracted = (
		frappe.db.get_value("Material Request", source_name, "material_request_type") == "Subcontracting"
	)

	def postprocess(source, target_doc):
		target_doc.is_subcontracted = is_subcontracted
		set_missing_values(source, target_doc)

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
				"postprocess": update_item,
				"condition": select_item,
			},
		},
		target_doc,
		postprocess,
	)

	doclist.set_onload("load_after_mapping", False)
	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name: str, target_doc: str | Document | None = None):
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
				],
			},
		},
		target_doc,
	)

	return doclist


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
def make_purchase_order_based_on_supplier(
	source_name: str, target_doc: str | Document | None = None, args: dict | None = None
):
	mr = source_name

	supplier_items = get_items_based_on_default_supplier(args.get("supplier"))

	def postprocess(source, target_doc):
		target_doc.supplier = args.get("supplier")
		if getdate(target_doc.schedule_date) < getdate(nowdate()):
			target_doc.schedule_date = None
		target_doc.set(
			"items",
			[d for d in target_doc.get("items") if d.get("item_code") in supplier_items and d.get("qty") > 0],
		)

		set_missing_values(source, target_doc)

	target_doc = get_mapped_doc(
		"Material Request",
		mr,
		{
			"Material Request": {
				"doctype": "Purchase Order",
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["uom", "stock_uom"],
					["uom", "uom"],
				],
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.qty,
			},
		},
		target_doc,
		postprocess,
	)

	return target_doc


@frappe.whitelist()
def make_supplier_quotation(source_name: str, target_doc: str | Document | None = None):
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
def make_stock_entry(source_name: str, target_doc: str | Document | None = None):
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
def create_pick_list(source_name: str, target_doc: str | Document | None = None):
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
