# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Sales Order / Material Request sourcing into Production Plan items (extracted from production_plan.py)."""

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
from frappe.utils import flt, now_datetime
from pypika.terms import ExistsCriterion

from erpnext.manufacturing.doctype.production_plan.services.planning_queries import get_sales_orders
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details


class SalesOrderSourcingService:
	def __init__(self, doc):
		self.doc = doc

	def get_open_sales_orders(self):
		"""Pull sales orders  which are pending to deliver based on criteria selected"""
		open_so = get_sales_orders(self.doc)

		if open_so:
			self.add_so_in_table(open_so)
		else:
			frappe.msgprint(_("Sales orders are not available for production"))

	def add_so_in_table(self, open_so):
		"""Add sales orders in the table"""
		self.doc.set("sales_orders", [])

		for data in open_so:
			self.doc.append(
				"sales_orders",
				{
					"sales_order": data.name,
					"sales_order_date": data.transaction_date,
					"customer": data.customer,
					"grand_total": data.base_grand_total,
				},
			)

	def get_pending_material_requests(self):
		"""Pull Material Requests that are pending based on criteria selected"""
		mr = frappe.qb.DocType("Material Request")
		mr_item = frappe.qb.DocType("Material Request Item")
		query = self._pending_mr_base_query(mr, mr_item)
		query = self._apply_pending_mr_filters(query, mr, mr_item)
		self.add_mr_in_table(query.run(as_dict=True))

	def _pending_mr_base_query(self, mr, mr_item):
		bom = frappe.qb.DocType("BOM")
		bom_exists = ExistsCriterion(
			frappe.qb.from_(bom)
			.select(bom.name)
			.where((bom.item == mr_item.item_code) & (bom.is_active == 1))
		)
		return (
			frappe.qb.from_(mr)
			.from_(mr_item)
			.select(mr.name, mr.transaction_date)
			.distinct()
			.where(
				(mr_item.parent == mr.name)
				& (mr.material_request_type == "Manufacture")
				& (mr.docstatus == 1)
				& (mr.status != "Stopped")
				& (mr.company == self.doc.company)
				& (mr_item.qty > IfNull(mr_item.ordered_qty, 0))
				& bom_exists
			)
		)

	def _apply_pending_mr_filters(self, query, mr, mr_item):
		if self.doc.from_date:
			query = query.where(mr.transaction_date >= self.doc.from_date)
		if self.doc.to_date:
			query = query.where(mr.transaction_date <= self.doc.to_date)
		if self.doc.warehouse:
			query = query.where(mr_item.warehouse == self.doc.warehouse)
		if self.doc.item_code:
			query = query.where(mr_item.item_code == self.doc.item_code)
		return query

	def add_mr_in_table(self, pending_mr):
		"""Add Material Requests in the table"""
		self.doc.set("material_requests", [])

		for data in pending_mr:
			self.doc.append(
				"material_requests",
				{"material_request": data.name, "material_request_date": data.transaction_date},
			)

	def combine_so_items(self):
		if not (self.doc.combine_items and self.doc.po_items and len(self.doc.po_items) > 0):
			self.get_items()
			return

		items = [self._combined_so_item(row) for row in self.doc.po_items]
		self.doc.set("po_items", [])
		self.add_items(items)

	@staticmethod
	def _combined_so_item(row):
		return frappe._dict(
			{
				"parent": row.sales_order,
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"qty": row.pending_qty,
				"pending_qty": row.pending_qty,
				"conversion_factor": 1.0,
				"description": row.description,
				"bom_no": row.bom_no,
			}
		)

	def get_items(self):
		self.doc.set("po_items", [])
		if self.doc.get_items_from == "Sales Order":
			self.get_so_items()
		elif self.doc.get_items_from == "Material Request":
			self.get_mr_items()

	def get_so_mr_list(self, field, table):
		"""Returns a list of Sales Orders or Material Requests from the respective tables"""
		so_mr_list = [d.get(field) for d in self.doc.get(table) if d.get(field)]
		return so_mr_list

	def get_bom_item_condition(self):
		"""Check if Item or if its Template has a BOM."""
		bom_item_condition = None
		has_bom = frappe.db.exists({"doctype": "BOM", "item": self.doc.item_code, "docstatus": 1})

		if not has_bom:
			bom = frappe.qb.DocType("BOM")
			template_item = frappe.db.get_value("Item", self.doc.item_code, ["variant_of"])
			bom_item_condition = bom.item == template_item or None

		return bom_item_condition

	def get_so_items(self):
		# Check for empty table or empty rows
		if not self.doc.get("sales_orders") or not self.get_so_mr_list("sales_order", "sales_orders"):
			frappe.throw(_("Please fill the Sales Orders table"), title=_("Sales Orders Required"))

		so_list = self.get_so_mr_list("sales_order", "sales_orders")
		items = self._so_items(so_list)
		packed_items = self._so_packed_items(so_list)

		self.add_items(items + packed_items)
		self.doc.calculate_total_planned_qty()

	def _so_items(self, so_list):
		bom = frappe.qb.DocType("BOM")
		so_item = frappe.qb.DocType("Sales Order Item")
		items_subquery = frappe.qb.from_(bom).select(bom.name).where(bom.is_active == 1)
		items_query = (
			frappe.qb.from_(so_item)
			.select(*_so_item_columns(so_item))
			.distinct()
			.where(_so_items_filter(so_item, so_list))
		)
		if self.doc.item_code and frappe.db.exists("Item", self.doc.item_code):
			items_query = items_query.where(so_item.item_code == self.doc.item_code)
			items_subquery = items_subquery.where(
				self.get_bom_item_condition() or bom.item == so_item.item_code
			)

		items = items_query.where(ExistsCriterion(items_subquery)).run(as_dict=True)
		_set_so_item_pending_qty(items)
		return items

	def _so_packed_items(self, so_list):
		bom = frappe.qb.DocType("BOM")
		so_item = frappe.qb.DocType("Sales Order Item")
		pi = frappe.qb.DocType("Packed Item")
		query = (
			frappe.qb.from_(so_item)
			.from_(pi)
			.select(*_so_packed_columns(so_item, pi))
			.distinct()
			.where(_so_packed_filter(bom, so_item, pi, so_list))
		)
		if self.doc.item_code:
			query = query.where(so_item.item_code == self.doc.item_code)
		return query.run(as_dict=True)

	def get_mr_items(self):
		# Check for empty table or empty rows
		if not self.doc.get("material_requests") or not self.get_so_mr_list(
			"material_request", "material_requests"
		):
			frappe.throw(_("Please fill the Material Requests table"), title=_("Material Requests Required"))

		mr_list = self.get_so_mr_list("material_request", "material_requests")
		items = self._mr_items(mr_list)
		self.add_items(items)
		self.doc.calculate_total_planned_qty()

	def _mr_items(self, mr_list):
		bom = frappe.qb.DocType("BOM")
		mr_item = frappe.qb.DocType("Material Request Item")
		query = (
			frappe.qb.from_(mr_item)
			.select(*_mr_item_columns(mr_item))
			.distinct()
			.where(_mr_items_filter(bom, mr_item, mr_list))
		)
		if self.doc.item_code:
			query = query.where(mr_item.item_code == self.doc.item_code)
		return query.run(as_dict=True)

	def add_items(self, items):
		refs = {}
		for data in items:
			if not data.pending_qty:
				continue

			item_details = get_item_details(data.item_code, throw=False)
			if self.doc.combine_items:
				self._add_combine_ref(refs, data, item_details)

			bom_no = data.bom_no or item_details and item_details.get("bom_no") or ""
			if not bom_no:
				continue
			self._append_po_item(data, item_details, bom_no)

		if refs:
			self._apply_combined_refs(refs)

	@staticmethod
	def _add_combine_ref(refs, data, item_details):
		bom_no = data.get("bom_no") or item_details.get("bom_no")
		detail = {"sales_order": data.parent, "sales_order_item": data.name, "qty": data.pending_qty}
		if bom_no in refs:
			refs[bom_no]["so_details"].append(detail)
			refs[bom_no]["qty"] += data.pending_qty
			return

		refs[bom_no] = {"qty": data.pending_qty, "po_item_ref": data.name, "so_details": [detail]}

	def _append_po_item(self, data, item_details, bom_no):
		pi = self.doc.append("po_items", self._po_item_values(data, item_details, bom_no))
		pi._set_defaults()

		if self.doc.get_items_from == "Sales Order":
			pi.sales_order = data.parent
			pi.sales_order_item = data.name
			pi.description = data.description
		elif self.doc.get_items_from == "Material Request":
			pi.material_request = data.parent
			pi.material_request_item = data.name
			pi.description = data.description

	@staticmethod
	def _po_item_values(data, item_details, bom_no):
		return {
			"warehouse": data.warehouse,
			"item_code": data.item_code,
			"description": data.description or item_details.description,
			"stock_uom": item_details and item_details.stock_uom or "",
			"bom_no": bom_no,
			"planned_qty": data.pending_qty,
			"pending_qty": data.pending_qty,
			"planned_start_date": now_datetime(),
			"product_bundle_item": data.parent_item,
		}

	def _apply_combined_refs(self, refs):
		for po_item in self.doc.po_items:
			po_item.planned_qty = refs[po_item.bom_no]["qty"]
			po_item.pending_qty = refs[po_item.bom_no]["qty"]
			po_item.sales_order = ""
		self.add_pp_ref(refs)

	def add_pp_ref(self, refs):
		for bom_no in refs:
			for so_detail in refs[bom_no]["so_details"]:
				self.doc.append(
					"prod_plan_references",
					{
						"item_reference": refs[bom_no]["po_item_ref"],
						"sales_order": so_detail["sales_order"],
						"sales_order_item": so_detail["sales_order_item"],
						"qty": so_detail["qty"],
					},
				)


