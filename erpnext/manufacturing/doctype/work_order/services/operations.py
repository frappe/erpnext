# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Operation scheduling, costing and job-card preparation for Work Order.

Extracted from work_order.py. ``OperationsService`` wraps a Work Order document
(composition); work_order.py keeps thin delegating stubs for the methods that
are called from other modules.
"""

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import (
	cint,
	date_diff,
	flt,
	get_datetime,
	get_link_to_form,
	getdate,
	time_diff_in_hours,
)

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_mins_between_operations,
)
from erpnext.manufacturing.doctype.work_order.mapper import (
	create_job_card,
	split_qty_based_on_batch_size,
)

_BOM_OPERATION_FIELDS = [
	"operation",
	"description",
	"workstation",
	"idx",
	"finished_good",
	"is_subcontracted",
	"wip_warehouse",
	"source_warehouse",
	"fg_warehouse",
	"workstation_type",
	"base_hour_rate as hour_rate",
	"time_in_mins",
	"parent as bom",
	"bom_no",
	"batch_size",
	"sequence_id",
	"fixed_time",
	"skip_material_transfer",
	"backflush_from_wip_warehouse",
	"set_cost_based_on_bom_qty",
	"quality_inspection_required",
]


class OperationsService:
	def __init__(self, doc):
		self.doc = doc

	def calculate_operating_cost(self):
		self.doc.planned_operating_cost, self.doc.actual_operating_cost = 0.0, 0.0
		for d in self.doc.get("operations"):
			self._set_operation_cost(d)
			self.doc.planned_operating_cost += flt(d.planned_operating_cost)
			self.doc.actual_operating_cost += flt(d.actual_operating_cost)

		variable_cost = self.doc.actual_operating_cost or self.doc.planned_operating_cost
		self.doc.total_operating_cost = (
			flt(self.doc.additional_operating_cost)
			+ flt(variable_cost)
			+ flt(self.doc.corrective_operation_cost)
		)

	@staticmethod
	def _set_operation_cost(d):
		if not d.hour_rate and d.workstation:
			d.hour_rate = get_hour_rate(d.workstation)

		d.planned_operating_cost = flt(
			flt(d.hour_rate) * (flt(d.time_in_mins) / 60.0), d.precision("planned_operating_cost")
		)
		d.actual_operating_cost = flt(
			flt(d.hour_rate) * (flt(d.actual_operation_time) / 60.0), d.precision("actual_operating_cost")
		)

	def create_job_card(self):
		manufacturing_settings_doc = frappe.get_doc("Manufacturing Settings")

		enable_capacity_planning = not cint(manufacturing_settings_doc.disable_capacity_planning)
		plan_days = cint(manufacturing_settings_doc.capacity_planning_for_days) or 30

		for idx, row in enumerate(self.doc.operations):
			qty = self.doc.qty
			while qty > 0:
				qty = split_qty_based_on_batch_size(self.doc, row, qty)
				if row.job_card_qty > 0:
					self.prepare_data_for_job_card(row, idx, plan_days, enable_capacity_planning)

		planned_end_date = self.doc.operations and self.doc.operations[-1].planned_end_time
		if planned_end_date:
			self.doc.db_set("planned_end_date", planned_end_date)

	def prepare_data_for_job_card(self, row, idx, plan_days, enable_capacity_planning):
		self.set_operation_start_end_time(row, idx)

		job_card_doc = create_job_card(
			self.doc, row, auto_create=True, enable_capacity_planning=enable_capacity_planning
		)

		if enable_capacity_planning and job_card_doc:
			row.planned_start_time = job_card_doc.scheduled_time_logs[-1].from_time
			row.planned_end_time = job_card_doc.scheduled_time_logs[-1].to_time
			self._validate_capacity_window(row, plan_days)
			row.db_update()

	def _validate_capacity_window(self, row, plan_days):
		from erpnext.manufacturing.doctype.work_order.work_order import CapacityError

		if date_diff(row.planned_end_time, self.doc.planned_start_date) <= plan_days:
			return

		frappe.message_log.pop()
		msg = _(
			"Unable to find the time slot in the next {0} days for the operation {1}. Please increase the 'Capacity Planning For (Days)' in the {2}."
		).format(
			plan_days, row.operation, get_link_to_form("Manufacturing Settings", "Manufacturing Settings")
		)
		frappe.throw(msg, CapacityError)

	def set_operation_start_end_time(self, row, idx):
		"""Set start and end time for given operation. If first operation, set start as
		`planned_start_date`, else add time diff to end time of earlier operation."""
		if idx == 0:
			# first operation at planned_start date
			row.planned_start_time = self.doc.planned_start_date
		elif self.doc.operations[idx - 1].sequence_id:
			row.planned_start_time = self._sequence_based_start_time(row, idx)
		else:
			previous_end = get_datetime(self.doc.operations[idx - 1].planned_end_time)
			row.planned_start_time = previous_end + get_mins_between_operations()

		row.planned_end_time = get_datetime(row.planned_start_time) + relativedelta(minutes=row.time_in_mins)

		if row.planned_start_time == row.planned_end_time:
			frappe.throw(_("Capacity Planning Error, planned start time can not be same as end time"))

	def _sequence_based_start_time(self, row, idx):
		previous = self.doc.operations[idx - 1]
		if previous.sequence_id == row.sequence_id:
			return previous.planned_start_time

		same_sequence = sorted(
			[op for op in self.doc.operations if op.sequence_id == previous.sequence_id],
			key=lambda op: get_datetime(op.planned_end_time),
		)
		return get_datetime(same_sequence[-1].planned_end_time) + get_mins_between_operations()

	def set_work_order_operations(self):
		"""Fetch operations from BOM and set in 'Work Order'"""
		self.doc.set("operations", [])
		if not self.doc.bom_no or not frappe.get_cached_value("BOM", self.doc.bom_no, "with_operations"):
			return

		operations = self._collect_bom_operations()
		for correct_index, operation in enumerate(operations, start=1):
			operation.idx = correct_index

		self.doc.set("operations", operations)
		self.calculate_time()
		self.set_operation_warehouses()

	def set_operation_warehouses(self):
		"""For semi-finished goods tracking, default each operation's warehouses from the Work
		Order and chain them: the first operation pulls from the WO source warehouse and every
		later operation pulls from the previous operation's output; intermediate outputs go to the
		WIP warehouse while the final operation outputs to the WO finished goods warehouse.

		Only empty fields are filled, so values configured on the BOM/operation are preserved."""
		if not self.doc.track_semi_finished_goods or not self.doc.operations:
			return

		operations = self.doc.operations
		last_idx = len(operations) - 1
		for idx, op in enumerate(operations):
			if not op.source_warehouse:
				op.source_warehouse = self.doc.source_warehouse

			if not op.fg_warehouse:
				op.fg_warehouse = self.doc.fg_warehouse if idx == last_idx else self.doc.source_warehouse

			if not op.wip_warehouse:
				op.wip_warehouse = self.doc.wip_warehouse

	def _collect_bom_operations(self):
		operations = []
		if self.doc.use_multi_level_bom:
			bom_tree = frappe.get_doc("BOM", self.doc.bom_no).get_tree_representation()
			for node in reversed(bom_tree.level_order_traversal()):
				if node.is_bom:
					qty = node.exploded_qty / node.bom_qty
					operations.extend(self._bom_operations(node.name, qty=qty, exploded=True))

		bom_qty = frappe.get_cached_value("BOM", self.doc.bom_no, "quantity")
		operations.extend(self._bom_operations(self.doc.bom_no, qty=bom_qty))
		return operations

	def _bom_operations(self, bom_no, qty=1, exploded=False):
		data = frappe.get_all(
			"BOM Operation", filters={"parent": bom_no}, fields=_BOM_OPERATION_FIELDS, order_by="idx"
		)
		for d in data:
			self._adjust_operation_row(d, qty, exploded)
		return data

	def _adjust_operation_row(self, d, qty, exploded):
		if not d.fixed_time:
			if frappe.get_value("Operation", d.operation, "create_job_card_based_on_batch_size"):
				qty = d.batch_size
			d.time_in_mins = d.time_in_mins * flt(qty) if exploded else d.time_in_mins / flt(qty)

		d.status = "Pending"
		if self.doc.track_semi_finished_goods and not d.sequence_id:
			d.sequence_id = d.idx

	def calculate_time(self):
		for d in self.doc.get("operations"):
			if not d.fixed_time:
				d.time_in_mins = flt(d.time_in_mins) * flt(self.doc.qty)

		self.calculate_operating_cost()

	def get_holidays(self, workstation):
		holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")

		holidays = {}

		if holiday_list not in holidays:
			holiday_list_days = [
				getdate(d[0])
				for d in frappe.get_all(
					"Holiday",
					fields=["holiday_date"],
					filters={"parent": holiday_list},
					order_by="holiday_date",
					limit_page_length=0,
					as_list=1,
				)
			]

			holidays[holiday_list] = holiday_list_days

		return holidays[holiday_list]

	def update_operation_status(self):
		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
		max_allowed_qty_for_wo = flt(self.doc.qty) + (allowance_percentage / 100 * flt(self.doc.qty))

		for d in self.doc.get("operations"):
			d.status = self._operation_status(d, max_allowed_qty_for_wo)

	def _operation_status(self, d, max_allowed_qty_for_wo):
		precision = d.precision("completed_qty")
		qty = flt(flt(d.completed_qty, precision) + flt(d.process_loss_qty, precision), precision)
		if not qty:
			return "Pending"
		if qty < flt(self.doc.qty, precision):
			return "Work in Progress"
		if qty <= flt(max_allowed_qty_for_wo, precision):
			return "Completed"
		frappe.throw(_("Completed Qty cannot be greater than 'Qty to Manufacture'"))

	def set_actual_dates(self):
		if self.doc.get("operations"):
			self._set_dates_from_operations()
		else:
			self._set_dates_from_stock_entries()

		self.set_lead_time()

	def _set_dates_from_operations(self):
		operations = self.doc.get("operations")
		start_dates = [d.actual_start_time for d in operations if d.actual_start_time]
		if start_dates:
			self.doc.actual_start_date = min(start_dates)

		end_dates = [d.actual_end_time for d in operations if d.actual_end_time]
		if end_dates:
			self.doc.actual_end_date = max(end_dates)

	def _set_dates_from_stock_entries(self):
		# {"TIMESTAMP": [...]} renders MySQL's TIMESTAMP(date, time), invalid on postgres; use the
		# portable CombineDatetime via query builder instead.
		se = frappe.qb.DocType("Stock Entry")
		data = (
			frappe.qb.from_(se)
			.select(CombineDatetime(se.posting_date, se.posting_time).as_("posting_datetime"))
			.where(
				(se.work_order == self.doc.name)
				& (se.purpose.isin(["Material Transfer for Manufacture", "Manufacture"]))
			)
			.run(as_dict=True)
		)
		if not data:
			return

		dates = [d.posting_datetime for d in data]
		self.doc.db_set("actual_start_date", min(dates))
		if self.doc.status == "Completed":
			self.doc.db_set("actual_end_date", max(dates))

	def set_lead_time(self):
		if self.doc.actual_start_date and self.doc.actual_end_date:
			self.doc.lead_time = flt(
				time_diff_in_hours(self.doc.actual_end_date, self.doc.actual_start_date) * 60
			)


@frappe.request_cache
def get_hour_rate(workstation):
	return frappe.get_cached_value("Workstation", workstation, "hour_rate") or 0.0
