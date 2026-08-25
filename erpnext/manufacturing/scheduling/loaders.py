# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe.utils import cint, flt, get_datetime, get_time

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
		.select(
			schedule.workstation,
			schedule.from_time,
			schedule.to_time,
			schedule.production_plan,
			schedule.plan_row,
			schedule.operation,
		)
		.where(
			schedule.workstation.isin(resource_names)
			& (schedule.to_time > from_date)
			& (plan.docstatus < 2)
			& (plan.status != "Closed")
		)
	)

	if exclude_plan:
		query = query.where(schedule.production_plan != exclude_plan)

	for row in filter_covered_schedule_rows(query.run(as_dict=True)):
		load[row.workstation].append(Interval(get_datetime(row.from_time), get_datetime(row.to_time)))


def filter_covered_schedule_rows(rows):
	"""A schedule block steps aside only when job cards carrying booked load (scheduled
	time or logged time) cover the full quantity of its plan row and operation. Partial
	coverage - a batch-split card deleted, capacity planning disabled - keeps the block,
	trading double-booked load for never silently freeing a reserved interval."""
	plans = {row.production_plan for row in rows}
	if not plans:
		return rows

	required, carried = get_job_card_coverage(plans)
	return [row for row in rows if not is_operation_covered(row, required, carried)]


def is_operation_covered(row, required, carried):
	key = (row.production_plan, row.plan_row, row.operation)
	needed = required.get(key)
	return bool(needed) and flt(carried.get(key)) >= flt(needed)


def get_job_card_coverage(production_plans):
	work_orders = frappe.get_all(
		"Work Order",
		filters={"production_plan": ("in", list(production_plans)), "docstatus": ("<", 2)},
		fields=[
			"name",
			"qty",
			"production_plan",
			"production_plan_item",
			"production_plan_sub_assembly_item",
		],
	)
	if not work_orders:
		return {}, {}

	return get_required_operation_qty(work_orders), get_carried_operation_qty(work_orders)


def get_required_operation_qty(work_orders):
	by_name = {row.name: row for row in work_orders}
	required = defaultdict(float)
	for operation_row in frappe.get_all(
		"Work Order Operation", filters={"parent": ("in", list(by_name))}, fields=["parent", "operation"]
	):
		work_order = by_name[operation_row.parent]
		add_operation_qty(required, work_order, operation_row.operation, flt(work_order.qty))

	return required


def get_carried_operation_qty(work_orders):
	by_name = {row.name: row for row in work_orders}
	job_cards = frappe.get_all(
		"Job Card",
		filters={"work_order": ("in", list(by_name)), "docstatus": ("<", 2)},
		fields=["name", "work_order", "operation", "for_quantity", "total_time_in_mins"],
	)

	with_scheduled_time = get_job_cards_with_scheduled_time(job_cards)
	carried = defaultdict(float)
	for job_card in job_cards:
		if flt(job_card.total_time_in_mins) or job_card.name in with_scheduled_time:
			work_order = by_name[job_card.work_order]
			add_operation_qty(carried, work_order, job_card.operation, flt(job_card.for_quantity))

	return carried


def get_job_cards_with_scheduled_time(job_cards):
	names = [job_card.name for job_card in job_cards]
	if not names:
		return set()

	return set(frappe.get_all("Job Card Scheduled Time", filters={"parent": ("in", names)}, pluck="parent"))


def add_operation_qty(bucket, work_order, operation, qty):
	for plan_row in (work_order.production_plan_item, work_order.production_plan_sub_assembly_item):
		if plan_row:
			bucket[(work_order.production_plan, plan_row, operation)] += qty


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