def _so_item_columns(so_item):
	return [
		so_item.parent,
		so_item.item_code,
		so_item.warehouse,
		(so_item.stock_qty - so_item.stock_reserved_qty).as_("qty"),
		so_item.work_order_qty,
		so_item.delivered_qty,
		so_item.conversion_factor,
		so_item.description,
		so_item.name,
		so_item.bom_no,
	]


def _so_items_filter(so_item, so_list):
	return (
		(so_item.parent.isin(so_list))
		& (so_item.docstatus == 1)
		& ((so_item.stock_qty - so_item.stock_reserved_qty) > so_item.work_order_qty)
	)


def _set_so_item_pending_qty(items):
	for item in items:
		item.pending_qty = flt(item.qty) - max(
			item.work_order_qty, flt(item.delivered_qty) * item.conversion_factor, 0
		)


def _so_packed_columns(so_item, pi):
	pending_qty = (
		frappe.qb.terms.Case()
		.when(
			(so_item.work_order_qty > so_item.delivered_qty),
			(((so_item.qty - so_item.work_order_qty) * pi.qty) / so_item.qty),
		)
		.else_(((so_item.qty - so_item.delivered_qty) * pi.qty) / so_item.qty)
	)
	return [
		pi.parent,
		pi.item_code,
		pi.warehouse.as_("warehouse"),
		pending_qty.as_("pending_qty"),
		pi.parent_item,
		pi.description,
		so_item.name,
	]


