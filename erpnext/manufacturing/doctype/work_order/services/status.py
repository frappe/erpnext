# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Status and quantity-rollup logic for Work Order.

Extracted from work_order.py. ``StatusService`` wraps a Work Order document
(composition); work_order.py keeps thin delegating stubs so the many external
callers (job cards, sales orders, production plans, patches) keep working.
"""

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, get_link_to_form

from erpnext.stock.stock_balance import get_planned_qty, update_bin_qty

_QTY_PURPOSES = (
	("Manufacture", "produced_qty"),
	("Material Transfer for Manufacture", "material_transferred_for_manufacturing"),
	("Material Transfer for Manufacture", "additional_transferred_qty"),
)


class StatusService:
	def __init__(self, doc):
		self.doc = doc

	def validate_work_order_against_so(self):
		from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError

		total_qty = flt(self._ordered_qty_against_so()) + flt(self.doc.qty)
		so_qty = flt(self._so_item_qty()) + flt(self._packed_item_qty())
		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_sales_order")
		)
		if total_qty <= so_qty + (allowance_percentage / 100 * so_qty):
			return

		frappe.throw(
			_("Cannot produce more Item {0} than Sales Order quantity {1} {2}").format(
				get_link_to_form("Item", self.doc.production_item),
				frappe.bold(so_qty),
				frappe.bold(frappe.get_value("Item", self.doc.production_item, "stock_uom")),
			),
			OverProductionError,
		)

	def _ordered_qty_against_so(self):
		wo = frappe.qb.DocType("Work Order")
		return (
			frappe.qb.from_(wo)
			.select(Sum(wo.qty - wo.process_loss_qty))
			.where(
				(wo.production_item == self.doc.production_item)
				& (wo.sales_order == self.doc.sales_order)
				& (wo.docstatus == 1)
				& (wo.status != "Closed")
				& (wo.name != self.doc.name)
			)
		).run()[0][0]

	def _so_item_qty(self):
		so_item = frappe.qb.DocType("Sales Order Item")
		return (
			frappe.qb.from_(so_item)
			.select(Sum(so_item.stock_qty))
			.where(
				(so_item.parent == self.doc.sales_order)
				& (so_item.item_code == self.doc.production_item)
				& (so_item.docstatus == 1)
			)
		).run()[0][0]

	def _packed_item_qty(self):
		packed_item = frappe.qb.DocType("Packed Item")
		return (
			frappe.qb.from_(packed_item)
			.select(Sum(packed_item.qty))
			.where(
				(packed_item.parent == self.doc.sales_order)
				& (packed_item.parenttype == "Sales Order")
				& (packed_item.item_code == self.doc.production_item)
				& (packed_item.docstatus == 1)
			)
		).run()[0][0]

	def update_status(self, status=None):
		"""Update status of work order if unknown"""
		if self.doc.status != "Closed":
			if status not in ["Stopped", "Closed"]:
				status = self.get_status(status)

			if status != self.doc.status:
				self.doc.db_set("status", status)

		self.doc.update_required_items()

		return status or self.doc.status

	def get_status(self, status=None):
		"""Return the status based on stock entries against this work order"""
		status = status or self.doc.status

		if self.doc.docstatus == 0:
			status = "Draft"
		elif self.doc.docstatus == 1:
			status = self._submitted_status(status)
		else:
			status = "Cancelled"

		if self._is_partial_skip_transfer():
			status = "In Process"

		if status != "Completed" and not all(d.status == "Pending" for d in self.doc.operations):
			status = "In Process"

		if status == "Not Started" and self.doc.reserve_stock:
			status = self._reservation_status(status)

		return status

	def _submitted_status(self, status):
		if status in ["Closed", "Stopped"]:
			return status

		status = (
			"In Process"
			if flt(self.doc.material_transferred_for_manufacturing) > 0 or self.doc.skip_transfer
			else "Not Started"
		)
		precision = frappe.get_precision("Work Order", "produced_qty")
		total_qty = flt(self.doc.produced_qty, precision) + flt(self.doc.process_loss_qty, precision)
		if flt(total_qty, precision) >= flt(self.doc.qty, precision):
			status = "Completed"
		return status

	def _is_partial_skip_transfer(self):
		return bool(
			self.doc.skip_transfer
			and self.doc.produced_qty
			and self.doc.qty > (flt(self.doc.produced_qty) + flt(self.doc.process_loss_qty))
		)

	def _reservation_status(self, status):
		for row in self.doc.required_items:
			if not row.stock_reserved_qty:
				continue

			if row.stock_reserved_qty >= row.required_qty:
				status = "Stock Reserved"
			else:
				return "Stock Partially Reserved"
		return status

	def update_work_order_qty(self):
		"""Update Manufactured Qty and Material Transferred for Qty based on Stock Entry"""
		if self.doc.track_semi_finished_goods:
			return

		for purpose, fieldname in _QTY_PURPOSES:
			self._update_qty_for_purpose(purpose, fieldname)

		if self.doc.production_plan:
			self.set_produced_qty_for_sub_assembly_item()
			self.update_production_plan_status()

		if self.doc.additional_transferred_qty:
			self.doc.validate_additional_transferred_qty()

	def _update_qty_for_purpose(self, purpose, fieldname):
		from erpnext.manufacturing.doctype.work_order.work_order import StockOverProductionError

		if self._skip_transfer_purpose(purpose):
			return

		qty = self.get_transferred_or_manufactured_qty(purpose, fieldname)
		completed_qty = self.doc.qty + (self._qty_allowance(purpose) / 100 * self.doc.qty)
		if qty > completed_qty:
			frappe.throw(
				_("{0} ({1}) cannot be greater than planned quantity ({2}) in Work Order {3}").format(
					_(self.doc.meta.get_label(fieldname)), qty, completed_qty, self.doc.name
				),
				StockOverProductionError,
			)

		self.doc.db_set(fieldname, qty)
		self.set_process_loss_qty()
		self._update_produced_qty_in_so()

	def _skip_transfer_purpose(self, purpose):
		return bool(
			purpose == "Material Transfer for Manufacture"
			and self.doc.operations
			and self.doc.transfer_material_against == "Job Card"
		)

	def _qty_allowance(self, purpose):
		allowance = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
		if not allowance and purpose == "Material Transfer for Manufacture":
			allowance = flt(
				frappe.db.get_single_value("Manufacturing Settings", "transfer_extra_materials_percentage")
			)
		return allowance

	def _update_produced_qty_in_so(self):
		from erpnext.selling.doctype.sales_order.sales_order import update_produced_qty_in_so_item

		if (
			self.doc.sales_order
			and self.doc.sales_order_item
			and not self.doc.production_plan_sub_assembly_item
		):
			update_produced_qty_in_so_item(self.doc.sales_order, self.doc.sales_order_item)

	def update_disassembled_qty(self, qty, is_cancel=False):
		if is_cancel:
			self.doc.disassembled_qty = max(0, self.doc.disassembled_qty - qty)
		else:
			if self.doc.docstatus == 1:
				self.doc.disassembled_qty += qty

		if not is_cancel and self.doc.disassembled_qty > self.doc.produced_qty:
			frappe.throw(_("Cannot disassemble more than produced quantity."))

		self.doc.db_set("disassembled_qty", self.doc.disassembled_qty)

	def get_transferred_or_manufactured_qty(self, purpose, fieldname):
		parent = frappe.qb.DocType("Stock Entry")
		is_additional = cint(fieldname == "additional_transferred_qty")
		query = frappe.qb.from_(parent).where(self._stock_entry_filter(parent, purpose, is_additional))

		if purpose == "Manufacture":
			child = frappe.qb.DocType("Stock Entry Detail")
			query = (
				query.join(child)
				.on(parent.name == child.parent)
				.select(Sum(child.transfer_qty))
				.where(child.is_finished_item == 1)
			)
		else:
			query = query.select(Sum(parent.fg_completed_qty))

		return flt(query.run()[0][0])

	def _stock_entry_filter(self, parent, purpose, is_additional):
		return (
			(parent.work_order == self.doc.name)
			& (parent.docstatus == 1)
			& (parent.purpose == purpose)
			& (parent.is_additional_transfer_entry == is_additional)
		)

	def set_process_loss_qty(self):
		table = frappe.qb.DocType("Stock Entry")
		process_loss_qty = (
			frappe.qb.from_(table)
			.select(Sum(table.process_loss_qty))
			.where(
				(table.work_order == self.doc.name)
				& (table.purpose == "Manufacture")
				& (table.docstatus == 1)
			)
		).run()[0][0]

		self.doc.db_set("process_loss_qty", flt(process_loss_qty))

	def update_production_plan_status(self):
		production_plan = frappe.get_doc("Production Plan", self.doc.production_plan)
		produced_qty = 0
		if self.doc.production_plan_item:
			total_qty = frappe.get_all(
				"Work Order",
				fields=[{"SUM": "produced_qty", "as": "produced_qty"}],
				filters={
					"docstatus": 1,
					"production_plan": self.doc.production_plan,
					"production_plan_item": self.doc.production_plan_item,
				},
				as_list=1,
			)

			produced_qty = total_qty[0][0] if total_qty else 0

		self.update_status()
		production_plan.run_method("update_produced_pending_qty", produced_qty, self.doc.production_plan_item)

	def update_planned_qty(self):
		if self.doc.track_semi_finished_goods:
			return

		update_bin_qty(self.doc.production_item, self.doc.fg_warehouse, self._planned_qty_dict())

		if self.doc.material_request:
			mr_obj = frappe.get_doc("Material Request", self.doc.material_request)
			mr_obj.update_requested_qty([self.doc.material_request_item])

	def _planned_qty_dict(self):
		from erpnext.manufacturing.doctype.production_plan.production_plan import (
			get_reserved_qty_for_sub_assembly,
		)

		qty_dict = {"planned_qty": get_planned_qty(self.doc.production_item, self.doc.fg_warehouse)}
		if self.doc.production_plan_sub_assembly_item and self.doc.production_plan:
			qty_dict["reserved_qty_for_production_plan"] = get_reserved_qty_for_sub_assembly(
				self.doc.production_item, self.doc.fg_warehouse
			)
		return qty_dict

	def set_produced_qty_for_sub_assembly_item(self):
		produced_qty = self._sub_assembly_produced_qty()
		frappe.db.set_value(
			"Production Plan Sub Assembly Item",
			self.doc.production_plan_sub_assembly_item,
			"wo_produced_qty",
			produced_qty,
		)

	def _sub_assembly_produced_qty(self):
		table = frappe.qb.DocType("Work Order")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.produced_qty))
			.where(
				(table.production_plan == self.doc.production_plan)
				& (table.production_plan_sub_assembly_item == self.doc.production_plan_sub_assembly_item)
				& (table.docstatus == 1)
			)
		).run()
		return flt(query[0][0]) if query else 0

	def update_ordered_qty(self):
		if not (
			self.doc.production_plan
			and (self.doc.production_plan_item or self.doc.production_plan_sub_assembly_item)
		):
			return

		qty = self._production_plan_ordered_qty()
		if self.doc.production_plan_item:
			frappe.db.set_value("Production Plan Item", self.doc.production_plan_item, "ordered_qty", qty)
		elif self.doc.production_plan_sub_assembly_item:
			field = self.doc.production_plan_sub_assembly_item
			frappe.db.set_value("Production Plan Sub Assembly Item", field, "ordered_qty", qty)

		doc = frappe.get_doc("Production Plan", self.doc.production_plan)
		doc.set_status()
		doc.db_set("status", doc.status)

	def _production_plan_ordered_qty(self):
		table = frappe.qb.DocType("Work Order")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.qty))
			.where((table.production_plan == self.doc.production_plan) & (table.docstatus == 1))
		)
		if self.doc.production_plan_item:
			query = query.where(table.production_plan_item == self.doc.production_plan_item)
		elif self.doc.production_plan_sub_assembly_item:
			query = query.where(
				table.production_plan_sub_assembly_item == self.doc.production_plan_sub_assembly_item
			)

		result = query.run()
		return flt(result[0][0]) if result else 0

	def update_work_order_qty_in_so(self):
		if (
			not self.doc.sales_order and not self.doc.sales_order_item
		) or self.doc.production_plan_sub_assembly_item:
			return

		total_bundle_qty = self._total_bundle_qty()
		work_order_qty = self._sales_order_work_order_qty()
		frappe.db.set_value(
			"Sales Order Item",
			self.doc.sales_order_item,
			"work_order_qty",
			flt(work_order_qty / total_bundle_qty, 2),
		)

	def _sales_order_work_order_qty(self):
		wo = frappe.qb.DocType("Work Order")
		query = (
			frappe.qb.from_(wo)
			.select(Sum(wo.qty))
			.where((wo.sales_order == self.doc.sales_order) & (wo.docstatus == 1) & (wo.status != "Closed"))
		)
		if self.doc.product_bundle_item:
			query = query.where(wo.product_bundle_item == self.doc.product_bundle_item)
		else:
			query = query.where(wo.production_item == self.doc.production_item)

		qty = query.run(as_list=1)
		return qty[0][0] if qty and qty[0][0] else 0

	def update_work_order_qty_in_combined_so(self):
		total_bundle_qty = self._total_bundle_qty()
		prod_plan = frappe.get_doc("Production Plan", self.doc.production_plan)
		item_reference = frappe.get_value(
			"Production Plan Item", self.doc.production_plan_item, "sales_order_item"
		)

		for plan_reference in prod_plan.prod_plan_references:
			if plan_reference.item_reference != item_reference:
				continue

			qty = flt(plan_reference.qty) / total_bundle_qty if self.doc.docstatus == 1 else 0.0
			frappe.db.set_value("Sales Order Item", plan_reference.sales_order_item, "work_order_qty", qty)

	def _total_bundle_qty(self):
		if not self.doc.product_bundle_item:
			return 1

		pbi = frappe.qb.DocType("Product Bundle Item")
		total_bundle_qty = (
			frappe.qb.from_(pbi).select(Sum(pbi.qty)).where(pbi.parent == self.doc.product_bundle_item)
		).run()[0][0]
		# product bundle is 0 (product bundle allows 0 qty for items)
		return total_bundle_qty or 1

	def update_completed_qty_in_material_request(self):
		if self.doc.material_request and self.doc.material_request_item:
			frappe.get_doc("Material Request", self.doc.material_request).update_completed_qty(
				[self.doc.material_request_item]
			)
