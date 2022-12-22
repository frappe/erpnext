# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import datetime
import json
from typing import Optional

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Max, Min
from frappe.utils import (
	add_days,
	add_to_date,
	cint,
	flt,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	time_diff,
	time_diff_in_hours,
	time_diff_in_seconds,
)

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_mins_between_operations,
)
from erpnext.manufacturing.doctype.workstation_type.workstation_type import get_workstations


class OverlapError(frappe.ValidationError):
	pass


class OperationMismatchError(frappe.ValidationError):
	pass


class OperationSequenceError(frappe.ValidationError):
	pass


class JobCardCancelError(frappe.ValidationError):
	pass


class JobCardOverTransferError(frappe.ValidationError):
	pass


class JobCard(Document):
	def onload(self):
		excess_transfer = frappe.db.get_single_value(
			"Manufacturing Settings", "job_card_excess_transfer"
		)
		self.set_onload("job_card_excess_transfer", excess_transfer)
		self.set_onload("work_order_closed", self.is_work_order_closed())
		self.set_onload("has_stock_entry", self.has_stock_entry())

	def has_stock_entry(self):
		return frappe.db.exists("Stock Entry", {"job_card": self.name, "docstatus": ["!=", 2]})

	def before_validate(self):
		self.set_wip_warehouse()

	def validate(self):
		self.validate_time_logs()
		self.set_status()
		self.validate_operation_id()
		self.validate_sequence_id()
		self.set_sub_operations()
		self.update_sub_operation_status()
		self.validate_work_order()

	def set_sub_operations(self):
		if not self.sub_operations and self.operation:
			self.sub_operations = []
			for row in frappe.get_all(
				"Sub Operation",
				filters={"parent": self.operation},
				fields=["operation", "idx"],
				order_by="idx",
			):
				row.status = "Pending"
				row.sub_operation = row.operation
				self.append("sub_operations", row)

	def validate_time_logs(self):
		self.total_time_in_mins = 0.0
		self.total_completed_qty = 0.0

		if self.get("time_logs"):
			for d in self.get("time_logs"):
				if d.to_time and get_datetime(d.from_time) > get_datetime(d.to_time):
					frappe.throw(_("Row {0}: From time must be less than to time").format(d.idx))

				data = self.get_overlap_for(d)
				if data:
					frappe.throw(
						_("Row {0}: From Time and To Time of {1} is overlapping with {2}").format(
							d.idx, self.name, data.name
						),
						OverlapError,
					)

				if d.from_time and d.to_time:
					d.time_in_mins = time_diff_in_hours(d.to_time, d.from_time) * 60
					self.total_time_in_mins += d.time_in_mins

				if d.completed_qty and not self.sub_operations:
					self.total_completed_qty += d.completed_qty

			self.total_completed_qty = flt(self.total_completed_qty, self.precision("total_completed_qty"))

		for row in self.sub_operations:
			self.total_completed_qty += row.completed_qty

	def get_overlap_for(self, args, check_next_available_slot=False):
		production_capacity = 1

		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType("Job Card Time Log")

		time_conditions = [
			((jctl.from_time < args.from_time) & (jctl.to_time > args.from_time)),
			((jctl.from_time < args.to_time) & (jctl.to_time > args.to_time)),
			((jctl.from_time >= args.from_time) & (jctl.to_time <= args.to_time)),
		]

		if check_next_available_slot:
			time_conditions.append(((jctl.from_time >= args.from_time) & (jctl.to_time >= args.to_time)))

		query = (
			frappe.qb.from_(jctl)
			.from_(jc)
			.select(jc.name.as_("name"), jctl.to_time, jc.workstation, jc.workstation_type)
			.where(
				(jctl.parent == jc.name)
				& (Criterion.any(time_conditions))
				& (jctl.name != f"{args.name or 'No Name'}")
				& (jc.name != f"{args.parent or 'No Name'}")
				& (jc.docstatus < 2)
			)
			.orderby(jctl.to_time, order=frappe.qb.desc)
		)

		if self.workstation_type:
			query = query.where(jc.workstation_type == self.workstation_type)

		if self.workstation:
			production_capacity = (
				frappe.get_cached_value("Workstation", self.workstation, "production_capacity") or 1
			)
			query = query.where(jc.workstation == self.workstation)

		if args.get("employee"):
			# override capacity for employee
			production_capacity = 1
			query = query.where(jctl.employee == args.get("employee"))

		existing = query.run(as_dict=True)

		if existing and production_capacity > len(existing):
			return

		if self.workstation_type:
			if workstation := self.get_workstation_based_on_available_slot(existing):
				self.workstation = workstation
				return None

		return existing[0] if existing else None

	def get_workstation_based_on_available_slot(self, existing) -> Optional[str]:
		workstations = get_workstations(self.workstation_type)
		if workstations:
			busy_workstations = [row.workstation for row in existing]
			for workstation in workstations:
				if workstation not in busy_workstations:
					return workstation

	def schedule_time_logs(self, row):
		row.remaining_time_in_mins = row.time_in_mins
		while row.remaining_time_in_mins > 0:
			args = frappe._dict({"from_time": row.planned_start_time, "to_time": row.planned_end_time})

			self.validate_overlap_for_workstation(args, row)
			self.check_workstation_time(row)

	def validate_overlap_for_workstation(self, args, row):
		# get the last record based on the to time from the job card
		data = self.get_overlap_for(args, check_next_available_slot=True)
		if data:
			if not self.workstation:
				self.workstation = data.workstation

			row.planned_start_time = get_datetime(data.to_time + get_mins_between_operations())

	def check_workstation_time(self, row):
		workstation_doc = frappe.get_cached_doc("Workstation", self.workstation)
		if not workstation_doc.working_hours or cint(
			frappe.db.get_single_value("Manufacturing Settings", "allow_overtime")
		):
			if get_datetime(row.planned_end_time) < get_datetime(row.planned_start_time):
				row.planned_end_time = add_to_date(row.planned_start_time, minutes=row.time_in_mins)
				row.remaining_time_in_mins = 0.0
			else:
				row.remaining_time_in_mins -= time_diff_in_minutes(
					row.planned_end_time, row.planned_start_time
				)

			self.update_time_logs(row)
			return

		start_date = getdate(row.planned_start_time)
		start_time = get_time(row.planned_start_time)

		new_start_date = workstation_doc.validate_workstation_holiday(start_date)

		if new_start_date != start_date:
			row.planned_start_time = datetime.datetime.combine(new_start_date, start_time)
			start_date = new_start_date

		total_idx = len(workstation_doc.working_hours)

		for i, time_slot in enumerate(workstation_doc.working_hours):
			workstation_start_time = datetime.datetime.combine(start_date, get_time(time_slot.start_time))
			workstation_end_time = datetime.datetime.combine(start_date, get_time(time_slot.end_time))

			if (
				get_datetime(row.planned_start_time) >= workstation_start_time
				and get_datetime(row.planned_start_time) <= workstation_end_time
			):
				time_in_mins = time_diff_in_minutes(workstation_end_time, row.planned_start_time)

				# If remaining time fit in workstation time logs else split hours as per workstation time
				if time_in_mins > row.remaining_time_in_mins:
					row.planned_end_time = add_to_date(row.planned_start_time, minutes=row.remaining_time_in_mins)
					row.remaining_time_in_mins = 0
				else:
					row.planned_end_time = add_to_date(row.planned_start_time, minutes=time_in_mins)
					row.remaining_time_in_mins -= time_in_mins

				self.update_time_logs(row)

				if total_idx != (i + 1) and row.remaining_time_in_mins > 0:
					row.planned_start_time = datetime.datetime.combine(
						start_date, get_time(workstation_doc.working_hours[i + 1].start_time)
					)

		if row.remaining_time_in_mins > 0:
			start_date = add_days(start_date, 1)
			row.planned_start_time = datetime.datetime.combine(
				start_date, get_time(workstation_doc.working_hours[0].start_time)
			)

	def add_time_log(self, args):
		last_row = []
		employees = args.employees
		if isinstance(employees, str):
			employees = json.loads(employees)

		if self.time_logs and len(self.time_logs) > 0:
			last_row = self.time_logs[-1]

		self.reset_timer_value(args)
		if last_row and args.get("complete_time"):
			for row in self.time_logs:
				if not row.to_time:
					row.update(
						{
							"to_time": get_datetime(args.get("complete_time")),
							"operation": args.get("sub_operation"),
							"completed_qty": args.get("completed_qty") or 0.0,
						}
					)
		elif args.get("start_time"):
			new_args = frappe._dict(
				{
					"from_time": get_datetime(args.get("start_time")),
					"operation": args.get("sub_operation"),
					"completed_qty": 0.0,
				}
			)

			if employees:
				for name in employees:
					new_args.employee = name.get("employee")
					self.add_start_time_log(new_args)
			else:
				self.add_start_time_log(new_args)

		if not self.employee and employees:
			self.set_employees(employees)

		if self.status == "On Hold":
			self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)

		self.save()

	def add_start_time_log(self, args):
		self.append("time_logs", args)

	def set_employees(self, employees):
		for name in employees:
			self.append("employee", {"employee": name.get("employee"), "completed_qty": 0.0})

	def reset_timer_value(self, args):
		self.started_time = None

		if args.get("status") in ["Work In Progress", "Complete"]:
			self.current_time = 0.0

			if args.get("status") == "Work In Progress":
				self.started_time = get_datetime(args.get("start_time"))

		if args.get("status") == "Resume Job":
			args["status"] = "Work In Progress"

		if args.get("status"):
			self.status = args.get("status")

	def update_sub_operation_status(self):
		if not (self.sub_operations and self.time_logs):
			return

		operation_wise_completed_time = {}
		for time_log in self.time_logs:
			if time_log.operation not in operation_wise_completed_time:
				operation_wise_completed_time.setdefault(
					time_log.operation,
					frappe._dict(
						{"status": "Pending", "completed_qty": 0.0, "completed_time": 0.0, "employee": []}
					),
				)

			op_row = operation_wise_completed_time[time_log.operation]
			op_row.status = "Work In Progress" if not time_log.time_in_mins else "Complete"
			if self.status == "On Hold":
				op_row.status = "Pause"

			op_row.employee.append(time_log.employee)
			if time_log.time_in_mins:
				op_row.completed_time += time_log.time_in_mins
				op_row.completed_qty += time_log.completed_qty

		for row in self.sub_operations:
			operation_deatils = operation_wise_completed_time.get(row.sub_operation)
			if operation_deatils:
				if row.status != "Complete":
					row.status = operation_deatils.status

				row.completed_time = operation_deatils.completed_time
				if operation_deatils.employee:
					row.completed_time = row.completed_time / len(set(operation_deatils.employee))

					if operation_deatils.completed_qty:
						row.completed_qty = operation_deatils.completed_qty / len(set(operation_deatils.employee))
			else:
				row.status = "Pending"
				row.completed_time = 0.0
				row.completed_qty = 0.0

	def update_time_logs(self, row):
		self.append(
			"time_logs",
			{
				"from_time": row.planned_start_time,
				"to_time": row.planned_end_time,
				"completed_qty": 0,
				"time_in_mins": time_diff_in_minutes(row.planned_end_time, row.planned_start_time),
			},
		)

	@frappe.whitelist()
	def get_required_items(self):
		if not self.get("work_order"):
			return

		doc = frappe.get_doc("Work Order", self.get("work_order"))
		if doc.transfer_material_against == "Work Order" or doc.skip_transfer:
			return

		for d in doc.required_items:
			if not d.operation:
				frappe.throw(
					_("Row {0} : Operation is required against the raw material item {1}").format(
						d.idx, d.item_code
					)
				)

			if self.get("operation") == d.operation:
				self.append(
					"items",
					{
						"item_code": d.item_code,
						"source_warehouse": d.source_warehouse,
						"uom": frappe.db.get_value("Item", d.item_code, "stock_uom"),
						"item_name": d.item_name,
						"description": d.description,
						"required_qty": (d.required_qty * flt(self.for_quantity)) / doc.qty,
						"rate": d.rate,
						"amount": d.amount,
					},
				)

	def on_submit(self):
		self.validate_transfer_qty()
		self.validate_job_card()
		self.update_work_order()
		self.set_transferred_qty()

	def on_cancel(self):
		self.update_work_order()
		self.set_transferred_qty()

	def validate_transfer_qty(self):
		if self.items and self.transferred_qty < self.for_quantity:
			frappe.throw(
				_(
					"Materials needs to be transferred to the work in progress warehouse for the job card {0}"
				).format(self.name)
			)

	def validate_job_card(self):
		if (
			self.work_order
			and frappe.get_cached_value("Work Order", self.work_order, "status") == "Stopped"
		):
			frappe.throw(
				_("Transaction not allowed against stopped Work Order {0}").format(
					get_link_to_form("Work Order", self.work_order)
				)
			)

		if not self.time_logs:
			frappe.throw(
				_("Time logs are required for {0} {1}").format(
					bold("Job Card"), get_link_to_form("Job Card", self.name)
				)
			)

		if self.for_quantity and self.total_completed_qty != self.for_quantity:
			total_completed_qty = bold(_("Total Completed Qty"))
			qty_to_manufacture = bold(_("Qty to Manufacture"))

			frappe.throw(
				_("The {0} ({1}) must be equal to {2} ({3})").format(
					total_completed_qty,
					bold(self.total_completed_qty),
					qty_to_manufacture,
					bold(self.for_quantity),
				)
			)

	def update_work_order(self):
		if not self.work_order:
			return

		if self.is_corrective_job_card and not cint(
			frappe.db.get_single_value(
				"Manufacturing Settings", "add_corrective_operation_cost_in_finished_good_valuation"
			)
		):
			return

		for_quantity, time_in_mins = 0, 0
		from_time_list, to_time_list = [], []

		field = "operation_id"
		data = self.get_current_operation_data()
		if data and len(data) > 0:
			for_quantity = flt(data[0].completed_qty)
			time_in_mins = flt(data[0].time_in_mins)

		wo = frappe.get_doc("Work Order", self.work_order)

		if self.is_corrective_job_card:
			self.update_corrective_in_work_order(wo)

		elif self.operation_id:
			self.validate_produced_quantity(for_quantity, wo)
			self.update_work_order_data(for_quantity, time_in_mins, wo)

	def update_corrective_in_work_order(self, wo):
		wo.corrective_operation_cost = 0.0
		for row in frappe.get_all(
			"Job Card",
			fields=["total_time_in_mins", "hour_rate"],
			filters={"is_corrective_job_card": 1, "docstatus": 1, "work_order": self.work_order},
		):
			wo.corrective_operation_cost += flt(row.total_time_in_mins) * flt(row.hour_rate)

		wo.calculate_operating_cost()
		wo.flags.ignore_validate_update_after_submit = True
		wo.save()

	def validate_produced_quantity(self, for_quantity, wo):
		if self.docstatus < 2:
			return

		if wo.produced_qty > for_quantity:
			first_part_msg = _(
				"The {0} {1} is used to calculate the valuation cost for the finished good {2}."
			).format(
				frappe.bold(_("Job Card")), frappe.bold(self.name), frappe.bold(self.production_item)
			)

			second_part_msg = _(
				"Kindly cancel the Manufacturing Entries first against the work order {0}."
			).format(frappe.bold(get_link_to_form("Work Order", self.work_order)))

			frappe.throw(
				_("{0} {1}").format(first_part_msg, second_part_msg), JobCardCancelError, title=_("Error")
			)

	def update_work_order_data(self, for_quantity, time_in_mins, wo):
		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType("Job Card Time Log")

		time_data = (
			frappe.qb.from_(jc)
			.from_(jctl)
			.select(Min(jctl.from_time).as_("start_time"), Max(jctl.to_time).as_("end_time"))
			.where(
				(jctl.parent == jc.name)
				& (jc.work_order == self.work_order)
				& (jc.operation_id == self.operation_id)
				& (jc.docstatus == 1)
				& (IfNull(jc.is_corrective_job_card, 0) == 0)
			)
		).run(as_dict=True)

		for data in wo.operations:
			if data.get("name") == self.operation_id:
				data.completed_qty = for_quantity
				data.actual_operation_time = time_in_mins
				data.actual_start_time = time_data[0].start_time if time_data else None
				data.actual_end_time = time_data[0].end_time if time_data else None
				if data.get("workstation") != self.workstation:
					# workstations can change in a job card
					data.workstation = self.workstation

		wo.flags.ignore_validate_update_after_submit = True
		wo.update_operation_status()
		wo.calculate_operating_cost()
		wo.set_actual_dates()
		wo.save()

	def get_current_operation_data(self):
		return frappe.get_all(
			"Job Card",
			fields=["sum(total_time_in_mins) as time_in_mins", "sum(total_completed_qty) as completed_qty"],
			filters={
				"docstatus": 1,
				"work_order": self.work_order,
				"operation_id": self.operation_id,
				"is_corrective_job_card": 0,
			},
		)

	def set_transferred_qty_in_job_card_item(self, ste_doc):
		from frappe.query_builder.functions import Sum

		def _validate_over_transfer(row, transferred_qty):
			"Block over transfer of items if not allowed in settings."
			required_qty = frappe.db.get_value("Job Card Item", row.job_card_item, "required_qty")
			is_excess = flt(transferred_qty) > flt(required_qty)
			if is_excess:
				frappe.throw(
					_(
						"Row #{0}: Cannot transfer more than Required Qty {1} for Item {2} against Job Card {3}"
					).format(
						row.idx, frappe.bold(required_qty), frappe.bold(row.item_code), ste_doc.job_card
					),
					title=_("Excess Transfer"),
					exc=JobCardOverTransferError,
				)

		for row in ste_doc.items:
			if not row.job_card_item:
				continue

			sed = frappe.qb.DocType("Stock Entry Detail")
			se = frappe.qb.DocType("Stock Entry")
			transferred_qty = (
				frappe.qb.from_(sed)
				.join(se)
				.on(sed.parent == se.name)
				.select(Sum(sed.qty))
				.where(
					(sed.job_card_item == row.job_card_item)
					& (se.docstatus == 1)
					& (se.purpose == "Material Transfer for Manufacture")
				)
			).run()[0][0]

			allow_excess = frappe.db.get_single_value("Manufacturing Settings", "job_card_excess_transfer")
			if not allow_excess:
				_validate_over_transfer(row, transferred_qty)

			frappe.db.set_value("Job Card Item", row.job_card_item, "transferred_qty", flt(transferred_qty))

	def set_transferred_qty(self, update_status=False):
		"Set total FG Qty in Job Card for which RM was transferred."
		if not self.items:
			self.transferred_qty = self.for_quantity if self.docstatus == 1 else 0

		doc = frappe.get_doc("Work Order", self.get("work_order"))
		if doc.transfer_material_against == "Work Order" or doc.skip_transfer:
			return

		if self.items:
			# sum of 'For Quantity' of Stock Entries against JC
			self.transferred_qty = (
				frappe.db.get_value(
					"Stock Entry",
					{
						"job_card": self.name,
						"work_order": self.work_order,
						"docstatus": 1,
						"purpose": "Material Transfer for Manufacture",
					},
					"sum(fg_completed_qty)",
				)
				or 0
			)

		self.db_set("transferred_qty", self.transferred_qty)

		qty = 0
		if self.work_order:
			doc = frappe.get_doc("Work Order", self.work_order)
			if doc.transfer_material_against == "Job Card" and not doc.skip_transfer:
				completed = True
				for d in doc.operations:
					if d.status != "Completed":
						completed = False
						break

				if completed:
					job_cards = frappe.get_all(
						"Job Card",
						filters={"work_order": self.work_order, "docstatus": ("!=", 2)},
						fields="sum(transferred_qty) as qty",
						group_by="operation_id",
					)

					if job_cards:
						qty = min(d.qty for d in job_cards)

			doc.db_set("material_transferred_for_manufacturing", qty)

		self.set_status(update_status)

	def set_status(self, update_status=False):
		if self.status == "On Hold" and self.docstatus == 0:
			return

		self.status = {0: "Open", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]

		if self.docstatus < 2:
			if self.for_quantity <= self.transferred_qty:
				self.status = "Material Transferred"

			if self.time_logs:
				self.status = "Work In Progress"

			if self.docstatus == 1 and (self.for_quantity <= self.total_completed_qty or not self.items):
				self.status = "Completed"

		if update_status:
			self.db_set("status", self.status)

	def set_wip_warehouse(self):
		if not self.wip_warehouse:
			self.wip_warehouse = frappe.db.get_single_value(
				"Manufacturing Settings", "default_wip_warehouse"
			)

	def validate_operation_id(self):
		if (
			self.get("operation_id")
			and self.get("operation_row_number")
			and self.operation
			and self.work_order
			and frappe.get_cached_value("Work Order Operation", self.operation_row_number, "name")
			!= self.operation_id
		):
			work_order = bold(get_link_to_form("Work Order", self.work_order))
			frappe.throw(
				_("Operation {0} does not belong to the work order {1}").format(
					bold(self.operation), work_order
				),
				OperationMismatchError,
			)

	def validate_sequence_id(self):
		if self.is_corrective_job_card:
			return

		if not (self.work_order and self.sequence_id):
			return

		current_operation_qty = 0.0
		data = self.get_current_operation_data()
		if data and len(data) > 0:
			current_operation_qty = flt(data[0].completed_qty)

		current_operation_qty += flt(self.total_completed_qty)

		data = frappe.get_all(
			"Work Order Operation",
			fields=["operation", "status", "completed_qty"],
			filters={"docstatus": 1, "parent": self.work_order, "sequence_id": ("<", self.sequence_id)},
			order_by="sequence_id, idx",
		)

		message = "Job Card {0}: As per the sequence of the operations in the work order {1}".format(
			bold(self.name), bold(get_link_to_form("Work Order", self.work_order))
		)

		for row in data:
			if row.status != "Completed" and row.completed_qty < current_operation_qty:
				frappe.throw(
					_("{0}, complete the operation {1} before the operation {2}.").format(
						message, bold(row.operation), bold(self.operation)
					),
					OperationSequenceError,
				)

	def validate_work_order(self):
		if self.is_work_order_closed():
			frappe.throw(_("You can't make any changes to Job Card since Work Order is closed."))

	def is_work_order_closed(self):
		if self.work_order:
			status = frappe.get_value("Work Order", self.work_order)

			if status == "Closed":
				return True

		return False


