# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Material Request planning and creation for a Production Plan.

Consolidates the former ``material_planning``, ``material_request_items`` and
``material_request_helpers`` modules. Also re-exports the planning helpers so
existing imports of ``...services.material_planning`` keep working through here.
"""

import copy
import json
from collections import defaultdict

import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.utils import add_days, ceil, cint, comma_and, flt, get_link_to_form, nowdate
from frappe.utils.csvutils import build_csv_response

from erpnext.manufacturing.doctype.production_plan.services.bom_explosion import (
	get_exploded_items,
	get_subitems,
)
from erpnext.manufacturing.doctype.production_plan.services.planning_queries import (
	get_bin_details,
	get_item_data,
	get_sales_orders,
	get_uom_conversion_factor,
	get_warehouse_list,
	set_default_warehouses,
)
from erpnext.manufacturing.doctype.production_plan.services.sub_assembly_queries import (
	get_raw_materials_of_sub_assembly_items,
	get_sub_assembly_items,
)
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.get_item_details import get_conversion_factor


class MaterialRequestService:
	def __init__(self, doc):
		self.doc = doc

	def validate_mr_subcontracted(self):
		for row in self.doc.mr_items:
			if row.material_request_type != "Subcontracting":
				continue
			if not frappe.db.get_value("Item", row.item_code, "is_sub_contracted_item"):
				frappe.throw(
					_("Item {0} is not a subcontracted item").format(row.item_code),
					title=_("Invalid Item"),
				)

	def make_material_request(self):
		"""Create Material Requests grouped by Sales Order and Material Request Type"""
		self.validate_mr_subcontracted()

		if all(item.requested_qty == item.quantity for item in self.doc.mr_items):
			msgprint(_("All items are already requested"))
			return

		material_request_map = {}
		material_request_list = []
		for item in self.doc.mr_items:
			if item.quantity == item.requested_qty:
				continue
			self._add_item_to_material_request(item, material_request_map, material_request_list)

		self._submit_material_requests(material_request_list)

	def _add_item_to_material_request(self, item, material_request_map, material_request_list):
		item_doc = frappe.get_cached_doc("Item", item.item_code)
		material_request_type = item.material_request_type or item_doc.default_material_request_type

		# key for Sales Order:Material Request Type:Customer
		key = "{}:{}:{}".format(item.sales_order, material_request_type, "")
		if key not in material_request_map:
			material_request_map[key] = self._new_material_request(material_request_type)
			material_request_list.append(material_request_map[key])

		schedule_date = item.schedule_date or add_days(nowdate(), cint(item_doc.lead_time_days))
		row = self._material_request_item(item, material_request_type, schedule_date)
		material_request_map[key].append("items", row)

	def _new_material_request(self, material_request_type):
		mr = frappe.new_doc("Material Request")
		mr.update(
			{
				"transaction_date": nowdate(),
				"status": "Draft",
				"company": self.doc.company,
				"material_request_type": material_request_type,
			}
		)
		return mr

	def _material_request_item(self, item, material_request_type, schedule_date):
		from_warehouse = item.from_warehouse if material_request_type == "Material Transfer" else None
		project = (
			frappe.db.get_value("Sales Order", item.sales_order, "project") if item.sales_order else None
		)
		return {
			"item_code": item.item_code,
			"from_warehouse": from_warehouse,
			"qty": item.quantity - item.requested_qty,
			"uom": item.uom,
			"schedule_date": schedule_date,
			"warehouse": item.warehouse,
			"sales_order": item.sales_order,
			"production_plan": self.doc.name,
			"material_request_plan_item": item.name,
			"project": project,
		}

	def _submit_material_requests(self, material_request_list):
		for material_request in material_request_list:
			material_request.flags.ignore_permissions = 1
			material_request.run_method("set_missing_values")
			material_request.save()
			if self.doc.get("submit_material_request"):
				material_request.submit()

		frappe.flags.mute_messages = False
		if not material_request_list:
			msgprint(_("No material request created"))
			return

		links = [get_link_to_form("Material Request", m.name) for m in material_request_list]
		msgprint(_("{0} created").format(comma_and(links)))


@frappe.whitelist()
def get_items_for_material_requests(
	doc: str | frappe._dict | Document,
	warehouses: str | list | None = None,
	get_parent_warehouse_data: bool | int | None = None,
):
	frappe.has_permission("Production Plan", "read", throw=True)

	doc = _normalize_mr_doc(doc)
	warehouses = _filter_warehouses(doc, warehouses, get_parent_warehouse_data)
	doc["mr_items"] = []

	po_items = _collect_po_items(doc)
	_validate_po_items(po_items)

	ignore_ordered_qty = _effective_ignore_ordered_qty(doc, po_items)
	so_item_details = _collect_item_details(doc, po_items)

	mr_items = _build_mr_items(doc, so_item_details, ignore_ordered_qty)
	mr_items = _apply_other_locations(
		doc, mr_items, warehouses, ignore_ordered_qty, get_parent_warehouse_data
	)

	if not mr_items:
		_warn_no_mr_items(doc)
	return mr_items


def _normalize_mr_doc(doc):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))
	return doc


def _filter_warehouses(doc, warehouses, get_parent_warehouse_data):
	if not warehouses:
		return warehouses

	warehouses = list(set(get_warehouse_list(warehouses)))
	for_warehouse = doc.get("for_warehouse")
	if for_warehouse and not get_parent_warehouse_data and for_warehouse in warehouses:
		warehouses.remove(for_warehouse)
	return warehouses


def _collect_po_items(doc):
	po_items = doc.get("po_items") if doc.get("po_items") else doc.get("items")
	for sa_row in doc.get("sub_assembly_items") or []:
		sa_row = frappe._dict(sa_row)
		if sa_row.type_of_manufacturing != "Material Request":
			continue
		po_items.append(
			frappe._dict(
				{
					"item_code": sa_row.production_item,
					"required_qty": sa_row.qty,
					"include_exploded_items": 0,
				}
			)
		)
	return po_items


def _validate_po_items(po_items):
	if not po_items or not [row.get("item_code") for row in po_items if row.get("item_code")]:
		frappe.throw(
			_("Items to Manufacture are required to pull the Raw Materials associated with it."),
			title=_("Items Required"),
		)


def _effective_ignore_ordered_qty(doc, po_items):
	if doc.get("ignore_existing_ordered_qty"):
		return doc.get("ignore_existing_ordered_qty")
	return any(data.get("ignore_existing_ordered_qty") for data in po_items)


def _build_sub_assembly_map(doc):
	if not (doc.get("skip_available_sub_assembly_item") and doc.get("sub_assembly_items")):
		return {}

	sub_assembly_items = defaultdict(int)
	for d in doc.get("sub_assembly_items"):
		key = (d.get("production_item"), d.get("bom_no"), d.get("type_of_manufacturing"))
		sub_assembly_items[key] += d.get("qty")
	return {k[:2]: v for k, v in sub_assembly_items.items()}


def _collect_item_details(doc, po_items):
	company = doc.get("company")
	sub_assembly_items = _build_sub_assembly_map(doc)
	existing_sub_assembly_items = set()
	so_item_details = frappe._dict()
	qty_precision = frappe.get_precision("Material Request Plan Item", "quantity")

	for data in po_items:
		if not data.get("include_exploded_items") and doc.get("sub_assembly_items"):
			data["include_exploded_items"] = 1
		item_details = _item_details_for_row(
			doc, data, company, sub_assembly_items, existing_sub_assembly_items
		)
		_accumulate_so_items(so_item_details, data.get("sales_order"), item_details, qty_precision)
	return so_item_details


def _item_details_for_row(doc, data, company, sub_assembly_items, existing_sub_assembly_items):
	planned_qty = data.get("required_qty") or data.get("planned_qty")
	if data.get("bom") or data.get("bom_no"):
		return _bom_item_details(
			doc, data, company, planned_qty, sub_assembly_items, existing_sub_assembly_items
		)
	if data.get("item_code"):
		return _plain_item_details(doc, data, planned_qty)
	return {}


def _bom_item_details(doc, data, company, planned_qty, sub_assembly_items, existing_sub_assembly_items):
	bom_no, include_non_stock_items, include_subcontracted_items = _bom_explosion_flags(doc, data)
	if not planned_qty:
		frappe.throw(_("For row {0}: Enter Planned Qty").format(data.get("idx")))
	if not bom_no:
		return {}
	return _explode_bom_items(
		doc,
		data,
		company,
		bom_no,
		planned_qty,
		include_non_stock_items,
		include_subcontracted_items,
		sub_assembly_items,
		existing_sub_assembly_items,
	)


def _bom_explosion_flags(doc, data):
	if data.get("required_qty"):
		include_subcontracted_items = 1 if data.get("include_exploded_items") else 0
		return data.get("bom"), 1, include_subcontracted_items
	return data.get("bom_no"), doc.get("include_non_stock_items"), doc.get("include_subcontracted_items")


def _explode_bom_items(
	doc,
	data,
	company,
	bom_no,
	planned_qty,
	include_non_stock_items,
	include_subcontracted_items,
	sub_assembly_items,
	existing_sub_assembly_items,
):
	item_details = {}
	if (
		data.get("include_exploded_items")
		and doc.get("skip_available_sub_assembly_item")
		and doc.get("sub_assembly_items")
	):
		return get_raw_materials_of_sub_assembly_items(
			existing_sub_assembly_items,
			item_details,
			company,
			bom_no,
			include_non_stock_items,
			sub_assembly_items,
			planned_qty=planned_qty,
		)
	if data.get("include_exploded_items") and include_subcontracted_items:
		return get_exploded_items(
			item_details, company, bom_no, include_non_stock_items, planned_qty=planned_qty, doc=doc
		)
	return get_subitems(
		doc,
		data,
		item_details,
		bom_no,
		company,
		include_non_stock_items,
		include_subcontracted_items,
		1,
		planned_qty=planned_qty,
	)


def _plain_item_details(doc, data, planned_qty):
	item_master = frappe.get_doc("Item", data["item_code"]).as_dict()
	purchase_uom = item_master.purchase_uom or item_master.stock_uom
	conversion_factor = (
		get_uom_conversion_factor(item_master.name, purchase_uom) if item_master.purchase_uom else 1.0
	)
	return {
		item_master.item_code: frappe._dict(
			{
				"item_name": item_master.item_name,
				"default_bom": doc.bom,
				"purchase_uom": purchase_uom,
				"default_warehouse": item_master.default_warehouse,
				"min_order_qty": item_master.min_order_qty,
				"default_material_request_type": item_master.default_material_request_type,
				"qty": planned_qty or 1,
				"is_sub_contracted": item_master.is_sub_contracted_item,
				"item_code": item_master.name,
				"description": item_master.description,
				"stock_uom": item_master.stock_uom,
				"conversion_factor": conversion_factor,
				"safety_stock": item_master.safety_stock,
			}
		)
	}


def _accumulate_so_items(so_item_details, sales_order, item_details, qty_precision):
	for key, details in item_details.items():
		details.qty = flt(details.qty, qty_precision)
		so_item_details.setdefault(sales_order, frappe._dict())
		if key in so_item_details[sales_order]:
			existing = so_item_details[sales_order][key]
			existing["qty"] = existing.get("qty", 0) + flt(details.qty)
		else:
			so_item_details[sales_order][key] = details


def _build_mr_items(doc, so_item_details, ignore_ordered_qty):
	mr_items = []
	consumed_qty = defaultdict(float)
	warehouse = doc.get("for_warehouse")
	company = doc.get("company")
	include_safety_stock = doc.get("include_safety_stock")

	for sales_order, item_dict in so_item_details.items():
		for details in item_dict.values():
			warehouse = warehouse or details.get("source_warehouse") or details.get("default_warehouse")
			row = _mr_item_for_details(
				doc,
				details,
				sales_order,
				company,
				ignore_ordered_qty,
				include_safety_stock,
				warehouse,
				consumed_qty,
			)
			if row:
				mr_items.append(row)
	return mr_items


def _mr_item_for_details(
	doc, details, sales_order, company, ignore_ordered_qty, include_safety_stock, warehouse, consumed_qty
):
	bin_dict = get_bin_details(details, doc.company, warehouse)
	bin_dict = bin_dict[0] if bin_dict else {}
	if details.qty <= 0:
		return None
	return get_material_request_items(
		doc,
		details,
		sales_order,
		company,
		ignore_ordered_qty,
		include_safety_stock,
		warehouse,
		bin_dict,
		consumed_qty,
	)


def _apply_other_locations(doc, mr_items, warehouses, ignore_ordered_qty, get_parent_warehouse_data):
	if not ((ignore_ordered_qty or get_parent_warehouse_data) and warehouses):
		return mr_items

	new_mr_items = []
	for item in mr_items:
		get_materials_from_other_locations(item, warehouses, new_mr_items, doc.get("company"))
	return new_mr_items


def _warn_no_mr_items(doc):
	to_enable = frappe.bold(frappe.get_meta("Production Plan").get_field("ignore_existing_ordered_qty").label)
	warehouse = frappe.bold(doc.get("for_warehouse"))
	message = (
		_(
			"As there are sufficient raw materials, Material Request is not required for Warehouse {0}."
		).format(warehouse)
		+ "<br><br>"
	)
	message += _("If you still want to proceed, please enable {0}.").format(to_enable)
	frappe.msgprint(message, title=_("Note"))


def get_material_request_items(
	doc,
	row,
	sales_order,
	company,
	ignore_existing_ordered_qty,
	include_safety_stock,
	warehouse,
	bin_dict,
	consumed_qty,
):
	required_qty = _required_qty_for_mr(
		doc, row, ignore_existing_ordered_qty, warehouse, bin_dict, consumed_qty
	)
	required_qty = _adjust_required_qty_for_uom(row, required_qty, include_safety_stock)
	item_group_defaults = get_item_group_defaults(row.item_code, company)
	conversion_factor = _mr_purchase_conversion_factor(row)
	return _material_request_item_row(
		row, sales_order, warehouse, bin_dict, required_qty, conversion_factor, item_group_defaults
	)


def _required_qty_for_mr(doc, row, ignore_existing_ordered_qty, warehouse, bin_dict, consumed_qty):
	if not ignore_existing_ordered_qty or bin_dict.get("projected_qty", 0) < 0:
		required_qty = flt(row.get("qty"))
	else:
		key = (row.get("item_code"), warehouse)
		available_qty = flt(bin_dict.get("projected_qty", 0)) - consumed_qty[key]
		if available_qty > 0:
			required_qty = max(0, flt(row.get("qty")) - available_qty)
			consumed_qty[key] += min(flt(row.get("qty")), available_qty)
		else:
			required_qty = flt(row.get("qty"))

	if doc.get("consider_minimum_order_qty") and 0 < required_qty < row["min_order_qty"]:
		required_qty = row["min_order_qty"]
	return required_qty


def _adjust_required_qty_for_uom(row, required_qty, include_safety_stock):
	if not row["purchase_uom"]:
		row["purchase_uom"] = row["stock_uom"]

	if row["purchase_uom"] != row["stock_uom"]:
		if not (row["conversion_factor"] or frappe.flags.show_qty_in_stock_uom):
			frappe.throw(
				_("UOM Conversion factor ({0} -> {1}) not found for item: {2}").format(
					row["purchase_uom"], row["stock_uom"], row.item_code
				)
			)
			required_qty = required_qty / row["conversion_factor"]

	if frappe.db.get_value("UOM", row["purchase_uom"], "must_be_whole_number"):
		required_qty = ceil(required_qty)
	if include_safety_stock:
		required_qty += flt(row["safety_stock"])
	return required_qty


def _mr_purchase_conversion_factor(row):
	item_details = frappe.get_cached_value("Item", row.item_code, ["purchase_uom", "stock_uom"], as_dict=1)
	if (
		row.get("default_material_request_type") == "Purchase"
		and item_details.purchase_uom
		and item_details.purchase_uom != item_details.stock_uom
	):
		return get_conversion_factor(row.item_code, item_details.purchase_uom).get("conversion_factor") or 1.0
	return 1.0


def _material_request_item_row(
	row, sales_order, warehouse, bin_dict, required_qty, conversion_factor, item_group_defaults
):
	warehouse = (
		warehouse
		or row.get("source_warehouse")
		or row.get("default_warehouse")
		or item_group_defaults.get("default_warehouse")
	)
	return {
		"item_code": row.item_code,
		"item_name": row.item_name,
		"quantity": required_qty / conversion_factor,
		"conversion_factor": conversion_factor,
		"required_bom_qty": row.get("qty"),
		"stock_uom": row.get("stock_uom"),
		"warehouse": warehouse,
		"safety_stock": row.safety_stock,
		"actual_qty": bin_dict.get("actual_qty", 0),
		"projected_qty": bin_dict.get("projected_qty", 0),
		"ordered_qty": bin_dict.get("ordered_qty", 0),
		"reserved_qty_for_production": bin_dict.get("reserved_qty_for_production", 0),
		"min_order_qty": row["min_order_qty"],
		"material_request_type": row.get("default_material_request_type"),
		"sales_order": sales_order,
		"description": row.get("description"),
		"uom": row.get("purchase_uom") or row.get("stock_uom"),
		"main_item_code": row.get("main_bom_item"),
		"from_bom": row.get("main_bom"),
	}


def get_materials_from_other_locations(item, warehouses, new_mr_items, company):
	from erpnext.stock.doctype.pick_list.pick_list import get_available_item_locations

	locations = get_available_item_locations(
		item.get("item_code"),
		warehouses,
		item.get("quantity") * item.get("conversion_factor"),
		company,
		ignore_validation=True,
	)

	required_qty = item.get("quantity")
	if item.get("conversion_factor") and item.get("purchase_uom") != item.get("stock_uom"):
		# Convert qty to stock UOM
		required_qty = required_qty * item.get("conversion_factor")

	required_qty = _transfer_from_locations(item, locations, new_mr_items, required_qty)
	_add_remaining_purchase_request(item, new_mr_items, required_qty)


def _transfer_from_locations(item, locations, new_mr_items, required_qty):
	# get available material by transferring to production warehouse
	for d in locations:
		if required_qty <= 0:
			return required_qty

		new_dict = copy.deepcopy(item)
		quantity = required_qty if d.get("qty") > required_qty else d.get("qty")
		new_dict.update(
			{
				"quantity": quantity,
				"material_request_type": "Material Transfer",
				"uom": new_dict.get("stock_uom"),  # internal transfer should be in stock UOM
				"from_warehouse": d.get("warehouse"),
				"conversion_factor": 1.0,
			}
		)
		required_qty -= quantity
		new_mr_items.append(new_dict)
	return required_qty


def _add_remaining_purchase_request(item, new_mr_items, required_qty):
	# raise purchase request for remaining qty
	precision = frappe.get_precision("Material Request Plan Item", "quantity")
	if flt(required_qty, precision) <= 0:
		return

	purchase_uom = frappe.db.get_value("Item", item.get("item_code"), "purchase_uom")
	if frappe.db.get_value("UOM", purchase_uom, "must_be_whole_number"):
		required_qty = ceil(required_qty)

	item["quantity"] = required_qty / item.get("conversion_factor")
	new_mr_items.append(item)


@frappe.whitelist()
def download_raw_materials(doc: str | dict | Document, warehouses: str | list | None = None):
	frappe.has_permission("Production Plan", "read", throw=True)

	doc = _normalize_mr_doc(doc)
	item_list = [_raw_materials_header()]

	doc.warehouse = None
	frappe.flags.show_qty_in_stock_uom = 1
	items = get_items_for_material_requests(doc, warehouses=warehouses, get_parent_warehouse_data=True)

	_build_download_rows(doc, items, item_list)
	build_csv_response(item_list, doc.name)


def _raw_materials_header():
	return [
		"Item Code",
		"Item Name",
		"Description",
		"Stock UOM",
		"Warehouse",
		"Required Qty as per BOM",
		"Projected Qty",
		"Available Qty In Hand",
		"Ordered Qty",
		"Planned Qty",
		"Reserved Qty for Production",
		"Safety Stock",
		"Required Qty",
	]


def _build_download_rows(doc, items, item_list):
	duplicate_item_wh_list = frappe._dict()
	for d in items:
		key = (d.get("item_code"), d.get("warehouse"))
		if key in duplicate_item_wh_list:
			duplicate_item_wh_list[key][12] += d.get("quantity")
			continue

		rm_data = _raw_material_row(d)
		duplicate_item_wh_list[key] = rm_data
		item_list.append(rm_data)

		if not doc.get("for_warehouse"):
			_append_other_warehouse_bins(item_list, d, doc)


def _raw_material_row(d):
	return [
		d.get("item_code"),
		d.get("item_name"),
		d.get("description"),
		d.get("stock_uom"),
		d.get("warehouse"),
		d.get("required_bom_qty"),
		d.get("projected_qty"),
		d.get("actual_qty"),
		d.get("ordered_qty"),
		d.get("planned_qty"),
		d.get("reserved_qty_for_production"),
		d.get("safety_stock"),
		d.get("quantity"),
	]


def _append_other_warehouse_bins(item_list, d, doc):
	row = {"item_code": d.get("item_code")}
	for bin_dict in get_bin_details(row, doc.company, all_warehouse=True):
		if d.get("warehouse") == bin_dict.get("warehouse"):
			continue

		item_list.append(
			[
				"",
				"",
				"",
				bin_dict.get("warehouse"),
				"",
				bin_dict.get("projected_qty", 0),
				bin_dict.get("actual_qty", 0),
				bin_dict.get("ordered_qty", 0),
				bin_dict.get("reserved_qty_for_production", 0),
			]
		)