def _so_packed_filter(bom, so_item, pi, so_list):
	bom_exists = ExistsCriterion(
		frappe.qb.from_(bom).select(bom.name).where((bom.item == pi.item_code) & (bom.is_active == 1))
	)
	pending = ((so_item.work_order_qty > so_item.delivered_qty) & (so_item.qty > so_item.work_order_qty)) | (
		(so_item.work_order_qty <= so_item.delivered_qty) & (so_item.qty > so_item.delivered_qty)
	)
	return (
		(so_item.parent == pi.parent)
		& (so_item.docstatus == 1)
		& (pi.parent_item == so_item.item_code)
		& (so_item.parent.isin(so_list))
		& pending
		& bom_exists
	)


def _mr_item_columns(mr_item):
	return [
		mr_item.parent,
		mr_item.name,
		mr_item.item_code,
		mr_item.warehouse,
		mr_item.description,
		mr_item.bom_no,
		((mr_item.qty - mr_item.ordered_qty) * mr_item.conversion_factor).as_("pending_qty"),
	]


def _mr_items_filter(bom, mr_item, mr_list):
	bom_exists = ExistsCriterion(
		frappe.qb.from_(bom).select(bom.name).where((bom.item == mr_item.item_code) & (bom.is_active == 1))
	)
	return (
		(mr_item.parent.isin(mr_list))
		& (mr_item.docstatus == 1)
		& (mr_item.qty > mr_item.ordered_qty)
		& bom_exists
	)
