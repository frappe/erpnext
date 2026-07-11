# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


from typing import Any

import frappe
import frappe.defaults
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.query_builder import Order
from frappe.query_builder.functions import Min, Sum
from frappe.utils import cint, flt, get_datetime, get_link_to_form, getdate, new_line_sep, nowdate

from erpnext.buying.utils import check_on_hold_or_closed_status, validate_for_items
from erpnext.controllers.buying_controller import BuyingController
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.stock.stock_balance import get_indented_qty, update_bin_qty

from .mapper import (
	get_items_based_on_default_supplier,
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
				already_indented = frappe.get_all(
					"Material Request Item",
					filters={
						"item_code": item,
						"sales_order": so_no,
						"docstatus": 1,
						"parent": ["!=", self.name],
					},
					fields=[{"SUM": "qty", "as": "qty"}],
				)
				already_indented = flt(already_indented[0].qty) if already_indented else 0

				actual_so_qty = frappe.get_all(
					"Sales Order Item",
					filters={"parent": so_no, "item_code": item, "docstatus": 1},
					fields=[{"SUM": "stock_qty", "as": "stock_qty"}],
				)
				actual_so_qty = flt(actual_so_qty[0].stock_qty) if actual_so_qty else 0

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

		if not self.buying_price_list:
			self.buying_price_list = frappe.defaults.get_defaults().buying_price_list

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
		mod_db = frappe.db.get_value("Material Request", self.name, "modified")

		if mod_db and get_datetime(mod_db) != get_datetime(self.modified):
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
									"The total Issue / Transfer quantity {0} in Material Request {1} cannot be greater than allowed requested quantity {2} for Item {3}"
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
def update_status(name: str, status: str):
	material_request = frappe.get_doc("Material Request", name)
	material_request.check_permission("write")
	material_request.update_status(status)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_material_requests_based_on_supplier(
	doctype: Any, txt: str, searchfield: Any, start: int, page_len: int, filters: dict
):
	supplier = filters.get("supplier")
	supplier_items = get_items_based_on_default_supplier(supplier)

	if not supplier_items:
		frappe.throw(_("{0} is not the default supplier for any items.").format(supplier))

	mr = frappe.qb.DocType("Material Request")
	mr_item = frappe.qb.DocType("Material Request Item")

	query = (
		frappe.qb.from_(mr)
		.from_(mr_item)
		.select(mr.name, mr.transaction_date, mr.company)
		.where(
			(mr.name == mr_item.parent)
			& (mr_item.item_code.isin(supplier_items))
			& (mr.material_request_type == "Purchase")
			& (mr.per_ordered < 99.99)
			& (mr.docstatus == 1)
			& (mr.status != "Stopped")
			& (mr.company == filters.get("company"))
		)
		.groupby(mr.name, mr.transaction_date, mr.company)
		.orderby(Min(mr_item.item_code), order=Order.asc)
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


@frappe.whitelist(methods=["POST"])
def raise_work_orders(material_request: str, company: str):
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
			_("Work Order cannot be created for the following reason: <br> {0}").format(new_line_sep(errors))
		)

	return work_orders
