# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe.utils import cint, flt, get_datetime, get_time
from pypika.terms import ExistsCriterion

from erpnext.manufacturing.scheduling.models import Interval, Resource, ResourceCalendar, Task


def get_workstation_resources(workstations=None, workstation_type=None):
	filters = {"disabled": 0}
	if workstations:
		filters["name"] = ("in", workstations)
	if workstation_type:
		filters["workstation_type"] = workstation_type

	rows = frappe.get_all(
		"Workstation",
		filters=filters,
		fields=["name", "production_capacity", "workstation_type", "holiday_list"],
	)

	settings = frappe.get_cached_doc("Manufacturing Settings")
	return [get_resource(row, settings) for row in rows]


def get_resource(row, settings):
	return Resource(
		name=row.name,
		capacity=cint(row.production_capacity) or 1,
		resource_type=row.workstation_type,
		calendar=get_workstation_calendar(row, settings),
	)


def get_workstation_calendar(row, settings):
	daily_windows = []
	if not cint(settings.allow_overtime):
		daily_windows = [
			(get_time(slot.start_time), get_time(slot.end_time))
			for slot in frappe.get_all(
				"Workstation Working Hour",
				filters={"parent": row.name, "enabled": 1},
				fields=["start_time", "end_time"],
				order_by="idx",
			)
		]

	holidays = set()
	if row.holiday_list and not cint(settings.allow_production_on_holidays):
		holidays = set(frappe.get_all("Holiday", filters={"parent": row.holiday_list}, pluck="holiday_date"))

	return ResourceCalendar(daily_windows=daily_windows, holidays=holidays)


def get_booked_load(resource_names, from_date, exclude_plan=None):
	load = defaultdict(list)
	add_booked_intervals(load, "Job Card Scheduled Time", resource_names, from_date, drafts_only=True)
	add_booked_intervals(load, "Job Card Time Log", resource_names, from_date, drafts_only=False)
	add_plan_schedule_intervals(load, resource_names, from_date, exclude_plan)
	return load


def add_booked_intervals(load, doctype, resource_names, from_date, drafts_only):
	child = frappe.qb.DocType(doctype)
	job_card = frappe.qb.DocType("Job Card")

	query = (
		frappe.qb.from_(child)
		.join(job_card)
		.on(child.parent == job_card.name)
		.select(job_card.workstation, child.from_time, child.to_time)
		.where(
			job_card.workstation.isin(resource_names) & child.to_time.notnull() & (child.to_time > from_date)
		)
	)

	if drafts_only:
		query = query.where((job_card.docstatus == 0) & (job_card.total_time_in_mins == 0))
	else:
		query = query.where(job_card.docstatus < 2)

	for row in query.run(as_dict=True):
		load[row.workstation].append(Interval(get_datetime(row.from_time), get_datetime(row.to_time)))


def add_plan_schedule_intervals(load, resource_names, from_date, exclude_plan):
	schedule = frappe.qb.DocType("Production Plan Schedule")
	plan = frappe.qb.DocType("Production Plan")

	query = (
		frappe.qb.from_(schedule)
		.join(plan)
		.on(schedule.production_plan == plan.name)
		.select(schedule.workstation, schedule.from_time, schedule.to_time)
		.where(
			schedule.workstation.isin(resource_names)
			& (schedule.to_time > from_date)
			& (plan.docstatus < 2)
			& (plan.status != "Closed")
			& has_job_cards_for_schedule_row(schedule).negate()
		)
	)

	if exclude_plan:
		query = query.where(schedule.production_plan != exclude_plan)

	for row in query.run(as_dict=True):
		load[row.workstation].append(Interval(get_datetime(row.from_time), get_datetime(row.to_time)))


def has_job_cards_for_schedule_row(schedule):
	"""A schedule block steps aside only for job cards that already carry booked load
	(scheduled time or logged time). Batch-split or repeated-operation job cards created
	with capacity planning disabled carry neither, so the block keeps reserving capacity."""
	job_card = frappe.qb.DocType("Job Card")
	work_order = frappe.qb.DocType("Work Order")

	return ExistsCriterion(
		frappe.qb.from_(job_card)
		.join(work_order)
		.on(job_card.work_order == work_order.name)
		.select(job_card.name)
		.where(
			(job_card.docstatus < 2)
			& (work_order.production_plan == schedule.production_plan)
			& (job_card.operation == schedule.operation)
			& (has_scheduled_time(job_card) | (job_card.total_time_in_mins > 0))
			& (
				(work_order.production_plan_item == schedule.plan_row)
				| (work_order.production_plan_sub_assembly_item == schedule.plan_row)
			)
		)
	)


def has_scheduled_time(job_card):
	scheduled_time = frappe.qb.DocType("Job Card Scheduled Time")

	return ExistsCriterion(
		frappe.qb.from_(scheduled_time)
		.select(scheduled_time.name)
		.where(scheduled_time.parent == job_card.name)
	)


def build_bom_operation_tasks(bom_no, qty, prefix, earliest_start=None, priority=0):
	bom_qty = flt(frappe.get_cached_value("BOM", bom_no, "quantity")) or 1
	rows = frappe.get_all(
		"BOM Operation",
		filters={"parent": bom_no},
		fields=[
			"name",
			"operation",
			"workstation",
			"workstation_type",
			"time_in_mins",
			"fixed_time",
			"sequence_id",
		],
		order_by="idx",
	)

	tasks = []
	previous_group, current_group, current_sequence = [], [], None
	for row in rows:
		if current_group and (not row.sequence_id or row.sequence_id != current_sequence):
			previous_group, current_group = current_group, []

		task = build_operation_task(row, qty, bom_qty, prefix, previous_group, earliest_start, priority)
		tasks.append(task)
		current_group.append(task.key)
		current_sequence = row.sequence_id

	return tasks, current_group


def build_operation_task(row, qty, bom_qty, prefix, previous_group, earliest_start, priority):
	duration = flt(row.time_in_mins)
	if not row.fixed_time:
		duration = duration * qty / bom_qty

	return Task(
		key=f"{prefix}:{row.name}",
		duration_mins=duration,
		resource=row.workstation,
		resource_type=None if row.workstation else row.workstation_type,
		depends_on=list(previous_group),
		earliest_start=earliest_start,
		priority=priority,
		label=row.operation,
	)
