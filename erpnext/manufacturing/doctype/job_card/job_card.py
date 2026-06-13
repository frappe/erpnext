# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import datetime
import json
from collections import OrderedDict
from typing import Any

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Max, Min, Sum
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
)

from erpnext.controllers.stock_controller import (
	QualityInspectionNotSubmittedError,
	QualityInspectionRejectedError,
)
from erpnext.manufacturing.doctype.bom.bom import add_additional_cost, get_bom_items_as_dict
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_mins_between_operations,
)
from erpnext.manufacturing.doctype.workstation_type.workstation_type import get_workstations
from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	get_subcontracting_boms_for_finished_goods,
)

from .mapper import (
	make_stock_entry,
)


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
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.job_card_item.job_card_item import JobCardItem
		from erpnext.manufacturing.doctype.job_card_operation.job_card_operation import JobCardOperation
		from erpnext.manufacturing.doctype.job_card_scheduled_time.job_card_scheduled_time import (
			JobCardScheduledTime,
		)
		from erpnext.manufacturing.doctype.job_card_secondary_item.job_card_secondary_item import (
			JobCardSecondaryItem,
		)
		from erpnext.manufacturing.doctype.job_card_time_log.job_card_time_log import JobCardTimeLog

		actual_end_date: DF.Datetime | None
		actual_start_date: DF.Datetime | None
		amended_from: DF.Link | None
		backflush_from_wip_warehouse: DF.Check
		barcode: DF.Barcode | None
		batch_no: DF.Link | None
		bom_no: DF.Link | None
		company: DF.Link
		employee: DF.TableMultiSelect[JobCardTimeLog]
		expected_end_date: DF.Datetime | None
		expected_start_date: DF.Datetime | None
		finished_good: DF.Link | None
		for_job_card: DF.Link | None
		for_operation: DF.Link | None
		for_quantity: DF.Float
		hour_rate: DF.Currency
		is_corrective_job_card: DF.Check
		is_paused: DF.Check
		is_subcontracted: DF.Check
		item_name: DF.ReadOnly | None
		items: DF.Table[JobCardItem]
		manufactured_qty: DF.Float
		naming_series: DF.Literal["PO-JOB.#####"]
		operation: DF.Link
		operation_id: DF.Data | None
		operation_row_id: DF.Int
		operation_row_number: DF.Literal[None]
		pending_qty: DF.Float
		posting_date: DF.Date | None
		process_loss_qty: DF.Float
		production_item: DF.Link | None
		project: DF.Link | None
		quality_inspection: DF.Link | None
		quality_inspection_template: DF.Link | None
		remarks: DF.SmallText | None
		requested_qty: DF.Float
		scheduled_time_logs: DF.Table[JobCardScheduledTime]
		secondary_items: DF.Table[JobCardSecondaryItem]
		semi_fg_bom: DF.Link | None
		sequence_id: DF.Int
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.SmallText | None
		skip_material_transfer: DF.Check
		source_warehouse: DF.Link | None
		status: DF.Literal[
			"Open",
			"Work In Progress",
			"Partially Transferred",
			"Material Transferred",
			"On Hold",
			"Submitted",
			"To Manufacture",
			"Cancelled",
			"Completed",
		]
		sub_operations: DF.Table[JobCardOperation]
		target_warehouse: DF.Link | None
		time_logs: DF.Table[JobCardTimeLog]
		time_required: DF.Float
		total_completed_qty: DF.Float
		total_time_in_mins: DF.Float
		track_semi_finished_goods: DF.Check
		transferred_qty: DF.Float
		wip_warehouse: DF.Link | None
		work_order: DF.Link
		workstation: DF.Link
		workstation_type: DF.Link | None
	# end: auto-generated types

	def onload(self):
		excess_transfer = frappe.db.get_single_value("Manufacturing Settings", "job_card_excess_transfer")
		self.set_onload("job_card_excess_transfer", excess_transfer)
		self.set_onload("work_order_closed", self.is_work_order_closed())
		self.set_onload("has_stock_entry", self.has_stock_entry())

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def has_stock_entry(self):
		return frappe.db.exists("Stock Entry", {"job_card": self.name, "docstatus": ["!=", 2]})

	def before_validate(self):
		self.set_wip_warehouse()

	def validate(self):
		self.validate_time_logs()
		self.validate_on_hold()
		self.set_status()
		self.validate_operation_id()
		self.validate_sequence_id()
		self.set_sub_operations()
		self.update_sub_operation_status()
		if self.sub_operations:
			self.set_total_completed_qty_from_sub_operations()

		self.validate_work_order()
		self.set_employees()

		if self.docstatus == 1:
			self.validate_semi_finished_goods()

	def validate_semi_finished_goods(self):
		if not self.track_semi_finished_goods or self.is_subcontracted:
			return

		if self.items and not self.transferred_qty and not self.skip_material_transfer:
			frappe.throw(
				_(
					"Materials need to be transferred to the work in progress warehouse for the job card {0}"
				).format(self.name)
			)

		if self.docstatus == 1 and not self.total_completed_qty:
			frappe.throw(
				_(
					"Total Completed Qty is required for Job Card {0}, please start and complete the job card before submission"
				).format(self.name)
			)

	def on_update(self):
		self.validate_job_card_qty()

	def validate_on_hold(self):
		if self.is_paused and not self.time_logs:
			self.is_paused = 0

	def set_manufactured_qty(self):
		self.manufactured_qty = flt(self.get_manufactured_qty())
		self.db_set("manufactured_qty", self.manufactured_qty)

		self.update_semi_finished_good_details()
		self.set_status(update_status=True)

	def get_manufactured_qty(self):
		table_name = "Subcontracting Receipt Item" if self.is_subcontracted else "Stock Entry"

		table = frappe.qb.DocType(table_name)
		query = frappe.qb.from_(table).where((table.job_card == self.name) & (table.docstatus == 1))

		if self.is_subcontracted:
			query = query.select(Sum(table.qty))
		else:
			child = frappe.qb.DocType("Stock Entry Detail")
			query = (
				query.join(child)
				.on(table.name == child.parent)
				.select(Sum(child.transfer_qty))
				.where((table.purpose == "Manufacture") & (child.is_finished_item == 1))
			)

		return query.run()[0][0] or 0.0

	def validate_job_card_qty(self):
		if not (self.operation_id and self.work_order):
			return

		wo_qty = self.get_allowed_wo_qty()
		completed_qty = flt(frappe.db.get_value("Work Order Operation", self.operation_id, "completed_qty"))
		job_card_qty = self.get_total_job_card_qty()

		if job_card_qty and ((job_card_qty - completed_qty) > wo_qty):
			self.throw_extra_qty_error()

	def get_allowed_wo_qty(self):
		wo_qty = flt(frappe.get_cached_value("Work Order", self.work_order, "qty"))
		over_production_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
		return wo_qty + (wo_qty * over_production_percentage / 100)

	def get_total_job_card_qty(self):
		job_card_qty = frappe.get_all(
			"Job Card",
			fields=[{"SUM": "for_quantity"}],
			filters={
				"work_order": self.work_order,
				"operation_id": self.operation_id,
				"docstatus": ["!=", 2],
			},
			as_list=1,
		)
		return flt(job_card_qty[0][0]) if job_card_qty else 0

	def throw_extra_qty_error(self):
		form_link = get_link_to_form("Manufacturing Settings", "Manufacturing Settings")
		frappe.throw(
			_(
				"Qty To Manufacture in the job card cannot be greater than Qty To Manufacture in the work order for the operation {0}. <br><br><b>Solution: </b> Either you can reduce the Qty To Manufacture in the job card or set the 'Overproduction Percentage For Work Order' in the {1}."
			).format(bold(self.operation), form_link),
			title=_("Extra Job Card Quantity"),
		)

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

	def set_secondary_items(self):
		if not self.semi_fg_bom and not self.bom_no:
			return

		items_dict = get_bom_items_as_dict(
			self.semi_fg_bom or self.bom_no,
			self.company,
			qty=self.for_quantity,
			fetch_exploded=0,
			fetch_secondary_items=1,
		)
		for item_code, values in items_dict.items():
			self.append_secondary_item(item_code, frappe._dict(values))

	def append_secondary_item(self, item_code, values):
		secondary_item = {
			"item_code": item_code,
			"stock_qty": values.qty,
			"item_name": values.item_name,
			"stock_uom": values.stock_uom,
			"secondary_item_type": values.secondary_item_type,
			"bom_secondary_item": values.name,
		}

		if not values.is_legacy:
			secondary_item["stock_qty"] -= flt(
				secondary_item["stock_qty"] * (values.process_loss_per / 100),
				self.precision("for_quantity"),
			)

		self.append("secondary_items", secondary_item)

	def validate_time_logs(self, save=False):
		self.total_time_in_mins = 0.0
		self.total_completed_qty = 0.0

		if not self.get("time_logs"):
			return

		for d in self.get("time_logs"):
			self.validate_time_log_row(d)

		self.total_completed_qty = flt(self.total_completed_qty, self.precision("total_completed_qty"))

		if save and self.docstatus == 1:
			self.save_time_log_totals()

	def validate_time_log_row(self, d):
		if d.to_time and get_datetime(d.from_time) > get_datetime(d.to_time):
			frappe.throw(_("Row {0}: From time must be less than to time").format(d.idx))

		self.validate_overlap_in_time_log(d)

		if d.from_time and d.to_time:
			d.time_in_mins = time_diff_in_hours(d.to_time, d.from_time) * 60
			self.total_time_in_mins += d.time_in_mins

		if d.completed_qty and not self.sub_operations:
			self.total_completed_qty += d.completed_qty

	def validate_overlap_in_time_log(self, d):
		open_job_cards = []
		if d.get("employee"):
			open_job_cards = self.get_open_job_cards(d.get("employee"), workstation=self.workstation)

		data = self.get_overlap_for(d, open_job_cards=open_job_cards)
		if data:
			frappe.throw(
				_("Row {0}: From Time and To Time of {1} are overlapping with {2}").format(
					d.idx, self.name, data.name
				),
				OverlapError,
			)

	def save_time_log_totals(self):
		self.db_set(
			{
				"total_time_in_mins": self.total_time_in_mins,
				"total_completed_qty": self.total_completed_qty,
			}
		)

	def set_total_completed_qty_from_sub_operations(self):
		sub_op_total_qty = []
		for row in self.sub_operations:
			sub_op_total_qty.append(flt(row.completed_qty))

		if sub_op_total_qty:
			self.total_completed_qty = min(sub_op_total_qty)

	def get_overlap_for(self, args, open_job_cards=None):
		time_logs = self.get_overlapping_time_logs(args, open_job_cards)
		if not time_logs:
			return {}

		time_logs = sorted(time_logs, key=lambda x: x.get("to_time"))

		self.validate_employee_overlap(args)

		if not self.has_overlap(self.get_production_capacity(), time_logs):
			return {}

		if not self.workstation and self.workstation_type and time_logs:
			if workstation_time := self.get_workstation_based_on_available_slot(time_logs):
				self.workstation = workstation_time.get("workstation")
				return workstation_time

		return time_logs[0]

	def get_overlapping_time_logs(self, args, open_job_cards=None):
		time_logs = []
		time_logs.extend(self.get_time_logs(args, "Job Card Time Log"))
		time_logs.extend(self.get_time_logs(args, "Job Card Scheduled Time", open_job_cards=open_job_cards))
		return time_logs

	def get_production_capacity(self):
		if self.workstation:
			return frappe.get_cached_value("Workstation", self.workstation, "production_capacity") or 1
		return 1

	def validate_employee_overlap(self, args):
		if self.get_open_job_cards(args.get("employee")):
			frappe.throw(
				_(
					"Employee {0} is currently working on another workstation. Please assign another employee."
				).format(args.get("employee")),
				OverlapError,
			)

	def has_overlap(self, production_capacity, time_logs):
		if production_capacity == 1 and len(time_logs) >= 1:
			return True
		if not len(time_logs):
			return False

		alloted_capacity = self.get_alloted_capacity(time_logs)
		# if number of keys is greater or equal to production capacity, full capacity is utilized -> overlap
		return len(alloted_capacity) >= production_capacity

	def get_alloted_capacity(self, time_logs):
		# sorting overlapping job cards as per from_time
		time_logs = sorted(time_logs, key=lambda x: x.get("from_time"))
		# alloted_capacity has key number starting from 1. Key number increments by 1 if a non sequential job card found.
		# Each key stores the last to_time of its sequential job cards.
		alloted_capacity = {1: time_logs[0]["to_time"]}
		for i in range(1, len(time_logs)):
			sequential_job_card_found = False
			for key in alloted_capacity.keys():
				# if current job card from_time is >= last to_time in that key, these job cards are sequential
				if alloted_capacity[key] <= time_logs[i]["from_time"]:
					alloted_capacity[key] = time_logs[i]["to_time"]
					sequential_job_card_found = True
					break
			# if no sequential job card found above, it is overlapping -> open a new capacity slot
			if not sequential_job_card_found:
				key = key + 1
				alloted_capacity[key] = time_logs[i]["to_time"]
		return alloted_capacity

	def get_time_logs(self, args, doctype, open_job_cards=None):
		if args.get("remaining_time_in_mins") and get_datetime(args.from_time) >= get_datetime(args.to_time):
			args.to_time = add_to_date(args.from_time, minutes=args.get("remaining_time_in_mins"))

		if args.get("employee") and not open_job_cards and doctype == "Job Card Scheduled Time":
			return []

		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType(doctype)

		query = self.get_base_overlap_query(jc, jctl, args)
		query = self.apply_workstation_filters(query, jc)
		query = self.apply_employee_filters(query, jc, jctl, args, doctype, open_job_cards)
		query = self.apply_docstatus_filters(query, jc, doctype)

		return query.run(as_dict=True)

	def get_base_overlap_query(self, jc, jctl, args):
		time_conditions = [
			((jctl.from_time < args.from_time) & (jctl.to_time > args.from_time)),
			((jctl.from_time < args.to_time) & (jctl.to_time > args.to_time)),
			((jctl.from_time >= args.from_time) & (jctl.to_time <= args.to_time)),
		]

		return (
			frappe.qb.from_(jctl)
			.from_(jc)
			.select(
				jc.name.as_("name"),
				jctl.name.as_("row_name"),
				jctl.from_time,
				jctl.to_time,
				jc.workstation,
				jc.workstation_type,
			)
			.where(
				(jctl.parent == jc.name)
				& (Criterion.any(time_conditions))
				& (jctl.name != f"{args.name or 'No Name'}")
				& (jc.name != f"{args.parent or 'No Name'}")
				& (jc.docstatus < 2)
			)
			.orderby(jctl.to_time)
		)

	def apply_workstation_filters(self, query, jc):
		if self.workstation_type:
			query = query.where(jc.workstation_type == self.workstation_type)

		if self.workstation:
			query = query.where(jc.workstation == self.workstation)

		return query

	def apply_employee_filters(self, query, jc, jctl, args, doctype, open_job_cards):
		if args.get("employee"):
			if doctype == "Job Card Time Log":
				query = query.where(jctl.employee == args.get("employee"))
			else:
				query = query.where(jc.name.isin(open_job_cards))

		return query

	def apply_docstatus_filters(self, query, jc, doctype):
		if doctype == "Job Card Time Log":
			query = query.where(jc.docstatus < 2)
		else:
			query = query.where((jc.docstatus == 0) & (jc.total_time_in_mins == 0))

		return query

	def get_open_job_cards(self, employee, workstation=None):
		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType("Job Card Time Log")

		query = (
			frappe.qb.from_(jc)
			.left_join(jctl)
			.on(jc.name == jctl.parent)
			.select(jc.name)
			.where(
				(jctl.parent == jc.name)
				& (jctl.employee == employee)
				& (jc.docstatus < 1)
				& (jc.name != self.name)
			)
		)

		if workstation:
			query = query.where(jc.workstation == workstation)

		jobs = query.run(as_dict=True)
		return [job.get("name") for job in jobs] if jobs else []

	def get_workstation_based_on_available_slot(self, existing_time_logs) -> dict:
		workstations = get_workstations(self.workstation_type)
		if workstations:
			busy_workstations = self.time_slot_wise_busy_workstations(existing_time_logs)
			for time_slot in busy_workstations:
				available_workstations = sorted(list(set(workstations) - set(busy_workstations[time_slot])))
				if available_workstations:
					return frappe._dict(
						{
							"workstation": available_workstations[0],
							"planned_start_time": get_datetime(time_slot[0]),
							"to_time": get_datetime(time_slot[1]),
						}
					)

		return frappe._dict({})

	@staticmethod
	def time_slot_wise_busy_workstations(existing_time_logs) -> dict:
		time_slot = OrderedDict()
		for row in existing_time_logs:
			from_time = get_datetime(row.from_time).strftime("%Y-%m-%d %H:%M")
			to_time = get_datetime(row.to_time).strftime("%Y-%m-%d %H:%M")
			time_slot.setdefault((from_time, to_time), []).append(row.workstation)

		return time_slot

	def schedule_time_logs(self, row):
		row.remaining_time_in_mins = row.time_in_mins
		while row.remaining_time_in_mins > 0:
			args = frappe._dict(
				{
					"from_time": row.planned_start_time,
					"to_time": row.planned_end_time,
					"remaining_time_in_mins": row.remaining_time_in_mins,
				}
			)

			self.validate_overlap_for_workstation(args, row)
			self.check_workstation_time(row)

	def validate_overlap_for_workstation(self, args, row):
		# get the last record based on the to time from the job card
		data = self.get_overlap_for(args)

		if not self.workstation:
			workstations = get_workstations(self.workstation_type)
			if workstations:
				# Get the first workstation
				self.workstation = workstations[0]

		if not data:
			row.planned_start_time = args.from_time
			return

		if data:
			if data.get("planned_start_time"):
				args.planned_start_time = get_datetime(data.planned_start_time)
			else:
				args.planned_start_time = get_datetime(data.to_time + get_mins_between_operations())

			args.from_time = args.planned_start_time
			args.to_time = add_to_date(args.planned_start_time, minutes=row.remaining_time_in_mins)

			self.validate_overlap_for_workstation(args, row)

	def check_workstation_time(self, row):
		workstation_doc = frappe.get_cached_doc("Workstation", self.workstation)
		if not workstation_doc.working_hours or cint(
			frappe.db.get_single_value("Manufacturing Settings", "allow_overtime")
		):
			self.schedule_without_working_hours(row)
			return

		start_date = self.adjust_start_date_for_holiday(workstation_doc, row)
		start_date = self.fit_row_in_working_hours(workstation_doc, row, start_date)

		if row.remaining_time_in_mins > 0:
			start_date = add_days(start_date, 1)
			row.planned_start_time = datetime.datetime.combine(
				start_date, get_time(workstation_doc.working_hours[0].start_time)
			)

	def schedule_without_working_hours(self, row):
		if get_datetime(row.planned_end_time) <= get_datetime(row.planned_start_time):
			row.planned_end_time = add_to_date(row.planned_start_time, minutes=row.time_in_mins)
			row.remaining_time_in_mins = 0.0
		else:
			row.remaining_time_in_mins -= time_diff_in_minutes(row.planned_end_time, row.planned_start_time)

		self.update_time_logs(row)

	def adjust_start_date_for_holiday(self, workstation_doc, row):
		start_date = getdate(row.planned_start_time)
		start_time = get_time(row.planned_start_time)

		new_start_date = workstation_doc.validate_workstation_holiday(start_date)

		if new_start_date != start_date:
			row.planned_start_time = datetime.datetime.combine(new_start_date, start_time)
			start_date = new_start_date

		return start_date

	def fit_row_in_working_hours(self, workstation_doc, row, start_date):
		total_idx = len(workstation_doc.working_hours)

		for i, time_slot in enumerate(workstation_doc.working_hours):
			workstation_start_time = datetime.datetime.combine(start_date, get_time(time_slot.start_time))
			workstation_end_time = datetime.datetime.combine(start_date, get_time(time_slot.end_time))

			if not (
				get_datetime(row.planned_start_time) >= workstation_start_time
				and get_datetime(row.planned_start_time) <= workstation_end_time
			):
				continue

			self.consume_working_hour_slot(row, workstation_end_time)

			if total_idx != (i + 1) and row.remaining_time_in_mins > 0:
				row.planned_start_time = datetime.datetime.combine(
					start_date, get_time(workstation_doc.working_hours[i + 1].start_time)
				)

		return start_date

	def consume_working_hour_slot(self, row, workstation_end_time):
		time_in_mins = time_diff_in_minutes(workstation_end_time, row.planned_start_time)

		# If remaining time fits in workstation time logs else split hours as per workstation time
		if time_in_mins > row.remaining_time_in_mins:
			row.planned_end_time = add_to_date(row.planned_start_time, minutes=row.remaining_time_in_mins)
			row.remaining_time_in_mins = 0
		else:
			row.planned_end_time = add_to_date(row.planned_start_time, minutes=time_in_mins)
			row.remaining_time_in_mins -= time_in_mins

		self.update_time_logs(row)

	def add_time_log(self, args):
		employees = args.employees
		if isinstance(employees, str):
			employees = json.loads(employees)

		last_row = self.time_logs[-1] if self.time_logs and len(self.time_logs) > 0 else []

		if last_row and args.get("complete_time"):
			self.complete_open_time_logs(args, last_row)
		elif args.get("start_time"):
			self.add_start_time_logs(args, employees)

	def complete_open_time_logs(self, args, last_row):
		for row in self.time_logs:
			if not row.to_time:
				to_time = get_datetime(args.get("complete_time"))
				row.db_set(
					{
						"to_time": to_time,
						"time_in_mins": time_diff_in_minutes(to_time, row.from_time),
						"operation": args.get("sub_operation"),
						"completed_qty": (args.get("completed_qty") if last_row.idx == row.idx else 0.0),
					}
				)

	def add_start_time_logs(self, args, employees):
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

	def add_start_time_log(self, args):
		if args.from_time and args.to_time:
			args.time_in_mins = time_diff_in_minutes(args.to_time, args.from_time)

		row = self.append("time_logs", args)
		row.db_update()

	def update_sub_operation_status(self):
		if not self.sub_operations:
			return

		operation_wise_completed_time = self.get_operation_wise_completed_time()

		for row in self.sub_operations:
			operation_deatils = operation_wise_completed_time.get(row.sub_operation)
			if operation_deatils:
				self.set_sub_operation_from_details(row, operation_deatils)
			else:
				row.status = "Pending"
				row.completed_time = 0.0
				row.completed_qty = 0.0

	def get_operation_wise_completed_time(self):
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
				op_row.completed_qty += flt(time_log.completed_qty)

		return operation_wise_completed_time

	def set_sub_operation_from_details(self, row, operation_deatils):
		if row.status != "Complete":
			row.status = operation_deatils.status

		row.completed_time = operation_deatils.completed_time
		if operation_deatils.employee:
			row.completed_time = row.completed_time / len(set(operation_deatils.employee))

			if operation_deatils.completed_qty:
				row.completed_qty = operation_deatils.completed_qty / len(set(operation_deatils.employee))

	def update_time_logs(self, row):
		self.append(
			"scheduled_time_logs",
			{
				"from_time": row.planned_start_time,
				"to_time": row.planned_end_time,
				"completed_qty": 0,
				"time_in_mins": time_diff_in_minutes(row.planned_end_time, row.planned_start_time),
			},
		)

	@frappe.whitelist()
	def get_required_items(self):
		frappe.has_permission("Job Card", "write", doc=self, throw=True)

		if not self.get("work_order"):
			return

		doc = frappe.get_doc("Work Order", self.get("work_order"))
		if not doc.track_semi_finished_goods and (
			doc.transfer_material_against == "Work Order" or doc.skip_transfer
		):
			return

		for d in doc.required_items:
			self.append_required_item(doc, d)

	def append_required_item(self, doc, d):
		if not doc.track_semi_finished_goods and not d.operation and not d.operation_row_id:
			frappe.throw(
				_("Row {0} : Operation is required against the raw material item {1}").format(
					d.idx, d.item_code
				)
			)

		if not (
			self.get("operation") == d.operation
			or self.operation_row_id == d.operation_row_id
			or self.is_corrective_job_card
		):
			return

		self.append(
			"items",
			{
				"item_code": d.item_code,
				"source_warehouse": self.source_warehouse or d.source_warehouse,
				"uom": frappe.db.get_value("Item", d.item_code, "stock_uom"),
				"item_name": d.item_name,
				"description": d.description,
				"required_qty": (d.required_qty * flt(self.for_quantity)) / doc.qty,
				"rate": d.rate,
				"amount": d.amount,
			},
		)

	def before_save(self):
		self.set_expected_and_actual_time()
		self.set_process_loss()

	def on_submit(self):
		self.validate_inspection()
		self.validate_transfer_qty()
		self.validate_job_card()
		self.update_work_order()
		self.set_transferred_qty()

	def on_cancel(self):
		self.update_work_order()
		self.set_transferred_qty()

	def validate_inspection(self):
		bom_inspection_required = frappe.get_value("BOM", self.bom_no, "inspection_required")
		operation_inspection_required = frappe.get_value(
			"Work Order Operation", self.operation_id, "quality_inspection_required"
		)
		if not (bom_inspection_required and operation_inspection_required):
			return

		if not self.quality_inspection:
			frappe.throw(
				_(
					"Quality Inspection is required for the item {0} before completing the job card {1}"
				).format(get_link_to_form("Item", self.finished_good), bold(self.name))
			)

		action_submit, action_reject = frappe.get_single_value(
			"Stock Settings",
			["action_if_quality_inspection_is_not_submitted", "action_if_quality_inspection_is_rejected"],
		)

		qa_status, docstatus = frappe.get_value(
			"Quality Inspection", self.quality_inspection, ["status", "docstatus"]
		)
		if docstatus != 1:
			self.handle_unsubmitted_inspection(action_submit)
		elif qa_status == "Rejected":
			self.handle_rejected_inspection(action_reject)

	def handle_unsubmitted_inspection(self, action_submit):
		message = _("Quality Inspection {0} is not submitted for the item: {1}").format(
			get_link_to_form("Quality Inspection", self.quality_inspection),
			get_link_to_form("Item", self.finished_good),
		)
		if action_submit == "Stop":
			frappe.throw(message, title=_("Inspection Submission"), exc=QualityInspectionNotSubmittedError)
		else:
			frappe.msgprint(message, alert=True, indicator="orange")

	def handle_rejected_inspection(self, action_reject):
		message = _("Quality Inspection {0} is rejected for the item: {1}").format(
			get_link_to_form("Quality Inspection", self.quality_inspection),
			get_link_to_form("Item", self.finished_good),
		)
		if action_reject == "Stop":
			frappe.throw(message, title=_("Inspection Rejected"), exc=QualityInspectionRejectedError)
		else:
			frappe.msgprint(message, alert=True, indicator="orange")

	def validate_transfer_qty(self):
		if (
			not self.finished_good
			and not self.is_corrective_job_card
			and self.items
			and self.transferred_qty < self.for_quantity
		):
			frappe.throw(
				_(
					"Materials need to be transferred to the work in progress warehouse for the job card {0}"
				).format(self.name)
			)

	def validate_job_card(self):
		if self.work_order and frappe.get_cached_value("Work Order", self.work_order, "status") == "Stopped":
			frappe.throw(
				_("Transaction not allowed against stopped Work Order {0}").format(
					get_link_to_form("Work Order", self.work_order)
				)
			)

		self.validate_not_on_hold()
		self.validate_time_logs_present()
		self.validate_completed_qty_matches_for_quantity()

	def validate_not_on_hold(self):
		if self.is_paused:
			frappe.throw(
				_(
					"Cannot submit Job Card {0} while it is On Hold. Please resume and complete the job before submission."
				).format(get_link_to_form("Job Card", self.name)),
				title=_("Job Card On Hold"),
			)

	def validate_time_logs_present(self):
		if self.track_semi_finished_goods and self.is_subcontracted:
			return

		if not self.time_logs:
			frappe.throw(
				_("Time logs are required for {0} {1}").format(
					bold("Job Card"), get_link_to_form("Job Card", self.name)
				)
			)
		elif frappe.db.get_single_value("Manufacturing Settings", "enforce_time_logs"):
			for row in self.time_logs:
				if not row.from_time or not row.to_time:
					frappe.throw(
						_("Row #{0}: From Time and To Time fields are required").format(row.idx),
					)

	def validate_completed_qty_matches_for_quantity(self):
		if self.track_semi_finished_goods and self.is_subcontracted:
			return

		precision = self.precision("total_completed_qty")
		total_completed_qty = flt(
			flt(self.total_completed_qty, precision)
			+ flt(self.process_loss_qty, precision)
			+ flt(self.pending_qty, precision)
		)

		if self.for_quantity and flt(total_completed_qty, precision) != flt(self.for_quantity, precision):
			frappe.throw(
				_("The {0} ({1}) must be equal to {2} ({3})").format(
					bold(_("Total Completed Qty")),
					bold(flt(total_completed_qty, precision)),
					bold(_("Qty to Manufacture")),
					bold(self.for_quantity),
				)
			)

	def set_expected_and_actual_time(self):
		for child_table, start_field, end_field, time_required in [
			("scheduled_time_logs", "expected_start_date", "expected_end_date", "time_required"),
			("time_logs", "actual_start_date", "actual_end_date", "total_time_in_mins"),
		]:
			if not self.get(child_table):
				continue

			if self.set_time_for_child_table(child_table, start_field, end_field, time_required):
				return

	def set_time_for_child_table(self, child_table, start_field, end_field, time_required):
		time_list = []
		time_in_mins = 0.0
		for row in self.get(child_table):
			time_in_mins += flt(row.get("time_in_mins"))
			for field in ["from_time", "to_time"]:
				if row.get(field):
					time_list.append(get_datetime(row.get(field)))

		if time_list:
			self.set(start_field, min(time_list))
			if end_field == "actual_end_date" and not self.time_logs[-1].to_time:
				self.set(end_field, "")
				return True

			self.set(end_field, max(time_list))

		self.set(time_required, time_in_mins)
		return False

	def set_process_loss(self):
		precision = self.precision("total_completed_qty")

		self.process_loss_qty = 0.0
		if self.total_completed_qty and self.for_quantity > self.total_completed_qty:
			self.process_loss_qty = (
				flt(self.for_quantity, precision)
				- flt(self.total_completed_qty, precision)
				- flt(self.pending_qty, precision)
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

		for_quantity, time_in_mins, process_loss_qty, pending_qty = self.get_operation_totals()

		wo = frappe.get_doc("Work Order", self.work_order)

		if self.is_corrective_job_card:
			self.update_corrective_in_work_order(wo)

		elif self.operation_id:
			self.validate_produced_quantity(for_quantity, process_loss_qty, pending_qty, wo)
			self.update_work_order_data(for_quantity, process_loss_qty, pending_qty, time_in_mins, wo)

	def get_operation_totals(self):
		for_quantity, time_in_mins, process_loss_qty, pending_qty = 0, 0, 0, 0

		data = self.get_current_operation_data()
		if data and len(data) > 0:
			for_quantity = flt(data[0].completed_qty)
			time_in_mins = flt(data[0].time_in_mins)
			process_loss_qty = flt(data[0].process_loss_qty)
			pending_qty = flt(data[0].pending_qty)

		return for_quantity, time_in_mins, process_loss_qty, pending_qty

	def update_semi_finished_good_details(self):
		if self.operation_id:
			qty = max(flt(self.manufactured_qty), flt(self.total_completed_qty))

			frappe.db.set_value("Work Order Operation", self.operation_id, "completed_qty", qty)
			if (
				self.finished_good
				and frappe.get_cached_value("Work Order", self.work_order, "production_item")
				== self.finished_good
			):
				_wo_doc = frappe.get_doc("Work Order", self.work_order)
				_wo_doc.db_set("produced_qty", self.manufactured_qty)
				_wo_doc.db_set("status", _wo_doc.get_status())

	def update_corrective_in_work_order(self, wo):
		wo.corrective_operation_cost = 0.0
		for row in frappe.get_all(
			"Job Card",
			fields=["total_time_in_mins", "hour_rate"],
			filters={"is_corrective_job_card": 1, "docstatus": 1, "work_order": self.work_order},
		):
			wo.corrective_operation_cost += flt(row.total_time_in_mins / 60) * flt(row.hour_rate)

		wo.calculate_operating_cost()
		wo.flags.ignore_validate_update_after_submit = True
		wo.save()

	def validate_produced_quantity(self, for_quantity, process_loss_qty, pending_qty, wo):
		if self.docstatus < 2:
			return

		if wo.produced_qty > for_quantity + process_loss_qty + pending_qty:
			first_part_msg = _(
				"The {0} {1} is used to calculate the valuation cost for the finished good {2}."
			).format(frappe.bold(_("Job Card")), frappe.bold(self.name), frappe.bold(self.production_item))

			second_part_msg = _(
				"Kindly cancel the Manufacturing Entries first against the work order {0}."
			).format(frappe.bold(get_link_to_form("Work Order", self.work_order)))

			frappe.throw(
				_("{0} {1}").format(first_part_msg, second_part_msg), JobCardCancelError, title=_("Error")
			)

	def update_work_order_data(self, for_quantity, process_loss_qty, pending_qty, time_in_mins, wo):
		time_data = self.get_operation_time_data()

		for data in wo.operations:
			if data.get("name") == self.operation_id:
				self.update_wo_operation_row(
					data, for_quantity, process_loss_qty, pending_qty, time_in_mins, time_data
				)

		wo.flags.ignore_validate_update_after_submit = True
		wo.update_operation_status()
		wo.calculate_operating_cost()
		wo.set_actual_dates()

		if time_data:
			wo.status = "In Process"

		wo.save()

	def get_operation_time_data(self):
		jc = frappe.qb.DocType("Job Card")
		jctl = frappe.qb.DocType("Job Card Time Log")

		return (
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

	def update_wo_operation_row(
		self, data, for_quantity, process_loss_qty, pending_qty, time_in_mins, time_data
	):
		data.completed_qty = for_quantity
		data.process_loss_qty = process_loss_qty
		data.pending_qty = pending_qty
		data.actual_operation_time = time_in_mins
		data.actual_start_time = time_data[0].start_time if time_data else None
		data.actual_end_time = time_data[0].end_time if time_data else None
		if data.get("workstation") != self.workstation:
			# workstations can change in a job card
			data.workstation = self.workstation
			data.hour_rate = flt(frappe.get_value("Workstation", self.workstation, "hour_rate"))

	def get_current_operation_data(self):
		return frappe.get_all(
			"Job Card",
			fields=[
				{"SUM": "total_time_in_mins", "as": "time_in_mins"},
				{"SUM": "total_completed_qty", "as": "completed_qty"},
				{"SUM": "process_loss_qty", "as": "process_loss_qty"},
				{"SUM": "pending_qty", "as": "pending_qty"},
			],
			filters={
				"docstatus": 1,
				"work_order": self.work_order,
				"operation_id": self.operation_id,
				"is_corrective_job_card": 0,
			},
		)

	def set_consumed_qty_in_job_card_item(self, ste_doc):
		jc_item_names = [row.job_card_item for row in ste_doc.get("items") if row.get("job_card_item")]

		if not jc_item_names:
			return

		se = frappe.qb.DocType("Stock Entry")
		sed = frappe.qb.DocType("Stock Entry Detail")

		query = (
			frappe.qb.from_(sed)
			.join(se)
			.on(sed.parent == se.name)
			.select(sed.job_card_item, Sum(sed.qty))
			.where(
				(sed.job_card_item.isin(jc_item_names)) & (se.docstatus == 1) & (se.purpose == "Manufacture")
			)
			.groupby(sed.job_card_item)
		)

		itemwise_consumed_qty = frappe._dict(query.run(as_list=True))

		for row in ste_doc.items:
			if not row.get("job_card_item"):
				continue

			consumed_qty = flt(itemwise_consumed_qty.get(row.job_card_item, 0.0))

			frappe.db.set_value("Job Card Item", row.job_card_item, "consumed_qty", consumed_qty)

	def set_transferred_qty_in_job_card_item(self, ste_doc):
		job_card_items_transferred_qty = self.get_job_card_items_transferred_qty(ste_doc) or {}
		allow_excess = frappe.db.get_single_value("Manufacturing Settings", "job_card_excess_transfer")

		for row in ste_doc.items:
			if not row.job_card_item:
				continue

			transferred_qty = flt(job_card_items_transferred_qty.get(row.job_card_item, 0.0))

			if not allow_excess:
				self.validate_over_transfer(ste_doc, row, transferred_qty)

			frappe.db.set_value("Job Card Item", row.job_card_item, "transferred_qty", flt(transferred_qty))

		self.set_status(update_status=True)

	def get_job_card_items_transferred_qty(self, ste_doc):
		from frappe.query_builder.functions import Sum

		job_card_items = [x.get("job_card_item") for x in ste_doc.get("items") if x.get("job_card_item")]
		if not job_card_items:
			return {}

		se = frappe.qb.DocType("Stock Entry")
		sed = frappe.qb.DocType("Stock Entry Detail")

		query = (
			frappe.qb.from_(sed)
			.join(se)
			.on(sed.parent == se.name)
			.select(sed.job_card_item, Sum(sed.qty))
			.where(
				(sed.job_card_item.isin(job_card_items))
				& (se.docstatus == 1)
				& (se.purpose == "Material Transfer for Manufacture")
			)
			.groupby(sed.job_card_item)
		)

		return frappe._dict(query.run(as_list=True))

	def validate_over_transfer(self, ste_doc, row, transferred_qty):
		"Block over transfer of items if not allowed in settings."
		required_qty = frappe.db.get_value("Job Card Item", row.job_card_item, "required_qty")
		if flt(transferred_qty) > flt(required_qty):
			frappe.throw(
				_(
					"Row #{0}: Cannot transfer more than Required Qty {1} for Item {2} against Job Card {3}"
				).format(row.idx, frappe.bold(required_qty), frappe.bold(row.item_code), ste_doc.job_card),
				title=_("Excess Transfer"),
				exc=JobCardOverTransferError,
			)

	def set_transferred_qty(self, update_status=False):
		self.db_set("transferred_qty", self.get_transferred_qty_from_stock_entry())
		self.set_status(update_status)

		if self.work_order and not frappe.get_cached_value(
			"Work Order", self.work_order, "track_semi_finished_goods"
		):
			self.set_transferred_qty_in_work_order()

	def get_transferred_qty_from_stock_entry(self):
		from frappe.query_builder.functions import Sum

		stock_entry = frappe.qb.DocType("Stock Entry")

		result = (
			frappe.qb.from_(stock_entry)
			.select(Sum(stock_entry.fg_completed_qty))
			.where(
				(stock_entry.job_card == self.name)
				& (stock_entry.docstatus == 1)
				& (stock_entry.purpose == "Material Transfer for Manufacture")
			)
			.groupby(stock_entry.job_card)
		).run()

		return flt(result[0][0]) if result and result[0][0] else 0

	def set_transferred_qty_in_work_order(self):
		doc = frappe.get_doc("Work Order", self.work_order)

		if doc.transfer_material_against == "Job Card" and not doc.skip_transfer:
			qty = self.get_min_completed_operation_qty(doc)
			doc.db_set("material_transferred_for_manufacturing", qty)

	def get_min_completed_operation_qty(self, doc):
		min_qty = []
		for d in doc.operations:
			completed_qty = flt(d.completed_qty) + flt(d.process_loss_qty)
			if completed_qty:
				min_qty.append(completed_qty)
			else:
				min_qty = []
				break

		return min(min_qty) if min_qty else 0.0

	def set_status(self, update_status=False):
		self.status = {0: "Open", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]
		if self.finished_good and self.docstatus == 1:
			self.set_finished_good_status()

		if self.docstatus == 0 and self.time_logs:
			self.status = "Work In Progress"

		if not self.track_semi_finished_goods and self.docstatus < 2:
			self.set_non_semi_fg_status()

		if self.is_paused:
			self.status = "On Hold"

		if update_status:
			self.db_set("status", self.status)

		if self.workstation:
			self.update_workstation_status()

	def set_finished_good_status(self):
		# Only reached for a submitted job card (docstatus == 1) with a finished good, see set_status().
		if (self.manufactured_qty + self.process_loss_qty) >= self.for_quantity:
			self.status = "Completed"
		elif (self.total_completed_qty + self.process_loss_qty) >= self.for_quantity:
			# Production is done and the card is submitted, but the finished goods have not been
			# booked into stock yet (Manufacture Stock Entry pending) — distinct from active WIP.
			self.status = "To Manufacture"
		elif self.transferred_qty > 0 or self.skip_material_transfer:
			self.status = "Work In Progress"

	def set_non_semi_fg_status(self):
		if self.items:
			item_data = frappe.get_all(
				"Job Card Item",
				filters={"parent": self.name},
				fields=["transferred_qty", "required_qty"],
			)
			all_transferred = item_data and all(
				flt(d.transferred_qty) >= flt(d.required_qty) for d in item_data
			)
			any_transferred = any(flt(d.transferred_qty) > 0 for d in item_data)

			if all_transferred:
				self.status = "Material Transferred"
			elif any_transferred:
				self.status = "Partially Transferred"
		elif flt(self.for_quantity) <= flt(self.transferred_qty):
			self.status = "Material Transferred"

		if self.time_logs:
			self.status = "Work In Progress"

		if self.docstatus == 1 and (
			self.for_quantity <= (self.total_completed_qty + self.process_loss_qty) or not self.items
		):
			self.status = "Completed"

	def set_wip_warehouse(self):
		if not self.wip_warehouse:
			self.wip_warehouse = frappe.get_cached_value("Company", self.company, "default_wip_warehouse")

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

	@frappe.whitelist()
	def pause_job(self, **kwargs):
		frappe.has_permission("Job Card", "write", doc=self, throw=True)

		self.validate_docstatus()

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		self.db_set("is_paused", 1)
		self.add_time_logs(to_time=kwargs.end_time, completed_qty=0.0, employees=self.employee)

	@frappe.whitelist()
	def resume_job(self, **kwargs):
		frappe.has_permission("Job Card", "write", doc=self, throw=True)

		self.validate_docstatus()

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		self.db_set("is_paused", 0)
		self.add_time_logs(
			from_time=kwargs.start_time,
			employees=self.employee,
			completed_qty=0.0,
		)

	def validate_sequence_id(self):
		if self.is_new() or self.is_corrective_job_card:
			return

		if not (self.work_order and self.sequence_id):
			return

		current_operation_qty = self.get_current_operation_completed_qty()

		previous_operations = frappe.get_all(
			"Work Order Operation",
			fields=["operation", "status", "completed_qty", "sequence_id"],
			filters={"docstatus": 1, "parent": self.work_order, "sequence_id": ("<", self.sequence_id)},
			order_by="sequence_id, idx",
		)

		for row in previous_operations:
			self.validate_previous_operation(row, current_operation_qty)

	def get_current_operation_completed_qty(self):
		current_operation_qty = 0.0
		data = self.get_current_operation_data()
		if data and len(data) > 0:
			current_operation_qty = flt(data[0].completed_qty)

		return current_operation_qty + flt(self.total_completed_qty)

	def validate_previous_operation(self, row, current_operation_qty):
		if not row.completed_qty or (row.status != "Completed" and row.completed_qty < current_operation_qty):
			frappe.throw(
				_(
					"Job Card {0}: As per the sequence of the operations in the work order {1}, complete the operation {2} before the operation {3}."
				).format(
					bold(self.name),
					bold(get_link_to_form("Work Order", self.work_order)),
					bold(row.operation),
					bold(self.operation),
				),
				OperationSequenceError,
			)

		if row.completed_qty < current_operation_qty:
			frappe.throw(
				_(
					"The completed quantity {0} of an operation {1} cannot be greater than the completed quantity {2} of a previous operation {3}."
				).format(
					bold(current_operation_qty),
					bold(self.operation),
					bold(row.completed_qty),
					bold(row.operation),
				)
			)

	def validate_work_order(self):
		if self.is_work_order_closed():
			frappe.throw(_("You cannot make any changes to Job Card since Work Order is closed."))

	def set_employees(self):
		self.employee = []
		for item in self.time_logs:
			if not any(d.employee == item.employee for d in self.employee):
				self.append("employee", {"employee": item.employee, "completed_qty": 0.0})

	def is_work_order_closed(self):
		if self.work_order:
			status = frappe.get_value("Work Order", self.work_order, "status")

			if status in ["Closed", "Stopped"]:
				return True

		return False

	def update_status_in_workstation(self, status):
		if not self.workstation:
			return

		frappe.db.set_value("Workstation", self.workstation, "status", status)

	def add_time_logs(self, **kwargs):
		kwargs = frappe._dict(kwargs)
		if not kwargs.employees and kwargs.to_time:
			for row in self.time_logs:
				if not row.to_time and row.from_time:
					row.to_time = kwargs.to_time
					row.time_in_mins = time_diff_in_minutes(row.to_time, row.from_time)

					if kwargs.completed_qty:
						row.completed_qty = kwargs.completed_qty
					row.db_update()
		else:
			self.add_time_logs_for_employess(kwargs)

		self.validate_time_logs(save=True)
		self.save()

	def add_time_logs_for_employess(self, kwargs):
		update_status = False

		for employee in kwargs.employees:
			kwargs.employee = employee.get("employee")
			if kwargs.from_time and not kwargs.to_time:
				self.add_new_time_log_for_employee(kwargs)
			elif not kwargs.from_time and not kwargs.to_time and kwargs.completed_qty:
				self.update_completed_qty_for_employee(kwargs)
				update_status = True
			else:
				self.close_time_log_for_employee(kwargs)
				update_status = True

			self.set_status(update_status=update_status)

	def add_new_time_log_for_employee(self, kwargs):
		if kwargs.qty:
			kwargs.completed_qty = kwargs.qty

		row = self.append("time_logs", kwargs)
		row.db_update()
		self.db_set("status", "Work In Progress")

	def update_completed_qty_for_employee(self, kwargs):
		for row in self.time_logs:
			if row.employee != kwargs.employee:
				continue

			row.completed_qty = kwargs.completed_qty
			row.db_update()

	def close_time_log_for_employee(self, kwargs):
		for row in self.time_logs:
			if row.to_time or row.employee != kwargs.employee:
				continue

			row.to_time = kwargs.to_time
			row.time_in_mins = time_diff_in_minutes(row.to_time, row.from_time)
			if kwargs.get("sub_operation"):
				row.operation = kwargs.get("sub_operation")

			if kwargs.employees[-1].get("employee") == row.employee:
				row.completed_qty = kwargs.completed_qty

			row.db_update()

	def update_workstation_status(self):
		status_map = {
			"Open": "Off",
			"Work In Progress": "Production",
			"Completed": "Off",
			"On Hold": "Idle",
		}

		job_cards = frappe.get_all(
			"Job Card",
			fields=["name", "status"],
			filters={"workstation": self.workstation, "docstatus": 0, "status": ("!=", "Completed")},
			order_by="status desc",
		)

		if not job_cards:
			frappe.db.set_value("Workstation", self.workstation, "status", "Off")

		for row in job_cards:
			frappe.db.set_value("Workstation", self.workstation, "status", status_map.get(row.status))
			return

	@frappe.whitelist()
	def start_timer(self, **kwargs):
		frappe.has_permission("Job Card", "write", doc=self, throw=True)

		self.validate_docstatus()

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		if isinstance(kwargs.employees, str):
			kwargs.employees = [{"employee": kwargs.employees}]

		if kwargs.start_time:
			self.add_time_logs(from_time=kwargs.start_time, employees=kwargs.employees)

	@frappe.whitelist()
	def complete_job_card(self, **kwargs):
		frappe.has_permission("Job Card", "write", doc=self, throw=True)

		self.validate_docstatus()

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		self.validate_complete_job_card_qty(kwargs)

		self.pending_qty = flt(kwargs.pending_qty)
		self.process_loss_qty = flt(kwargs.process_loss_qty)

		self.add_completion_time_logs(kwargs)

		if kwargs.auto_submit:
			self.auto_submit_job_card(kwargs.auto_submit)

	def validate_docstatus(self):
		if self.docstatus == 2:
			frappe.throw(_("Cancelled Job Card cannot be processed."))

		if self.docstatus == 1:
			frappe.throw(_("Submitted Job Card cannot be processed."))

	def validate_complete_job_card_qty(self, kwargs):
		if flt(kwargs.pending_qty) and flt(kwargs.pending_qty) < 0:
			frappe.throw(_("Pending quantity cannot be negative."))

		if flt(kwargs.process_loss_qty) and flt(kwargs.process_loss_qty) < 0:
			frappe.throw(_("Process loss quantity cannot be negative."))

		if flt(kwargs.pending_qty) and flt(kwargs.pending_qty) > self.for_quantity:
			frappe.throw(_("Pending quantity cannot be greater than the for quantity."))

	def add_completion_time_logs(self, kwargs):
		if kwargs.end_time:
			self.add_time_logs(
				to_time=kwargs.end_time,
				completed_qty=kwargs.qty,
				employees=self.employee,
				sub_operation=kwargs.get("sub_operation"),
			)

			if self.docstatus == 1:
				self.update_work_order()
		else:
			self.add_time_logs(completed_qty=kwargs.qty, employees=self.employee)
			self.save()

	def auto_submit_job_card(self, auto_submit):
		self.submit()

		if not self.finished_good:
			return

		self.make_stock_entry_for_semi_fg_item(auto_submit)
		frappe.msgprint(_("Job Card {0} has been completed").format(get_link_to_form("Job Card", self.name)))

	@frappe.whitelist()
	def make_stock_entry_for_semi_fg_item(self, auto_submit: bool = False):
		frappe.has_permission("Job Card", "write", doc=self, throw=True)
		frappe.has_permission("Stock Entry", "create", throw=True)

		ste = self.build_manufacture_stock_entry()
		self.populate_manufacture_stock_entry(ste)

		if auto_submit:
			ste.stock_entry.submit()
		else:
			ste.stock_entry.save()

		frappe.msgprint(
			_("Stock Entry {0} has been created").format(
				get_link_to_form("Stock Entry", ste.stock_entry.name)
			)
		)

		return ste.stock_entry.as_dict()

	def get_consumed_process_loss(self):
		table = frappe.qb.DocType("Stock Entry")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.process_loss_qty))
			.where((table.purpose == "Manufacture") & (table.job_card == self.name) & (table.docstatus == 1))
		)
		return query.run()[0][0] or 0

	def build_manufacture_stock_entry(self):
		from erpnext.stock.doctype.stock_entry_type.stock_entry_type import ManufactureEntry

		return ManufactureEntry(
			{
				"for_quantity": self.for_quantity - self.manufactured_qty,
				"process_loss_qty": max(self.process_loss_qty - self.get_consumed_process_loss(), 0),
				"job_card": self.name,
				"skip_material_transfer": self.skip_material_transfer,
				"backflush_from_wip_warehouse": self.backflush_from_wip_warehouse,
				"work_order": self.work_order,
				"purpose": "Manufacture",
				"production_item": self.finished_good,
				"company": self.company,
				"wip_warehouse": self.wip_warehouse,
				"fg_warehouse": self.target_warehouse,
				"bom_no": self.semi_fg_bom,
				"project": frappe.db.get_value("Work Order", self.work_order, "project"),
			}
		)

	def populate_manufacture_stock_entry(self, ste):
		from erpnext.stock.doctype.stock_entry.services.manufacturing import ManufactureStockEntry

		ste.make_stock_entry()
		ste.stock_entry.flags.ignore_mandatory = True
		wo_doc = frappe.get_doc("Work Order", self.work_order)
		add_additional_cost(ste.stock_entry, wo_doc, self)
		ManufactureStockEntry(ste.stock_entry).add_secondary_items_from_job_card()
		for row in ste.stock_entry.items:
			if (row.secondary_item_type or row.is_legacy_scrap_item) and not row.t_warehouse:
				row.t_warehouse = self.target_warehouse


