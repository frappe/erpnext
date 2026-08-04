# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import json

import frappe
import frappe.defaults
from frappe import _, msgprint
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Order
from frappe.query_builder.functions import Sum
from frappe.utils import (
	cint,
	comma_and,
	cstr,
	flt,
	get_link_to_form,
	getdate,
	new_line_sep,
	nowdate,
)

from erpnext.buying.utils import check_on_hold_or_closed_status, validate_for_items
from erpnext.controllers.buying_controller import BuyingController
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_supplier, get_price_list_rate_for
from erpnext.stock.stock_balance import get_indented_qty, update_bin_qty
from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	get_subcontracting_boms_for_finished_goods,
)

form_grid_templates = {"items": "templates/form_grid/material_request_grid.html"}


class MaterialRequest(BuyingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.material_request_item.material_request_item import MaterialRequestItem

		amended_from: DF.Link | None
		auto_created_via_reorder: DF.Check
		buying_price_list: DF.Link | None
		company: DF.Link
		customer: DF.Link | None
		items: DF.Table[MaterialRequestItem]
		job_card: DF.Link | None
		letter_head: DF.Link | None
		material_request_type: DF.Literal[
			"Purchase",
			"Material Transfer",
			"Material Issue",
			"Manufacture",
			"Subcontracting",
			"Customer Provided",
		]
		naming_series: DF.Literal["MAT-MR-.YYYY.-"]
		per_ordered: DF.Percent
		per_received: DF.Percent
		scan_barcode: DF.Data | None
		schedule_date: DF.Date | None
		select_print_heading: DF.Link | None
		set_from_warehouse: DF.Link | None
		set_warehouse: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Submitted",
			"Stopped",
			"Cancelled",
			"Pending",
			"Partially Ordered",
			"Partially Received",
			"Ordered",
			"Issued",
			"Transferred",
			"Received",
		]
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		title: DF.Data | None
		transaction_date: DF.Date
		transfer_status: DF.Literal["", "Not Started", "In Transit", "Completed"]
		work_order: DF.Link | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Material Request Item",
				"target_dt": "Sales Order Item",
				"target_field": "requested_qty",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "",
				"join_field": "sales_order_item",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
			},
			{
				"source_dt": "Material Request Item",
				"target_dt": "Packed Item",
				"target_field": "requested_qty",
				"target_parent_dt": "Sales Order",
				"join_field": "packed_item",
				"target_ref_field": "qty",
				"source_field": "qty",
			},
		]

	def check_if_already_pulled(self):
		pass

	def validate_qty_against_so(self):
		so_items = {}  # Format --> {'SO/00001': {'Item/001': 120, 'Item/002': 24}}
		for d in self.get("items"):
			if d.sales_order:
				if d.sales_order not in so_items:
					so_items[d.sales_order] = {d.item_code: flt(d.qty)}
				else:
					if d.item_code not in so_items[d.sales_order]:
						so_items[d.sales_order][d.item_code] = flt(d.qty)
					else:
						so_items[d.sales_order][d.item_code] += flt(d.qty)

		for so_no in so_items.keys():
			for item in so_items[so_no].keys():
				already_indented = frappe.db.sql(
					"""select sum(qty)
					from `tabMaterial Request Item`
					where item_code = %s and sales_order = %s and
					docstatus = 1 and parent != %s""",
					(item, so_no, self.name),
				)
				already_indented = already_indented and flt(already_indented[0][0]) or 0

				actual_so_qty = frappe.db.sql(
					"""select sum(stock_qty) from `tabSales Order Item`
					where parent = %s and item_code = %s and docstatus = 1""",
					(so_no, item),
				)
				actual_so_qty = actual_so_qty and flt(actual_so_qty[0][0]) or 0

				if actual_so_qty and (flt(so_items[so_no][item]) + already_indented > actual_so_qty):
					frappe.throw(
						_(
							"Material Request of maximum {0} can be made for Item {1} against Sales Order {2}"
						).format(actual_so_qty - already_indented, item, so_no)
					)

	def validate(self):
		super().validate()

		self.validate_schedule_date()
		self.check_for_on_hold_or_closed_status("Sales Order", "sales_order")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_material_request_type()

		if not self.status:
			self.status = "Draft"

		from erpnext.controllers.status_updater import validate_status

		validate_status(
			self.status,
			[
				"Draft",
				"Submitted",
				"Stopped",
				"Cancelled",
				"Pending",
				"Partially Ordered",
				"Ordered",
				"Issued",
				"Transferred",
				"Received",
			],
		)

		validate_for_items(self)

		self.set_title()
		# self.validate_qty_against_so()
		# NOTE: Since Item BOM and FG quantities are combined, using current data, it cannot be validated
		# Though the creation of Material Request from a Production Plan can be rethought to fix this

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("set_from_warehouse", "items", "from_warehouse")

		self.validate_pp_qty()

		if self.buying_price_list and not frappe.get_value("Price List", self.buying_price_list, "buying"):
			self.buying_price_list = None

		if not self.buying_price_list:
			buying_price_list = frappe.defaults.get_defaults().buying_price_list
			if frappe.has_permission("Price List", "read", buying_price_list):
				self.buying_price_list = buying_price_list

	def on_update(self):
		if not self.is_new() and self.buying_price_list and self.has_value_changed("buying_price_list"):
			self.update_item_rates()

	def update_item_rates(self):
		price_not_uom_dependent = frappe.get_value(
			"Price List", self.buying_price_list, "price_not_uom_dependent"
		)
		for item in self.items:
			rate = get_price_list_rate_for(
				frappe._dict(
					{
						"price_list": self.buying_price_list,
						"uom": item.uom,
						"transaction_date": self.transaction_date,
						"qty": item.qty,
						"stock_uom": item.stock_uom,
						"conversion_factor": item.conversion_factor,
						"price_list_uom_dependant": price_not_uom_dependent,
					}
				),
				item.item_code,
			)
			if rate is not None:
				item.db_set({"rate": rate, "amount": flt(rate * item.qty, item.precision("amount"))})

		frappe.msgprint(
			_("Item rates have been updated based on the selected Buying Price List {0}").format(
				self.buying_price_list
			),
			alert=True,
		)

	def validate_pp_qty(self):
		items_from_pp = [item for item in self.items if item.material_request_plan_item]
		if items_from_pp:
			items_mr_plan_items = [item.material_request_plan_item for item in items_from_pp]
			table = frappe.qb.DocType("Material Request Plan Item")
			query = (
				frappe.qb.from_(table)
				.select(table.name, (table.quantity - table.requested_qty).as_("available_qty"))
				.where(table.name.isin(items_mr_plan_items))
			)
			result = query.run(as_dict=True)

			for item in items_from_pp:
				row = next(r for r in result if r.name == item.material_request_plan_item)
				if item.qty > row.available_qty:
					frappe.throw(
						_("Quantity cannot be greater than {0} for Item {1}").format(
							row.available_qty, item.item_code
						)
					)

	def before_update_after_submit(self):
		self.validate_schedule_date()

	def validate_material_request_type(self):
		"""Validate fields in accordance with selected type"""

		if self.material_request_type != "Customer Provided":
			self.customer = None

	def set_title(self):
		"""Set title as comma separated list of items"""
		if not self.title:
			items = ", ".join([d.item_name for d in self.items][:3])
			self.title = _("{0} Request for {1}").format(_(self.material_request_type), items)[:100]

	def on_submit(self):
		self.update_requested_qty_in_production_plan()
		self.update_requested_qty()
		if self.material_request_type == "Purchase":
			self.update_prevdoc_status()
			if frappe.db.exists("Budget", {"applicable_on_material_request": 1, "docstatus": 1}):
				self.validate_budget()

	def before_save(self):
		self.set_status(update=True)

	def before_submit(self):
		self.set_status(update=True)

	def before_cancel(self):
		# if MRQ is already closed, no point saving the document
		check_on_hold_or_closed_status(self.doctype, self.name)

		self.set_status(update=True, status="Cancelled")

	def check_modified_date(self):
		mod_db = frappe.db.sql("""select modified from `tabMaterial Request` where name = %s""", self.name)
		date_diff = frappe.db.sql("""select TIMEDIFF(%s, %s)""", (mod_db[0][0], cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(_(self.doctype), self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.status_can_change(status)
		self.set_status(update=True, status=status)
		self.update_requested_qty()

	def status_can_change(self, status):
		"""
		validates that `status` is acceptable for the present controller status
		and throws an Exception if otherwise.
		"""
		if self.status and self.status == "Cancelled":
			# cancelled documents cannot change
			if status != self.status:
				frappe.throw(
					_("{0} {1} is cancelled so the action cannot be completed").format(
						_(self.doctype), self.name
					),
					frappe.InvalidStatusError,
				)

		elif self.status and self.status == "Draft":
			# draft document to pending only
			if status != "Pending":
				frappe.throw(
					_("{0} {1} has not been submitted so the action cannot be completed").format(
						_(self.doctype), self.name
					),
					frappe.InvalidStatusError,
				)

	def on_cancel(self):
		self.update_requested_qty_in_production_plan(cancel=True)
		self.update_requested_qty()
		if self.material_request_type == "Purchase":
			self.update_prevdoc_status()

	def get_mr_items_ordered_qty(self, mr_items):
		mr_items_ordered_qty = {}
		mr_items = [d.name for d in self.get("items") if d.name in mr_items]

		doctype = qty_field = None
		if self.material_request_type in ("Material Issue", "Material Transfer", "Customer Provided"):
			doctype = frappe.qb.DocType("Stock Entry Detail")
			qty_field = doctype.transfer_qty
		elif self.material_request_type == "Manufacture":
			doctype = frappe.qb.DocType("Work Order")
			qty_field = doctype.qty

		if doctype and qty_field:
			query = (
				frappe.qb.from_(doctype)
				.select(doctype.material_request_item, Sum(qty_field))
				.where(
					(doctype.material_request == self.name)
					& (doctype.material_request_item.isin(mr_items))
					& (doctype.docstatus == 1)
				)
				.groupby(doctype.material_request_item)
			)

			if self.material_request_type == "Manufacture":
				query = query.where(doctype.status != "Closed")

			mr_items_ordered_qty = frappe._dict(query.run())

		return mr_items_ordered_qty

	def update_completed_qty(self, mr_items=None, update_modified=True):
		if self.material_request_type == "Purchase":
			return

		if not mr_items:
			mr_items = [d.name for d in self.get("items")]

		mr_items_ordered_qty = self.get_mr_items_ordered_qty(mr_items)
		mr_qty_allowance = frappe.db.get_single_value("Stock Settings", "mr_qty_allowance")

		for d in self.get("items"):
			precision = d.precision("ordered_qty")
			if d.name in mr_items:
				if self.material_request_type in ("Material Issue", "Material Transfer", "Customer Provided"):
					d.ordered_qty = flt(mr_items_ordered_qty.get(d.name))

					if mr_qty_allowance:
						allowed_qty = flt(
							(d.stock_qty + (d.stock_qty * (mr_qty_allowance / 100))),
							d.precision("ordered_qty"),
						)

						if d.ordered_qty and flt(d.ordered_qty, precision) > flt(allowed_qty, precision):
							frappe.throw(
								_(
									"The total Issue / Transfer quantity {0} in Material Request {1}  cannot be greater than allowed requested quantity {2} for Item {3}"
								).format(d.ordered_qty, d.parent, allowed_qty, d.item_code)
							)

					elif d.ordered_qty and flt(d.ordered_qty, precision) > flt(d.stock_qty, precision):
						frappe.throw(
							_(
								"The total Issue / Transfer quantity {0} in Material Request {1} cannot be greater than requested quantity {2} for Item {3}"
							).format(d.ordered_qty, d.parent, d.qty, d.item_code)
						)

				elif self.material_request_type == "Manufacture":
					d.ordered_qty = flt(mr_items_ordered_qty.get(d.name))

				frappe.db.set_value(d.doctype, d.name, "ordered_qty", d.ordered_qty)

		self._update_percent_field(
			{
				"target_dt": "Material Request Item",
				"target_parent_dt": self.doctype,
				"target_parent_field": "per_ordered",
				"target_ref_field": "stock_qty",
				"target_field": "ordered_qty",
				"name": self.name,
			},
			update_modified,
		)

	def update_requested_qty(self, mr_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []
		for d in self.get("items"):
			if (
				(not mr_item_rows or d.name in mr_item_rows)
				and [d.item_code, d.warehouse] not in item_wh_list
				and d.warehouse
				and frappe.db.get_value("Item", d.item_code, "is_stock_item") == 1
			):
				item_wh_list.append([d.item_code, d.warehouse])

		for item_code, warehouse in item_wh_list:
			update_bin_qty(
				item_code,
				warehouse,
				{
					"indented_qty": get_indented_qty(item_code, warehouse),
				},
			)

	def update_requested_qty_in_production_plan(self, cancel=False):
		production_plans = []
		for d in self.get("items"):
			if d.production_plan and d.material_request_plan_item:
				requested_qty = frappe.get_value(
					"Material Request Plan Item", d.material_request_plan_item, "requested_qty"
				)
				qty = (requested_qty + d.qty) if not cancel else (requested_qty - d.qty)
				frappe.db.set_value(
					"Material Request Plan Item", d.material_request_plan_item, "requested_qty", qty
				)

				if d.production_plan not in production_plans:
					production_plans.append(d.production_plan)

		for production_plan in production_plans:
			doc = frappe.get_doc("Production Plan", production_plan)
			doc.set_status()
			doc.db_set("status", doc.status)


def update_completed_and_requested_qty(stock_entry, method):
	if stock_entry.doctype == "Stock Entry":
		material_request_map = {}

		for d in stock_entry.get("items"):
			if d.material_request:
				material_request_map.setdefault(d.material_request, []).append(d.material_request_item)

		for mr, mr_item_rows in material_request_map.items():
			if mr and mr_item_rows:
				mr_obj = frappe.get_doc("Material Request", mr)

				if mr_obj.status in ["Stopped", "Cancelled"]:
					frappe.throw(
						_("{0} {1} is cancelled or stopped").format(_("Material Request"), mr),
						frappe.InvalidStatusError,
					)

				mr_obj.update_completed_qty(mr_item_rows)
				mr_obj.update_requested_qty(mr_item_rows)


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


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Material Request"),
			"list_template": "templates/includes/list/list.html",
		}
	)

	return list_context


@frappe.whitelist()
def update_status(name, status):
	material_request = frappe.get_doc("Material Request", name)
	material_request.check_permission("write")
	material_request.update_status(status)


@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None):
	if args is None:
		args = frappe.flags.args or {}
	if isinstance(args, str):
		args = json.loads(args)

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
def make_request_for_quotation(source_name, target_doc=None):
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
def make_purchase_order_based_on_supplier(source_name, target_doc=None, args=None):
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
def get_items_based_on_default_supplier(supplier):
	supplier_items = [
		d.parent
		for d in frappe.db.get_all(
			"Item Default", {"default_supplier": supplier, "parenttype": "Item"}, "parent"
		)
	]

	return supplier_items


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_material_requests_based_on_supplier(doctype, txt, searchfield, start, page_len, filters):
	supplier = filters.get("supplier")
	supplier_items = get_items_based_on_default_supplier(supplier)

	if not supplier_items:
		frappe.throw(_("{0} is not the default supplier for any items.").format(supplier))

	mr = frappe.qb.DocType("Material Request")
	mr_item = frappe.qb.DocType("Material Request Item")

	query = (
		frappe.qb.from_(mr)
		.from_(mr_item)
		.select(mr.name)
		.distinct()
		.select(mr.transaction_date, mr.company)
		.where(
			(mr.name == mr_item.parent)
			& (mr_item.item_code.isin(supplier_items))
			& (mr.material_request_type == "Purchase")
			& (mr.per_ordered < 99.99)
			& (mr.docstatus == 1)
			& (mr.status != "Stopped")
			& (mr.company == filters.get("company"))
		)
		.orderby(mr_item.item_code, order=Order.asc)
		.limit(cint(page_len))
		.offset(cint(start))
	)

	if txt:
		query = query.where(mr.name.like(f"%%{txt}%%"))

	if filters.get("transaction_date"):
		date = filters.get("transaction_date")[1]
		query = query.where(mr.transaction_date[date[0] : date[1]])

	material_requests = query.run(as_dict=True)

	return material_requests


@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
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
def make_stock_entry(source_name: str, target_doc: str | dict | None = None):
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
		target.set_job_card_data()

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
def raise_work_orders(material_request, company):
	mr = frappe.get_doc("Material Request", material_request)
	errors = []
	work_orders = []
	default_wip_warehouse = frappe.get_cached_value("Company", company, "default_wip_warehouse")

	for d in mr.items:
		if (d.stock_qty - d.ordered_qty) > 0:
			if frappe.db.exists("BOM", {"item": d.item_code, "is_default": 1, "is_active": 1}) or (
				(variant_of := frappe.get_value("Item", d.item_code, "variant_of"))
				and frappe.db.exists("BOM", {"item": variant_of, "is_default": 1, "is_active": 1})
			):
				wo_order = frappe.new_doc("Work Order")
				wo_order.update(
					{
						"production_item": d.item_code,
						"qty": d.stock_qty - d.ordered_qty,
						"fg_warehouse": d.warehouse,
						"wip_warehouse": default_wip_warehouse,
						"description": d.description,
						"stock_uom": d.stock_uom,
						"expected_delivery_date": d.schedule_date,
						"sales_order": d.sales_order,
						"sales_order_item": d.get("sales_order_item"),
						"bom_no": get_item_details(d.item_code).bom_no,
						"material_request": mr.name,
						"material_request_item": d.name,
						"planned_start_date": mr.transaction_date,
						"company": mr.company,
						"project": d.project,
					}
				)

				wo_order.get_items_and_operations_from_bom()
				wo_order.flags.ignore_validate = True
				wo_order.flags.ignore_mandatory = True
				wo_order.save()

				work_orders.append(wo_order.name)
			else:
				errors.append(
					_("Row {0}: Bill of Materials not found for the Item {1}").format(
						d.idx, get_link_to_form("Item", d.item_code)
					)
				)

	if work_orders:
		work_orders_list = [get_link_to_form("Work Order", d) for d in work_orders]

		if len(work_orders) > 1:
			msgprint(
				_("The following {0} were created: {1}").format(
					frappe.bold(_("Work Orders")), "<br>" + ", ".join(work_orders_list)
				)
			)
		else:
			msgprint(
				_("The {0} {1} created successfully").format(
					frappe.bold(_("Work Order")), work_orders_list[0]
				)
			)

	if errors:
		frappe.throw(
			_("Work Order cannot be created for following reason: <br> {0}").format(new_line_sep(errors))
		)

	return work_orders


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
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
def make_in_transit_stock_entry(source_name, in_transit_warehouse):
	ste_doc = make_stock_entry(source_name)
	ste_doc.add_to_transit = 1
	ste_doc.to_warehouse = in_transit_warehouse

	for row in ste_doc.items:
		row.t_warehouse = in_transit_warehouse

	return ste_doc
