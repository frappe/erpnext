# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	get_subcontracting_boms_for_finished_goods,
)


@frappe.whitelist()
def make_subcontracting_po(source_name: str, target_doc: Document | str | None = None):
	def set_missing_values(source, target):
		_item_details = get_subcontracting_boms_for_finished_goods(source.finished_good)

		pending_qty = source.for_quantity - source.manufactured_qty
		service_item_qty = flt(_item_details.service_item_qty) or 1.0
		fg_item_qty = flt(_item_details.finished_good_qty) or 1.0

		target.is_subcontracted = 1
		target.supplier_warehouse = source.wip_warehouse
		target.append(
			"items",
			{
				"item_code": _item_details.service_item,
				"fg_item": source.finished_good,
				"uom": _item_details.service_item_uom,
				"stock_uom": _item_details.service_item_uom,
				"conversion_factor": _item_details.conversion_factor or 1,
				"item_name": _item_details.service_item,
				"qty": pending_qty * service_item_qty / fg_item_qty,
				"fg_item_qty": pending_qty,
				"job_card": source.name,
				"bom": source.semi_fg_bom,
				"warehouse": source.target_warehouse,
			},
		)

	doclist = get_mapped_doc(
		"Job Card",
		source_name,
		{
			"Job Card": {"doctype": "Purchase Order", "field_no_map": ["naming_series"]},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_material_request(source_name: str, target_doc: Document | str | None = None):
	def update_item(obj, target, source_parent):
		target.warehouse = source_parent.wip_warehouse

	def set_missing_values(source, target):
		target.material_request_type = "Material Transfer"

	doclist = get_mapped_doc(
		"Job Card",
		source_name,
		{
			"Job Card": {
				"doctype": "Material Request",
				"field_map": {
					"name": "job_card",
				},
			},
			"Job Card Item": {
				"doctype": "Material Request Item",
				"field_map": {"required_qty": "qty", "uom": "stock_uom", "name": "job_card_item"},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_stock_entry(source_name: str, target_doc: Document | str | None = None):
	from erpnext.stock.doctype.stock_entry.services.manufacturing import (
		set_previous_operation_serial_batch,
	)

	def update_item(source, target, source_parent):
		target.t_warehouse = source_parent.wip_warehouse

		if not target.conversion_factor:
			target.conversion_factor = 1

		pending_rm_qty = flt(source.required_qty) - flt(source.transferred_qty)
		if pending_rm_qty > 0:
			target.qty = pending_rm_qty

	def set_missing_values(source, target):
		if source.finished_good and not source.target_warehouse:
			frappe.throw(_("Please set the Target Warehouse in the Job Card"))

		if not source.skip_material_transfer or source.backflush_from_wip_warehouse:
			if not source.wip_warehouse:
				frappe.throw(_("Please set the WIP Warehouse in the Job Card"))

		target.purpose = "Material Transfer for Manufacture"
		target.from_bom = 1

		if source.semi_fg_bom:
			target.bom_no = source.semi_fg_bom

		# avoid negative 'For Quantity'
		pending_fg_qty = flt(source.get("for_quantity", 0)) - flt(source.get("transferred_qty", 0))
		target.fg_completed_qty = pending_fg_qty if pending_fg_qty > 0 else 0

		target.set_missing_values()
		target.set_stock_entry_type()

		wo_allows_alternate_item = frappe.db.get_value(
			"Work Order", target.work_order, "allow_alternative_item"
		)
		for item in target.items:
			item.allow_alternative_item = int(
				wo_allows_alternate_item
				and frappe.get_cached_value("Item", item.item_code, "allow_alternative_item")
			)
			set_previous_operation_serial_batch(target, item)

	doclist = get_mapped_doc(
		"Job Card",
		source_name,
		{
			"Job Card": {
				"doctype": "Stock Entry",
				"field_map": {"name": "job_card", "for_quantity": "fg_completed_qty"},
			},
			"Job Card Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"source_warehouse": "s_warehouse",
					"required_qty": "qty",
					"name": "job_card_item",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.required_qty > 0,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_corrective_job_card(
	source_name: str,
	operation: str | None = None,
	for_operation: str | None = None,
	target_doc: Document | str | None = None,
):
	def set_missing_values(source, target):
		target.is_corrective_job_card = 1
		target.operation = operation
		target.for_operation = for_operation

		target.set("time_logs", [])
		target.set("employee", [])
		target.set("items", [])
		target.set("sub_operations", [])
		target.set_sub_operations()
		target.get_required_items()

	doclist = get_mapped_doc(
		"Job Card",
		source_name,
		{
			"Job Card": {
				"doctype": "Job Card",
				"field_map": {
					"name": "for_job_card",
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist
