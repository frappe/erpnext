# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

QTY_FIELDS = {"production_plan_item": "planned_qty", "production_plan_sub_assembly_item": "qty"}


class ProductionPlanWorkOrderQuantities:
	"""Count submitted Work Orders after unplanned process loss, independently for each plan row."""

	def __init__(self, production_plan):
		self.production_plan = production_plan

	def validate_work_order(self, work_order, *, process_loss_qty=0):
		from erpnext.manufacturing.doctype.production_plan.services.planning_queries import (
			round_up_to_whole_unit,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError

		row = self.lock_plan_row(work_order)

		committed = self.get_committed_quantities(
			exclude_work_order=work_order.name,
			reference_field=row.reference_field,
			reference_name=row.name,
			for_update=True,
		)[row.reference_field].get(row.name, 0)
		allowance = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
		precision = work_order.precision("qty")
		maximum_qty = flt(
			round_up_to_whole_unit(row.order_qty * (1 + allowance / 100) - committed, row.stock_uom),
			precision,
		)
		committed_qty = flt(
			self._get_committed_qty(work_order, process_loss_qty, row.process_loss_percentage), precision
		)
		if committed_qty > maximum_qty:
			frappe.throw(
				_(
					"Row {0} in {1} {2}: Work Order quantity after process loss {3} exceeds the remaining allowed quantity {4}."
				).format(
					row.idx,
					_(row.doctype),
					get_link_to_form("Production Plan", self.production_plan),
					committed_qty,
					max(0, maximum_qty),
				),
				OverProductionError,
				title=_("Production Plan Quantity Exceeded"),
			)

	def lock_plan_row(self, work_order):
		if work_order.production_plan_item and work_order.production_plan_sub_assembly_item:
			frappe.throw(_("Work Order must reference only one Production Plan row."))

		if work_order.production_plan_sub_assembly_item:
			reference_field = "production_plan_sub_assembly_item"
			row_doctype = "Production Plan Sub Assembly Item"
		else:
			reference_field = "production_plan_item"
			row_doctype = "Production Plan Item"

		reference_name = work_order.get(reference_field)
		# Serialize submissions and loss reversals. The submit rollup updates this row.
		row = (
			frappe.db.get_value(
				row_doctype,
				{"name": reference_name, "parent": self.production_plan},
				["name", "idx", QTY_FIELDS[reference_field], "process_loss_percentage", "stock_uom"],
				as_dict=True,
				for_update=True,
			)
			if reference_name
			else None
		)
		if not row:
			frappe.throw(
				_("Work Order must reference a row in Production Plan {0}.").format(
					get_link_to_form("Production Plan", self.production_plan)
				)
			)

		row.reference_field = reference_field
		row.doctype = row_doctype
		row.order_qty = self.get_order_qty(row, reference_field)
		return row

	@staticmethod
	def get_order_qty(row, reference_field):
		"""Work Order quantity a plan row allows. Sub-assembly rows already include their process loss."""
		from erpnext.manufacturing.doctype.production_plan.services.planning_queries import (
			get_qty_before_process_loss,
		)

		qty = flt(row.get(QTY_FIELDS[reference_field]))
		if reference_field == "production_plan_sub_assembly_item":
			return qty
		return get_qty_before_process_loss(qty, row.process_loss_percentage, row.stock_uom)

	def get_pending_quantities(self, plan):
		from erpnext.manufacturing.doctype.production_plan.services.planning_queries import (
			round_up_to_whole_unit,
		)

		committed = self.get_committed_quantities(include_drafts=True)
		precision = frappe.get_precision("Work Order", "qty")
		pending = {}
		for table, reference_field in (
			("po_items", "production_plan_item"),
			("sub_assembly_items", "production_plan_sub_assembly_item"),
		):
			pending[reference_field] = {
				row.name: max(
					0,
					flt(
						round_up_to_whole_unit(
							self.get_order_qty(row, reference_field)
							- committed[reference_field].get(row.name, 0),
							row.stock_uom,
						),
						precision,
					),
				)
				for row in plan.get(table)
				if table == "po_items" or row.type_of_manufacturing == "In House"
			}
		return pending

	def get_committed_quantities(
		self,
		exclude_work_order=None,
		reference_field=None,
		reference_name=None,
		for_update=False,
		include_drafts=False,
	):
		filters = {"production_plan": self.production_plan, "docstatus": ("<", 2) if include_drafts else 1}
		if exclude_work_order:
			filters["name"] = ("!=", exclude_work_order)
		if reference_field:
			filters[reference_field] = reference_name

		# Read rows instead of an aggregate so MariaDB uses a current locking read on submit.
		work_orders = frappe.qb.get_query(
			"Work Order",
			fields=[
				"production_plan_item",
				"production_plan_sub_assembly_item",
				"qty",
				"produced_qty",
				"process_loss_qty",
			],
			filters=filters,
			for_update=for_update,
			order_by="name",
		).run(as_dict=True)
		loss_percentages = self.get_planned_loss_percentages()
		quantities = {
			"production_plan_item": defaultdict(float),
			"production_plan_sub_assembly_item": defaultdict(float),
		}
		for work_order in work_orders:
			field = (
				"production_plan_sub_assembly_item"
				if work_order.production_plan_sub_assembly_item
				else "production_plan_item"
			)
			if work_order.get(field):
				quantities[field][work_order[field]] += self._get_committed_qty(
					work_order,
					work_order.process_loss_qty,
					loss_percentages.get(work_order[field]),
				)
		return quantities

	def get_planned_loss_percentages(self):
		"""Process loss % each plan row already orders for, by row name."""
		loss_percentages = {}
		for doctype in ("Production Plan Item", "Production Plan Sub Assembly Item"):
			loss_percentages.update(
				frappe.get_all(
					doctype,
					filters={"parent": self.production_plan, "process_loss_percentage": (">", 0)},
					fields=["name", "process_loss_percentage"],
					as_list=True,
				)
			)
		return loss_percentages

	def _get_committed_qty(self, work_order, process_loss_qty, planned_loss_percentage):
		from erpnext.manufacturing.doctype.production_plan.services.planning_queries import (
			get_planned_loss_percentage,
		)

		loss_percentage = get_planned_loss_percentage(planned_loss_percentage)
		good_qty = flt(work_order.qty) - max(
			flt(process_loss_qty), flt(work_order.qty) * loss_percentage / 100
		)
		# Count the qty that makes this good output after the planned loss, so a replacement
		# for unplanned loss also covers its own planned loss.
		committed_qty = good_qty / (1 - loss_percentage / 100)
		# Excess loss in existing records must not erase finished goods already produced.
		return max(0, flt(work_order.produced_qty), committed_qty)
