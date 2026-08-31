# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Document-mapping and creation helpers for Work Order.

These functions build related documents (Work Order, Stock Entry, Job Card,
Pick List) from a Work Order. They were extracted from work_order.py to slim
the controller; work_order.py re-exports them for backward compatibility.
"""

import json
import math
from functools import partial

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, get_link_to_form, nowdate

from erpnext.manufacturing.doctype.bom.bom import get_bom_item_rate
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


@frappe.whitelist()
def get_item_details(item: str, project: str | None = None, skip_bom_info: bool = False, throw: bool = True):
	frappe.has_permission("Item", "read", throw=True)

	res = _item_master_details(item)
	if not res:
		return {}
	if skip_bom_info:
		return res

	res["bom_no"] = _default_bom_for_item(item, project)
	if not res["bom_no"]:
		return _handle_missing_default_bom(res, item, project, throw)

	_merge_bom_details(res, project)
	return res


def _item_master_details(item):
	item_table = frappe.qb.DocType("Item")
	res = (
		frappe.qb.from_(item_table)
		.select(
			item_table.stock_uom,
			item_table.description,
			item_table.item_name,
			item_table.allow_alternative_item,
			item_table.include_item_in_manufacturing,
		)
		.where((item_table.disabled == 0) & (item_table.name == item) & _item_is_alive(item_table))
	).run(as_dict=1)
	return res[0] if res else {}


def _item_is_alive(item_table):
	# "not set" end_of_life is NULL on postgres (the MariaDB zero-date '0000-00-00' is an invalid
	# date constant there), so only add the zero-date term on MariaDB.
	is_alive = item_table.end_of_life.isnull() | (item_table.end_of_life > nowdate())
	if frappe.db.db_type != "postgres":
		is_alive |= item_table.end_of_life == "0000-00-00"
	return is_alive


def _default_bom_for_item(item, project):
	filters = (
		{"item": item, "project": project} if project else {"item": item, "is_default": 1, "docstatus": 1}
	)
	bom_no = frappe.db.get_value("BOM", filters=filters)
	if bom_no:
		return bom_no

	variant_of = frappe.db.get_value("Item", item, "variant_of")
	return frappe.db.get_value("BOM", {"item": variant_of, "is_default": 1}) if variant_of else None


def _handle_missing_default_bom(res, item, project, throw):
	if project:
		res = get_item_details(item, throw=throw)
		frappe.msgprint(
			_("Default BOM not found for Item {0} and Project {1}").format(item, project), alert=1
		)
		return res

	msg = _("Default BOM for {0} not found").format(item)
	frappe.msgprint(msg, raise_exception=throw, indicator="yellow", alert=(not throw))
	return res


def _merge_bom_details(res, project):
	bom_data = frappe.db.get_value(
		"BOM",
		res["bom_no"],
		["project", "allow_alternative_item", "transfer_material_against", "item_name"],
		as_dict=1,
	)
	res["project"] = project or bom_data.pop("project")
	res.update(bom_data)
	res.update(check_if_scrap_warehouse_mandatory(res["bom_no"]))


@frappe.whitelist()
def make_work_order(
	bom_no: str,
	item: str,
	qty: float = 0,
	company: str | None = None,
	project: str | None = None,
	variant_items: str | list | None = None,
	use_multi_level_bom: bool | None = None,
):
	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	item_details = get_item_details(item, project)
	bom_no = _variant_default_bom(item, bom_no) or bom_no
	wo_doc = _new_work_order(item, bom_no, company, item_details, use_multi_level_bom)

	if flt(qty) > 0:
		wo_doc.qty = flt(qty)
		wo_doc.get_items_and_operations_from_bom()

	if variant_items and not wo_doc.use_multi_level_bom:
		add_variant_item(variant_items, wo_doc, bom_no, "required_items")

	return wo_doc


def _variant_default_bom(item, bom_no=None):
	if not frappe.db.get_value("Item", item, "variant_of"):
		return None
	# selected BOM already belongs to this variant
	if bom_no and frappe.db.get_value("BOM", bom_no, "item") == item:
		return None
	return frappe.db.get_value("BOM", {"item": item, "is_default": 1, "docstatus": 1})


def _new_work_order(item, bom_no, company, item_details, use_multi_level_bom):
	from erpnext import get_default_company

	wo_doc = frappe.new_doc("Work Order")
	wo_doc.track_semi_finished_goods = frappe.db.get_value("BOM", bom_no, "track_semi_finished_goods")
	wo_doc.production_item = item
	wo_doc.company = company or get_default_company()
	wo_doc.update(item_details)
	wo_doc.bom_no = bom_no
	wo_doc.use_multi_level_bom = cint(use_multi_level_bom)
	return wo_doc


def add_variant_item(variant_items, wo_doc, bom_no, table_name="items"):
	variant_items = frappe.parse_json(variant_items)

	for item in variant_items:
		_add_variant_row(item, wo_doc, bom_no, table_name)


def _add_variant_row(item, wo_doc, bom_no, table_name):
	bom_doc = frappe.get_cached_doc("BOM", bom_no)
	args = _variant_item_args(item, wo_doc, bom_doc)

	existing_row = (
		get_template_rm_item(wo_doc, item.get("item_code")) if table_name == "required_items" else None
	)
	if existing_row:
		existing_row.update(args)
	else:
		wo_doc.append(table_name, args)


def _variant_item_args(item, wo_doc, bom_doc):
	args = frappe._dict(
		item_code=item.get("variant_item_code"),
		required_qty=item.get("qty"),
		qty=item.get("qty"),  # for bom
		source_warehouse=item.get("source_warehouse"),
		operation=item.get("operation"),
	)
	item_data = get_item_details(args.item_code, skip_bom_info=True)
	args.update(item_data)

	args["rate"] = _variant_item_rate(args, wo_doc, bom_doc)
	if not args.source_warehouse:
		default = get_item_defaults(item.get("variant_item_code"), wo_doc.company)
		args["source_warehouse"] = default.default_warehouse

	args["amount"] = flt(args.get("required_qty")) * flt(args.get("rate"))
	args["uom"] = item_data.stock_uom
	return args


def _variant_item_rate(args, wo_doc, bom_doc):
	return get_bom_item_rate(
		{
			"company": wo_doc.company,
			"item_code": args.get("item_code"),
			"qty": args.get("required_qty"),
			"uom": args.get("stock_uom"),
			"stock_uom": args.get("stock_uom"),
			"conversion_factor": 1,
		},
		bom_doc,
	)


def get_template_rm_item(wo_doc, item_code):
	for row in wo_doc.required_items:
		if row.item_code == item_code:
			return row


@frappe.whitelist()
def check_if_scrap_warehouse_mandatory(bom_no: str):
	frappe.has_permission("BOM", "read", throw=True)

	res = {"set_scrap_wh_mandatory": False}
	if bom_no:
		bom = frappe.get_doc("BOM", bom_no)

		if bom.has_scrap_items():
			res["set_scrap_wh_mandatory"] = True

	return res


@frappe.whitelist()
def make_stock_entry(
	work_order_id: str,
	purpose: str,
	qty: float | None = None,
	target_warehouse: str | None = None,
	is_additional_transfer_entry: bool = False,
	source_stock_entry: str | None = None,
):
	frappe.has_permission("Stock Entry", "create", throw=True)

	work_order = frappe.get_doc("Work Order", work_order_id)
	stock_entry = _new_manufacture_stock_entry(work_order, purpose, qty)
	_set_stock_entry_warehouses(stock_entry, work_order, purpose, target_warehouse, source_stock_entry)

	stock_entry.set_stock_entry_type()
	stock_entry.is_additional_transfer_entry = is_additional_transfer_entry
	stock_entry.get_items()

	return stock_entry.as_dict()


def _new_manufacture_stock_entry(work_order, purpose, qty):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.work_order = work_order.name
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
	return stock_entry


def _set_stock_entry_warehouses(stock_entry, work_order, purpose, target_warehouse, source_stock_entry):
	is_group = frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group")
	wip_warehouse = None if is_group else work_order.wip_warehouse
	stock_entry.project = work_order.project

	if purpose == "Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
	else:
		skip = work_order.skip_transfer and not work_order.from_wip_warehouse
		stock_entry.from_warehouse = work_order.source_warehouse if skip else wip_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)

	if purpose == "Disassemble":
		stock_entry.from_warehouse = work_order.fg_warehouse
		stock_entry.to_warehouse = target_warehouse or work_order.source_warehouse
		if source_stock_entry:
			stock_entry.source_stock_entry = source_stock_entry


@frappe.whitelist()
def get_fg_conversion_details(work_order: str):
	from erpnext.stock.doctype.stock_entry.services.manufacturing import (
		get_alternative_finished_goods,
		get_converted_fg_qty,
	)

	if not work_order or not isinstance(work_order, str):
		frappe.throw(_("Invalid Work Order"))

	frappe.has_permission("Work Order", "read", doc=work_order, throw=True)

	wo_details = frappe.db.get_value(
		"Work Order", work_order, ["production_item", "produced_qty"], as_dict=True
	)

	return {
		"alternative_items": get_alternative_finished_goods(wo_details.production_item),
		"available_qty": flt(wo_details.produced_qty) - get_converted_fg_qty(work_order),
	}


@frappe.whitelist()
def make_fg_conversion_entry(work_order: str, item_code: str, qty: float):
	if not (work_order and isinstance(work_order, str) and item_code and isinstance(item_code, str)):
		frappe.throw(_("Invalid Work Order or Item"))

	qty = flt(qty)
	if qty <= 0:
		frappe.throw(_("The qty to convert must be greater than zero."))

	frappe.has_permission("Stock Entry", "create", throw=True)
	frappe.has_permission("Work Order", "read", doc=work_order, throw=True)

	wo_doc = frappe.get_doc("Work Order", work_order)

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = "Repack"
	stock_entry.is_fg_conversion = 1
	stock_entry.work_order = wo_doc.name
	stock_entry.company = wo_doc.company
	stock_entry.set_stock_entry_type()

	stock_entry.append("items", _get_fg_conversion_row(wo_doc.production_item, qty, wo_doc.fg_warehouse))

	target_row = _get_fg_conversion_row(item_code, qty, wo_doc.fg_warehouse, is_target=True)
	stock_entry.append("items", target_row)

	return stock_entry.as_dict()


def _get_fg_conversion_row(item_code, qty, warehouse, is_target=False):
	stock_uom = frappe.get_cached_value("Item", item_code, "stock_uom")
	row = {
		"item_code": item_code,
		"qty": flt(qty),
		"transfer_qty": flt(qty),
		"uom": stock_uom,
		"stock_uom": stock_uom,
		"conversion_factor": 1,
		"use_serial_batch_fields": 1,
	}

	if is_target:
		row.update({"t_warehouse": warehouse, "is_finished_item": 1})
	else:
		row["s_warehouse"] = warehouse

	return row


@frappe.whitelist()
def make_job_card(work_order: str, operations: str | list, parent_bom: str | None = None):
	frappe.has_permission("Job Card", "create", throw=True)

	operations = frappe.parse_json(operations)

	work_order = frappe.get_doc("Work Order", work_order)
	for row in operations:
		row = frappe._dict(row)
		row.update(get_operation_details(row.name, work_order, parent_bom))

		validate_operation_data(row)
		qty = row.get("qty")
		while qty > 0:
			qty = split_qty_based_on_batch_size(work_order, row, qty)
			if row.job_card_qty > 0:
				create_job_card(work_order, row, auto_create=True)


def get_operation_details(name, work_order, parent_bom):
	for row in work_order.operations:
		if row.name == name:
			return {
				"idx": row.idx,
				"workstation": row.workstation,
				"workstation_type": row.workstation_type,
				"source_warehouse": row.source_warehouse,
				"fg_warehouse": row.fg_warehouse,
				"wip_warehouse": row.wip_warehouse,
				"finished_good": row.finished_good,
				"bom_no": row.get("bom_no") or parent_bom,
				"is_subcontracted": row.get("is_subcontracted"),
			}


def split_qty_based_on_batch_size(wo_doc, row, qty):
	if not cint(frappe.db.get_value("Operation", row.operation, "create_job_card_based_on_batch_size")):
		row.batch_size = row.get("qty") or wo_doc.qty

	row.job_card_qty = row.batch_size
	if row.batch_size and qty >= row.batch_size:
		qty -= row.batch_size
	elif qty > 0:
		row.job_card_qty = qty
		qty = 0

	get_serial_nos_for_job_card(row, wo_doc)

	return qty


def get_serial_nos_for_job_card(row, wo_doc):
	if not wo_doc.has_serial_no:
		return

	serial_nos = get_serial_nos_for_work_order(wo_doc.name, wo_doc.production_item)
	used_serial_nos = []
	for d in frappe.get_all(
		"Job Card",
		fields=["serial_no"],
		filters={"docstatus": ("<", 2), "work_order": wo_doc.name, "operation_id": row.name},
	):
		used_serial_nos.extend(get_serial_nos(d.serial_no))

	serial_nos = sorted(list(set(serial_nos) - set(used_serial_nos)))
	row.serial_no = "\n".join(serial_nos[0 : cint(row.job_card_qty)])


def get_serial_nos_for_work_order(work_order, production_item):
	serial_nos = []
	for d in frappe.get_all(
		"Serial No",
		fields=["name"],
		filters={
			"work_order": work_order,
			"item_code": production_item,
		},
	):
		serial_nos.append(d.name)

	return serial_nos


def validate_operation_data(row):
	if flt(row.get("qty")) <= 0:
		frappe.throw(
			_("Quantity to Manufacture can not be zero for the operation {0}").format(
				frappe.bold(row.get("operation"))
			)
		)

	if flt(row.get("qty")) > flt(row.get("pending_qty")):
		frappe.throw(
			_("For operation {0}: Quantity ({1}) can not be greater than pending quantity ({2})").format(
				frappe.bold(row.get("operation")),
				frappe.bold(row.get("qty")),
				frappe.bold(row.get("pending_qty")),
			)
		)


def create_job_card(work_order, row, enable_capacity_planning=False, auto_create=False, schedule_blocks=None):
	doc = frappe.new_doc("Job Card")
	doc.update(_job_card_values(work_order, row))

	if work_order.track_semi_finished_goods or (
		work_order.transfer_material_against == "Job Card" and not work_order.skip_transfer
	):
		doc.get_required_items()

	if work_order.track_semi_finished_goods:
		doc.set_secondary_items()

	if auto_create:
		_auto_create_job_card(doc, row, enable_capacity_planning, schedule_blocks)

	if enable_capacity_planning or schedule_blocks:
		# automatically added scheduling rows shouldn't change status to WIP
		doc.db_set("status", "Open")

	return doc


def _job_card_values(work_order, row):
	qty = row.job_card_qty or work_order.get("qty", 0)
	values = _job_card_core_values(work_order, row, qty)
	values.update(_job_card_warehouse_values(work_order, row, qty))
	return values


def _job_card_core_values(work_order, row, qty):
	return {
		"work_order": work_order.name,
		"workstation_type": row.get("workstation_type"),
		"operation": row.get("operation"),
		"workstation": row.get("workstation"),
		"operation_row_id": cint(row.idx),
		"posting_date": nowdate(),
		"for_quantity": qty,
		"operation_id": row.get("name"),
		"bom_no": work_order.bom_no,
		"project": work_order.project,
		"company": work_order.company,
		"sequence_id": row.get("sequence_id"),
		"hour_rate": row.get("hour_rate"),
	}


def _job_card_warehouse_values(work_order, row, qty):
	if not work_order.skip_transfer or work_order.from_wip_warehouse:
		wip_warehouse = work_order.wip_warehouse or row.get("wip_warehouse")
	else:
		wip_warehouse = work_order.source_warehouse or row.get("source_warehouse")

	return {
		"serial_no": row.get("serial_no"),
		"time_required": (row.get("time_in_mins", 0) / work_order.qty) * qty,
		"source_warehouse": row.get("source_warehouse") or work_order.get("source_warehouse"),
		"target_warehouse": row.get("fg_warehouse") or work_order.get("fg_warehouse"),
		"wip_warehouse": wip_warehouse,
		"skip_material_transfer": row.get("skip_material_transfer"),
		"backflush_from_wip_warehouse": row.get("backflush_from_wip_warehouse"),
		"finished_good": row.get("finished_good"),
		"semi_fg_bom": row.get("bom_no"),
		"is_subcontracted": row.get("is_subcontracted"),
		"batch_split": row.get("batch_split"),
		"weight_per_piece": row.get("weight_per_piece"),
	}


def _auto_create_job_card(doc, row, enable_capacity_planning, schedule_blocks=None):
	doc.flags.ignore_mandatory = True
	if schedule_blocks:
		_apply_schedule_blocks(doc, schedule_blocks)
	elif enable_capacity_planning:
		doc.schedule_time_logs(row)

	doc.insert()
	frappe.msgprint(_("Job card {0} created").format(get_link_to_form("Job Card", doc.name)), alert=True)


def _apply_schedule_blocks(doc, schedule_blocks):
	if schedule_blocks[0].workstation:
		doc.workstation = schedule_blocks[0].workstation

	for block in schedule_blocks:
		doc.append(
			"scheduled_time_logs",
			{
				"from_time": block.from_time,
				"to_time": block.to_time,
				"time_in_mins": flt(block.duration_mins),
			},
		)


def get_work_order_operation_data(work_order, operation, workstation):
	for d in work_order.operations:
		if d.operation == operation and d.workstation == workstation:
			return d


@frappe.whitelist()
def create_pick_list(
	source_name: str, target_doc: str | dict | Document | None = None, for_qty: float | None = None
):
	frappe.has_permission("Pick List", "create", throw=True)

	if for_qty is None:
		for_qty = frappe.parse_json(target_doc or "{}").get("for_qty")

	for_qty = _validated_for_qty(for_qty)
	work_order = frappe.get_doc("Work Order", source_name)
	allocation = _allocate_material_demand(work_order, for_qty / flt(work_order.qty))
	postprocess = partial(_set_pick_list_item_qty, allocation_by_item=allocation)

	doc = get_mapped_doc("Work Order", source_name, _pick_list_mapping(postprocess, allocation), target_doc)
	_validate_material_is_pending(doc.locations)
	doc.purpose = "Material Transfer for Manufacture"
	doc.for_qty = for_qty
	doc.set_item_locations()
	return doc


def _pick_list_mapping(postprocess, allocation):
	return {
		"Work Order": {"doctype": "Pick List", "validation": {"docstatus": ["=", 1]}},
		"Work Order Item": {
			"doctype": "Pick List Item",
			"field_no_map": ["transferred_qty"],
			"postprocess": postprocess,
			"condition": lambda doc: _allocation_key(doc) in allocation,
		},
	}


def _allocate_material_demand(work_order, fraction):
	"""Fraction of each (item, warehouse, operation row) group's requirement, capped
	at the group's proportional share of the item's pending pool."""
	required_by_item = {}
	covered_by_item = {}
	required_by_group = {}
	for row in work_order.required_items:
		required_by_item[row.item_code] = required_by_item.get(row.item_code, 0.0) + flt(row.required_qty)
		covered_by_item.setdefault(
			row.item_code,
			flt(row.transferred_qty) + flt(row.requested_qty) + flt(row.picked_qty),
		)
		key = _allocation_key(row)
		required_by_group[key] = required_by_group.get(key, 0.0) + flt(row.required_qty)

	pending_pool = {
		item_code: required_qty - covered_by_item[item_code]
		for item_code, required_qty in required_by_item.items()
	}

	allocation = {}
	for key, required_qty in required_by_group.items():
		item_code = key[0]
		if required_by_item[item_code] <= 0:
			continue

		pool_share = pending_pool[item_code] * required_qty / required_by_item[item_code]
		qty = min(required_qty * fraction, pool_share)
		if qty > 0:
			allocation[key] = qty
	return allocation


def _allocation_key(row):
	"""Manual rows have no operation_row_id; their operation label splits them."""
	return (row.item_code, row.source_warehouse, cint(row.operation_row_id) or row.operation)


def _merge_allocation_per_item(allocation):
	"""Material Request rejects repeated item codes unless Buying Settings allows them."""
	merged = {}
	key_by_item = {}
	for key, qty in allocation.items():
		item_code = key[0]
		if item_code in key_by_item:
			merged[key_by_item[item_code]] += qty
		else:
			key_by_item[item_code] = key
			merged[key] = qty
	return merged


def _validated_for_qty(for_qty):
	qty = flt(for_qty)
	if not math.isfinite(qty) or qty <= 0:
		frappe.throw(_("Quantity must be greater than zero."))
	return qty


def _validate_material_is_pending(rows):
	if not rows:
		frappe.throw(
			_("All required items have already been transferred, requested or picked."),
			title=_("No Pending Materials"),
		)


def _set_pick_list_item_qty(source, target, source_parent, allocation_by_item):
	qty = allocation_by_item.pop(_allocation_key(source), 0.0)
	if qty <= 0:
		target.delete()
		return

	target.qty = qty
	target.stock_qty = qty
	target.uom = frappe.get_value("Item", source.item_code, "stock_uom")
	target.stock_uom = target.uom
	target.conversion_factor = 1


@frappe.whitelist()
def make_material_request(
	source_name: str, target_doc: str | dict | Document | None = None, for_qty: float | None = None
):
	frappe.has_permission("Material Request", "create", throw=True)

	if for_qty is None and frappe.flags.args:
		for_qty = frappe.flags.args.for_qty

	work_order = frappe.get_doc("Work Order", source_name)
	fraction = 1.0
	if for_qty is not None:
		fraction = _validated_for_qty(for_qty) / flt(work_order.qty)

	allocation = _allocate_material_demand(work_order, fraction)
	if not cint(frappe.db.get_single_value("Buying Settings", "allow_multiple_items")):
		allocation = _merge_allocation_per_item(allocation)
	postprocess = partial(_set_material_request_item, allocation_by_item=allocation)
	doc = get_mapped_doc(
		"Work Order", source_name, _material_request_mapping(postprocess, allocation), target_doc
	)
	_validate_material_is_pending(doc.items)
	doc.material_request_type = "Material Transfer"
	return doc


def _material_request_mapping(postprocess, allocation):
	return {
		"Work Order": {
			"doctype": "Material Request",
			"validation": {"docstatus": ["=", 1]},
			"field_map": {"name": "work_order"},
		},
		"Work Order Item": {
			"doctype": "Material Request Item",
			"field_map": [
				("stock_uom", "uom"),
				("source_warehouse", "from_warehouse"),
			],
			"postprocess": postprocess,
			"condition": lambda doc: _allocation_key(doc) in allocation,
		},
	}


def _set_material_request_item(source, target, source_parent, allocation_by_item):
	qty = allocation_by_item.pop(_allocation_key(source), 0.0)
	if qty <= 0:
		target.delete()
		return

	target.warehouse = source_parent.wip_warehouse
	target.qty = qty
	target.schedule_date = nowdate()


@frappe.whitelist()
def make_stock_return_entry(work_order: str):
	from erpnext.stock.doctype.stock_entry.services.manufacturing import (
		ManufactureStockEntry,
	)

	frappe.has_permission("Stock Entry", "create", throw=True)

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