@frappe.whitelist()
def make_time_log(args):
	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)
	doc = frappe.get_doc("Job Card", args.job_card_id)
	doc.validate_sequence_id()
	doc.add_time_log(args)


@frappe.whitelist()
def get_operation_details(work_order, operation):
	if work_order and operation:
		return frappe.get_all(
			"Work Order Operation",
			fields=["name", "idx"],
			filters={"parent": work_order, "operation": operation},
		)


@frappe.whitelist()
def get_operations(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("work_order"):
		frappe.msgprint(_("Please select a Work Order first."))
		return []
	args = {"parent": filters.get("work_order")}
	if txt:
		args["operation"] = ("like", "%{0}%".format(txt))

	return frappe.get_all(
		"Work Order Operation",
		filters=args,
		fields=["distinct operation as operation"],
		limit_start=start,
		limit_page_length=page_len,
		order_by="idx asc",
		as_list=1,
	)


@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
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
def make_stock_entry(source_name, target_doc=None):
	def update_item(source, target, source_parent):
		target.t_warehouse = source_parent.wip_warehouse

		if not target.conversion_factor:
			target.conversion_factor = 1

		pending_rm_qty = flt(source.required_qty) - flt(source.transferred_qty)
		if pending_rm_qty > 0:
			target.qty = pending_rm_qty

	def set_missing_values(source, target):
		target.purpose = "Material Transfer for Manufacture"
		target.from_bom = 1

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


def time_diff_in_minutes(string_ed_date, string_st_date):
	return time_diff(string_ed_date, string_st_date).total_seconds() / 60


@frappe.whitelist()
def get_job_details(start, end, filters=None):
	events = []

	event_color = {
		"Completed": "#cdf5a6",
		"Material Transferred": "#ffdd9e",
		"Work In Progress": "#D3D3D3",
	}

	from frappe.desk.reportview import get_filters_cond

	conditions = get_filters_cond("Job Card", filters, [])

	job_cards = frappe.db.sql(
		""" SELECT `tabJob Card`.name, `tabJob Card`.work_order,
			`tabJob Card`.status, ifnull(`tabJob Card`.remarks, ''),
			min(`tabJob Card Time Log`.from_time) as from_time,
			max(`tabJob Card Time Log`.to_time) as to_time
		FROM `tabJob Card` , `tabJob Card Time Log`
		WHERE
			`tabJob Card`.name = `tabJob Card Time Log`.parent {0}
			group by `tabJob Card`.name""".format(
			conditions
		),
		as_dict=1,
	)

	for d in job_cards:
		subject_data = []
		for field in ["name", "work_order", "remarks"]:
			if not d.get(field):
				continue

			subject_data.append(d.get(field))

		color = event_color.get(d.status)
		job_card_data = {
			"from_time": d.from_time,
			"to_time": d.to_time,
			"name": d.name,
			"subject": "\n".join(subject_data),
			"color": color if color else "#89bcde",
		}

		events.append(job_card_data)

	return events


@frappe.whitelist()
def make_corrective_job_card(source_name, operation=None, for_operation=None, target_doc=None):
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
		target.validate_time_logs()

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