@frappe.whitelist()
def make_time_log(kwargs: str | dict):
	kwargs = frappe.parse_json(kwargs)

	kwargs = frappe._dict(kwargs)
	doc = frappe.get_doc("Job Card", kwargs.job_card_id)
	frappe.has_permission("Job Card", "write", doc=doc, throw=True)
	doc.validate_sequence_id()
	doc.add_time_log(kwargs)
	doc.set_status(update_status=True)


@frappe.whitelist()
def get_operation_details(work_order: str, operation: str):
	frappe.has_permission("Work Order", "read", throw=True)

	if work_order and operation:
		return frappe.get_all(
			"Work Order Operation",
			fields=["name", "idx"],
			filters={"parent": work_order, "operation": operation},
		)


@frappe.whitelist()
def get_operations(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	frappe.has_permission("Work Order", "read", throw=True)

	if not filters.get("work_order"):
		frappe.msgprint(_("Please select a Work Order first."))
		return []
	args = {"parent": filters.get("work_order")}
	if txt:
		args["operation"] = ("like", f"%{txt}%")

	return frappe.get_all(
		"Work Order Operation",
		filters=args,
		fields=["operation"],
		limit_start=start,
		limit_page_length=page_len,
		order_by="idx asc",  # pg-ok: dropped under distinct on PG — paging order of an operation autocomplete only
		as_list=1,
		distinct=True,
	)


def time_diff_in_minutes(string_ed_date, string_st_date):
	return time_diff(string_ed_date, string_st_date).total_seconds() / 60


# Maps a filter operator to a callable that builds the query builder condition
# for a given column and value. Avoids a long if/elif chain.
FILTER_OPERATORS = {
	"=": lambda column, value: column == value,
	"!=": lambda column, value: column != value,
	">": lambda column, value: column > value,
	"<": lambda column, value: column < value,
	">=": lambda column, value: column >= value,
	"<=": lambda column, value: column <= value,
	"like": lambda column, value: column.like(value),
	"not like": lambda column, value: column.not_like(value),
	"in": lambda column, value: column.isin(value),
	"not in": lambda column, value: column.notin(value),
	"between": lambda column, value: column.between(value[0], value[1]),
	"is": lambda column, value: (
		(column.isnotnull() & (column != "")) if value == "set" else (column.isnull() | (column == ""))
	),
}


def get_job_card_filter_conditions(jc, filters):
	"""Build query builder conditions for the calendar filters on the Job Card table.

	Replaces the previous raw SQL ``get_filters_cond`` based filtering so that all
	user supplied values are passed as bound parameters via the query builder.
	"""
	filters = frappe.parse_json(filters)

	if not filters:
		return []

	conditions = []
	for field, operator, value in normalize_calendar_filters(filters):
		builder = FILTER_OPERATORS.get((operator or "=").lower())
		if builder:
			conditions.append(builder(jc[field], value))

	return conditions


def normalize_calendar_filters(filters):
	"""Normalize the supported filter formats into (field, operator, value) tuples."""
	if isinstance(filters, dict):
		return normalize_dict_filters(filters)

	normalized = []
	for f in filters:
		f = list(f)
		if len(f) == 4:
			# [doctype, fieldname, operator, value]
			normalized.append((f[1], f[2], f[3]))
		elif len(f) == 3:
			normalized.append((f[0], f[1], f[2]))
		elif len(f) == 2:
			normalized.append((f[0], "=", f[1]))

	return normalized


def normalize_dict_filters(filters):
	normalized = []
	for field, value in filters.items():
		if isinstance(value, list | tuple) and len(value) == 2:
			normalized.append((field, value[0], value[1]))
		elif isinstance(value, str) and value.startswith("!"):
			normalized.append((field, "!=", value[1:]))
		else:
			normalized.append((field, "=", value))

	return normalized


@frappe.whitelist()
def get_job_details(start: Any, end: Any, filters: str | dict | None = None):
	if not frappe.has_permission("Job Card", "read"):
		frappe.throw(_("Not permitted to read Job Card"), frappe.PermissionError)

	job_cards = get_job_cards_for_calendar(filters)

	return [get_calendar_event(d) for d in job_cards]


def get_job_cards_for_calendar(filters):
	jc = frappe.qb.DocType("Job Card")
	jctl = frappe.qb.DocType("Job Card Time Log")

	query = (
		frappe.qb.from_(jc)
		.from_(jctl)
		.select(
			jc.name,
			jc.work_order,
			jc.status,
			IfNull(jc.remarks, "").as_("remarks"),
			Min(jctl.from_time).as_("from_time"),
			Max(jctl.to_time).as_("to_time"),
		)
		.where(jc.name == jctl.parent)
		.groupby(jc.name)
	)

	for condition in get_job_card_filter_conditions(jc, filters):
		query = query.where(condition)

	return query.run(as_dict=True)


def get_calendar_event(d):
	event_color = {
		"Completed": "#cdf5a6",
		"Material Transferred": "#ffdd9e",
		"Partially Transferred": "#ffe5b4",
		"Work In Progress": "#D3D3D3",
	}

	subject_data = [d.get(field) for field in ["name", "work_order", "remarks"] if d.get(field)]
	color = event_color.get(d.status)

	return {
		"from_time": d.from_time,
		"to_time": d.to_time,
		"name": d.name,
		"subject": "\n".join(subject_data),
		"color": color if color else "#89bcde",
	}
