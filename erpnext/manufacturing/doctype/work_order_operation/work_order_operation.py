# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrderOperation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_end_time: DF.Datetime | None
		actual_operating_cost: DF.Currency
		actual_operation_time: DF.Float
		actual_start_time: DF.Datetime | None
		backflush_from_wip_warehouse: DF.Check
		batch_size: DF.Float
		batch_split: DF.Check
		bom: DF.Link | None
		bom_operation: DF.Data | None
		bom_no: DF.Link | None
		completed_qty: DF.Float
		description: DF.TextEditor | None
		fg_warehouse: DF.Link | None
		finished_good: DF.Link | None
		hour_rate: DF.Float
		is_subcontracted: DF.Check
		operation: DF.Link
		output_qty_per_unit: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pending_qty: DF.Float
		planned_end_time: DF.Datetime | None
		planned_operating_cost: DF.Currency
		planned_start_time: DF.Datetime | None
		process_loss_qty: DF.Float
		quality_inspection_required: DF.Check
		sequence_id: DF.Int
		skip_material_transfer: DF.Check
		source_warehouse: DF.Link | None
		status: DF.Literal["Pending", "Work in Progress", "Completed"]
		time_in_mins: DF.Float
		weight_per_piece: DF.Float
		wip_warehouse: DF.Link | None
		workstation: DF.Link | None
		workstation_type: DF.Link | None
	# end: auto-generated types

	def get_qty_to_produce(self, work_order_qty):
		"""Output Item qty this operation makes for `work_order_qty` units of the Work Order item."""
		return get_qty_to_produce(work_order_qty, self.output_qty_per_unit)


def get_qty_to_produce(work_order_qty, output_qty_per_unit):
	"""Output Item qty an operation makes for `work_order_qty` units of the Work Order item."""
	precision = frappe.get_precision("Work Order Operation", "completed_qty")
	return flt(flt(work_order_qty) * flt(output_qty_per_unit), precision)


def get_output_qty_per_unit(operation_id):
	"""Output Item qty a Work Order Operation makes per Work Order unit."""
	if not operation_id:
		return 1.0

	output_qty_per_unit = frappe.db.get_value(
		"Work Order Operation", operation_id, "output_qty_per_unit", cache=True
	)
	return flt(output_qty_per_unit) or 1.0


def get_work_order_qty(stock_entry):
	"""`fg_completed_qty` in Work Order units. A Job Card entry counts the operation's Output Item."""
	operation_id = stock_entry.job_card and frappe.db.get_value(
		"Job Card", stock_entry.job_card, "operation_id", cache=True
	)
	return flt(stock_entry.fg_completed_qty) / get_output_qty_per_unit(operation_id)
