# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime
import math
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, get_datetime, getdate

from erpnext.manufacturing.scheduling import loaders
from erpnext.manufacturing.scheduling.engine import SchedulingEngine
from erpnext.manufacturing.scheduling.models import Task


@frappe.whitelist(methods=["GET"])
def get_schedule_preview(
	production_plan: str,
	start_date: str | datetime.datetime,
	use_item_dates: int | str = 0,
	item_dates: str | dict | None = None,
):
	plan = frappe.get_doc("Production Plan", production_plan)
	plan.check_permission("read")

	proposal = run_engine(plan, get_datetime(start_date), cint(use_item_dates), parse_item_dates(item_dates))
	proposal["orders_exist"] = has_orders_against_plan(plan)
	return proposal


@frappe.whitelist(methods=["POST"])
def apply_schedule(
	production_plan: str,
	start_date: str | datetime.datetime,
	use_item_dates: int | str = 0,
	item_dates: str | dict | None = None,
):
	plan = frappe.get_doc("Production Plan", production_plan)
	plan.check_permission("write")
	validate_plan_for_scheduling(plan)

	use_item_dates = cint(use_item_dates)
	item_dates = parse_item_dates(item_dates)
	proposal = run_engine(plan, get_datetime(start_date), use_item_dates, item_dates)
	validate_complete_proposal(proposal)
	replace_schedule_entries(plan, proposal)
	update_plan_row_dates(plan, proposal, use_item_dates, item_dates)
	plan.notify_update()

	return proposal


def parse_item_dates(item_dates):
	if not item_dates:
		return {}

	return {row: get_datetime(date) for row, date in frappe.parse_json(item_dates).items() if date}


def validate_complete_proposal(proposal):
	unscheduled = proposal.get("unscheduled") or {}
	if not unscheduled:
		return

	reasons = "<br>".join(f"{key}: {reason}" for key, reason in unscheduled.items())
	frappe.throw(
		_("Cannot apply an incomplete schedule. {0} task(s) could not be placed:<br>{1}").format(
			len(unscheduled), reasons
		)
	)


def validate_plan_for_scheduling(plan):
	if plan.docstatus == 2:
		frappe.throw(_("Cannot schedule a cancelled Production Plan"))

	if plan.status in ("Completed", "Closed"):
		frappe.throw(_("Cannot schedule a Production Plan with status {0}").format(_(plan.status)))

	if has_orders_against_plan(plan):
		frappe.throw(
			_(
				"Work Orders / Purchase Orders have already been created against this Production Plan. Cancel them before re-scheduling."
			)
		)


def has_orders_against_plan(plan):
	if frappe.db.exists("Work Order", {"production_plan": plan.name, "docstatus": ("<", 2)}):
		return True

	return bool(
		frappe.db.exists("Purchase Order Item", {"production_plan": plan.name, "docstatus": ("<", 2)})
	)


def run_engine(plan, start_date, use_item_dates=0, item_dates=None):
	tasks, task_info = build_plan_tasks(plan, use_item_dates, item_dates)
	settings = frappe.get_cached_doc("Manufacturing Settings")

	resources = loaders.get_workstation_resources()
	load = (
		loaders.get_booked_load([r.name for r in resources], start_date, exclude_plan=plan.name)
		if resources
		else {}
	)
	engine = SchedulingEngine(
		resources,
		existing_load=load,
		gap_mins=cint(settings.mins_between_operations) or 10,
		horizon_days=cint(settings.capacity_planning_for_days) or 365,
	)

	result = engine.schedule(tasks, anchor=start_date)
	return build_proposal(plan, result, task_info)


def build_plan_tasks(plan, use_item_dates=0, item_dates=None):
	ctx = get_build_context(plan)
	tasks, task_info = ctx.tasks, ctx.task_info

	for fg_row in plan.po_items:
		sub_rows = [row for row in plan.sub_assembly_items if row.production_plan_item == fg_row.name]
		row_bounds = build_sub_assembly_tasks(plan, sub_rows, ctx)
		fg_deps = get_finished_good_dependencies(fg_row, sub_rows, row_bounds)

		fg_tasks, first_keys, _terminal = build_row_tasks(
			plan, fg_row.bom_no, fg_row.item_code, flt(fg_row.planned_qty), False, fg_row.name, ctx
		)
		wire_dependencies(fg_tasks, fg_deps)
		wire_material_dependencies(
			fg_row.bom_no, get_first_tasks((first_keys, None, fg_tasks)), ctx, consumer_row=fg_row.name
		)
		register_tasks(fg_tasks, fg_row.name, "Finished Good", fg_row.item_code, tasks, task_info)

		if use_item_dates:
			row_date = (item_dates or {}).get(fg_row.name)
			if row_date:
				set_chain_earliest_start(row_date, sub_rows, row_bounds, fg_tasks)

	return tasks, task_info


def get_build_context(plan):
	bom_materials = get_bom_materials(plan)
	produced_items = {row.item_code for row in plan.po_items}
	produced_items.update(row.production_item for row in plan.sub_assembly_items)

	material_items = {
		item for items in bom_materials.values() for item in items if item not in produced_items
	}
	lead_times = get_lead_time_details(plan, material_items)
	supplier_lead_times = get_supplier_lead_times(material_items | produced_items)
	material_lead_days, material_suppliers = get_material_lead_days(
		material_items, lead_times, supplier_lead_times, get_chosen_suppliers(plan)
	)

	return frappe._dict(
		bom_materials={
			bom: [item for item in items if item not in produced_items]
			for bom, items in bom_materials.items()
		},
		lead_times=lead_times,
		supplier_lead_times=supplier_lead_times,
		material_lead_days=material_lead_days,
		material_suppliers=material_suppliers,
		material_tasks={},
		tasks=[],
		task_info={},
	)


def get_supplier_lead_times(item_codes):
	if not item_codes:
		return {}

	table = frappe.qb.DocType("Item Lead Time Supplier")
	rows = (
		frappe.qb.from_(table)
		.select(table.parent, table.supplier, table.purchase_time, table.buffer_time, table.is_default)
		.where(table.parent.isin(list(item_codes)) & (table.parenttype == "Item Lead Time"))
		.run(as_dict=True)
	)

	grouped = defaultdict(dict)
	for row in rows:
		grouped[row.parent][row.supplier] = row
	return dict(grouped)


def get_chosen_suppliers(plan):
	chosen = defaultdict(set)
	for row in plan.get("mr_items") or []:
		if row.get("supplier"):
			chosen[row.item_code].add(row.supplier)
	return chosen


def get_bom_materials(plan):
	boms = {row.bom_no for row in plan.po_items if row.bom_no}
	boms.update(row.bom_no for row in plan.sub_assembly_items if row.bom_no)
	if not boms:
		return {}

	materials = defaultdict(list)
	for row in frappe.get_all(
		"BOM Item",
		filters={"parent": ("in", list(boms)), "parenttype": "BOM"},
		fields=["parent", "item_code"],
	):
		materials[row.parent].append(row.item_code)

	return materials


def get_material_lead_days(material_items, lead_times, supplier_lead_times, chosen_suppliers):
	missing = [item for item in material_items if item not in lead_times and item not in supplier_lead_times]
	item_master_days = {}
	if missing:
		item_master_days = dict(
			frappe.get_all(
				"Item", filters={"name": ("in", missing)}, fields=["name", "lead_time_days"], as_list=True
			)
		)

	lead_days, suppliers = {}, {}
	for item in material_items:
		days, supplier = resolve_purchase_lead_time(
			lead_times.get(item), supplier_lead_times.get(item), chosen_suppliers.get(item)
		)
		lead_days[item] = cint(item_master_days.get(item)) if days is None else days
		if supplier:
			suppliers[item] = supplier

	return lead_days, suppliers


def resolve_purchase_lead_time(lead_time, supplier_rows, chosen_suppliers=None):
	rows = supplier_rows or {}
	item_days = cint(lead_time.purchase_time) + cint(lead_time.buffer_time) if lead_time else None

	candidates = []
	for supplier in chosen_suppliers or []:
		if supplier in rows:
			candidates.append(
				(cint(rows[supplier].purchase_time) + cint(rows[supplier].buffer_time), supplier)
			)
		elif item_days is not None:
			candidates.append((item_days, supplier))

	if candidates:
		return max(candidates)

	default_row = next((r for r in rows.values() if r.is_default), None)
	if default_row:
		return cint(default_row.purchase_time) + cint(default_row.buffer_time), default_row.supplier
	return (item_days, None) if lead_time else (None, None)


def wire_material_dependencies(bom_no, first_tasks, ctx, consumer_row=None):
	if not bom_no or not first_tasks:
		return

	dependency_keys = []
	for item_code in ctx.bom_materials.get(bom_no, []):
		lead_days = ctx.material_lead_days.get(item_code)
		if lead_days:
			dependency_keys.append(get_material_task(item_code, lead_days, ctx, consumer_row))

	if dependency_keys:
		wire_dependencies(first_tasks, dependency_keys)


def get_material_task(item_code, lead_days, ctx, consumer_row=None):
	key = f"material:{item_code}"
	if key not in ctx.material_tasks:
		task = Task(key=key, duration_mins=lead_days * 1440.0)
		ctx.material_tasks[key] = task
		ctx.tasks.append(task)
		ctx.task_info[key] = {
			"plan_row": key,
			"row_type": "Raw Material",
			"item_code": item_code,
			"operation": None,
			"parent_row": None,
			"supplier": ctx.material_suppliers.get(item_code),
			"consumers": [],
		}

	if consumer_row and consumer_row not in ctx.task_info[key]["consumers"]:
		ctx.task_info[key]["consumers"].append(consumer_row)

	return key


def set_chain_earliest_start(row_date, sub_rows, row_bounds, fg_tasks):
	earliest_start = get_datetime(row_date)
	chain_tasks = list(fg_tasks)
	for row in sub_rows:
		chain_tasks.extend(row_bounds[row.name][2])

	for task in chain_tasks:
		task.earliest_start = earliest_start


def build_sub_assembly_tasks(plan, sub_rows, ctx):
	row_bounds = {}
	row_suppliers = {}
	for row in sub_rows:
		subcontracted = row.type_of_manufacturing == "Subcontract"
		row_suppliers[row.name] = get_subcontract_supplier(row, ctx) if subcontracted else None
		row_tasks, first_keys, terminal_keys = build_row_tasks(
			plan,
			row.bom_no,
			row.production_item,
			flt(row.qty),
			subcontracted,
			row.name,
			ctx,
			row_suppliers[row.name],
		)
		row_bounds[row.name] = (first_keys, terminal_keys, row_tasks)
		if not subcontracted:
			wire_material_dependencies(
				row.bom_no, get_first_tasks(row_bounds[row.name]), ctx, consumer_row=row.name
			)

	rows_by_item = defaultdict(list)
	for row in sub_rows:
		rows_by_item[row.production_item].append(row)

	for row in sub_rows:
		parents = rows_by_item.get(row.parent_item_code) or []
		if parents:
			parent_first_tasks = get_first_tasks(row_bounds[parents[0].name])
			wire_dependencies(parent_first_tasks, row_bounds[row.name][1])

	for row in sub_rows:
		register_tasks(
			row_bounds[row.name][2],
			row.name,
			"Sub Assembly",
			row.production_item,
			ctx.tasks,
			ctx.task_info,
			parent_row=row.production_plan_item,
			supplier=row_suppliers[row.name],
		)

	return row_bounds


def get_subcontract_supplier(row, ctx):
	if row.supplier:
		return row.supplier

	rows = ctx.supplier_lead_times.get(row.production_item) or {}
	default_row = next((r for r in rows.values() if r.is_default), None)
	return default_row.supplier if default_row else None


def get_first_tasks(bounds):
	first_keys, _terminal_keys, row_tasks = bounds
	return [task for task in row_tasks if task.key in first_keys]


def get_finished_good_dependencies(fg_row, sub_rows, row_bounds):
	produced_items = {row.production_item for row in sub_rows}
	dependencies = []
	for row in sub_rows:
		if row.parent_item_code == fg_row.item_code or row.parent_item_code not in produced_items:
			dependencies.extend(row_bounds[row.name][1])

	return dependencies


def wire_dependencies(first_tasks, dependency_keys):
	for task in first_tasks:
		task.depends_on = list(dict.fromkeys([*task.depends_on, *dependency_keys]))


def register_tasks(
	row_tasks, row_name, row_type, item_code, tasks, task_info, parent_row=None, supplier=None
):
	for task in row_tasks:
		tasks.append(task)
		task_info[task.key] = {
			"plan_row": row_name,
			"row_type": row_type,
			"item_code": item_code,
			"operation": task.label,
			"parent_row": parent_row,
			"supplier": supplier,
		}


def build_row_tasks(plan, bom_no, item_code, qty, subcontracted, prefix, ctx, supplier=None):
	if not subcontracted and bom_no and frappe.get_cached_value("BOM", bom_no, "with_operations"):
		row_tasks, terminal_keys = loaders.build_bom_operation_tasks(bom_no, qty, prefix)
		if row_tasks:
			first_keys = [task.key for task in row_tasks if not task.depends_on]
			return row_tasks, first_keys, terminal_keys

	lead_time = ctx.lead_times.get(item_code)
	if subcontracted:
		supplier_row = (ctx.supplier_lead_times.get(item_code) or {}).get(supplier)
		if supplier_row:
			lead_time = frappe._dict(
				purchase_time=supplier_row.purchase_time, buffer_time=supplier_row.buffer_time
			)

	duration = get_lead_time_duration_mins(lead_time, qty, subcontracted, cint(plan.get("no_of_shifts")))
	task = Task(key=prefix, duration_mins=duration)
	return [task], [task.key], [task.key]


def get_lead_time_duration_mins(lead_time, qty, subcontracted, no_of_shifts):
	if not lead_time:
		return 1440.0

	if subcontracted:
		return max(cint(lead_time.purchase_time) + cint(lead_time.buffer_time), 1) * 1440.0

	buffer_mins = cint(lead_time.buffer_time) * 1440.0
	days_needed = get_days_needed(lead_time, qty, no_of_shifts)
	if not days_needed:
		return max(buffer_mins, 1440.0)

	full_days = math.ceil(days_needed) - 1
	partial_day_mins = (days_needed - full_days) * get_daily_working_mins(lead_time, no_of_shifts)
	return full_days * 1440.0 + partial_day_mins + buffer_mins


def get_days_needed(lead_time, qty, no_of_shifts):
	capacity = get_daily_capacity(lead_time, no_of_shifts)
	if capacity:
		return qty / capacity

	if lead_time.manufacturing_time_in_mins:
		minutes_per_day = get_daily_working_mins(lead_time, no_of_shifts) * (
			cint(lead_time.no_of_workstations) or 1
		)
		return cint(lead_time.manufacturing_time_in_mins) * qty / minutes_per_day

	return 0


def get_daily_working_mins(lead_time, no_of_shifts):
	return (
		(no_of_shifts or cint(lead_time.no_of_shift) or 1) * (cint(lead_time.shift_time_in_hours) or 8) * 60.0
	)


def get_daily_capacity(lead_time, no_of_shifts):
	capacity = flt(lead_time.capacity_per_day)
	if capacity and lead_time.daily_yield:
		capacity = capacity * flt(lead_time.daily_yield) / 100

	if capacity and no_of_shifts:
		capacity = capacity * no_of_shifts / (cint(lead_time.no_of_shift) or 1)

	return capacity


def get_lead_time_details(plan, extra_items=None):
	item_codes = {row.item_code for row in plan.po_items}
	item_codes.update(row.production_item for row in plan.sub_assembly_items)
	item_codes.update(extra_items or [])

	return {
		row.item_code: row
		for row in frappe.get_all(
			"Item Lead Time",
			filters={"item_code": ("in", list(item_codes))},
			fields=[
				"item_code",
				"capacity_per_day",
				"daily_yield",
				"manufacturing_time_in_mins",
				"no_of_shift",
				"shift_time_in_hours",
				"no_of_workstations",
				"purchase_time",
				"buffer_time",
			],
		)
	}


def build_proposal(plan, result, task_info):
	rows = defaultdict(lambda: {"blocks": []})
	for key, assignment in result.assignments.items():
		info = task_info[key]
		row = rows[info["plan_row"]]
		row.update(
			{
				"row_type": info["row_type"],
				"item_code": info["item_code"],
				"parent_row": info.get("parent_row"),
				"supplier": info.get("supplier"),
				"consumers": info.get("consumers") or [],
			}
		)
		for block in assignment.blocks:
			row["blocks"].append(
				{
					"task_key": key,
					"operation": info["operation"],
					"workstation": assignment.resource,
					"from_time": block.start,
					"to_time": block.end,
					"duration_mins": block.duration_mins(),
				}
			)

	for row in rows.values():
		row["blocks"].sort(key=lambda block: block["from_time"])
		row["start"] = row["blocks"][0]["from_time"]
		row["end"] = row["blocks"][-1]["to_time"]

	return {
		"production_plan": plan.name,
		"direction_used": result.direction_used,
		"completion_date": result.end_date,
		"rows": dict(rows),
		"unscheduled": {key: reason for key, reason in result.unscheduled.items()},
	}


def replace_schedule_entries(plan, proposal):
	lock_booked_workstations(proposal)
	frappe.db.delete("Production Plan Schedule", {"production_plan": plan.name})

	for row_name, row in proposal["rows"].items():
		for block in row["blocks"]:
			entry = make_schedule_entry(plan, row_name, row, block)
			entry.flags.from_scheduler = True
			entry.insert(ignore_permissions=True)


def lock_booked_workstations(proposal):
	workstations = sorted(
		{
			block["workstation"]
			for row in proposal["rows"].values()
			for block in row["blocks"]
			if block.get("workstation")
		}
	)
	if workstations:
		frappe.db.get_values(
			"Workstation", {"name": ("in", workstations)}, "name", order_by="name", for_update=True
		)


def make_schedule_entry(plan, row_name, row, block):
	return frappe.get_doc(
		{
			"doctype": "Production Plan Schedule",
			"production_plan": plan.name,
			"company": plan.company,
			"plan_row": row_name,
			"row_type": row["row_type"],
			"item_code": row["item_code"],
			"operation": block.get("operation") if block.get("workstation") else None,
			"workstation": block.get("workstation"),
			"supplier": row.get("supplier"),
			"from_time": block["from_time"],
			"to_time": block["to_time"],
			"duration_mins": block["duration_mins"],
			"task_key": block["task_key"],
			"subject": get_entry_subject(row, block),
		}
	)


def get_entry_subject(row, block):
	item_name = frappe.get_cached_value("Item", row["item_code"], "item_name") or row["item_code"]

	if row["row_type"] == "Raw Material":
		activity = _("Procurement")
	elif block.get("workstation") and block.get("operation"):
		activity = block["operation"]
	else:
		activity = _("Production")

	return f"{item_name} · {activity}"


def update_plan_row_dates(plan, proposal, use_item_dates=0, item_dates=None):
	rows = proposal["rows"]
	for fg_row in plan.po_items:
		if fg_row.name in rows:
			set_finished_good_start_date(fg_row, rows, use_item_dates, item_dates)
			fg_row.db_set("planned_end_date", rows[fg_row.name]["end"], update_modified=False)

	for row in plan.sub_assembly_items:
		if row.name in rows:
			row.db_set("schedule_date", rows[row.name]["start"], update_modified=False)
			row.db_set("schedule_end_date", rows[row.name]["end"], update_modified=False)

	update_material_request_row_dates(plan, rows)


def update_material_request_row_dates(plan, rows):
	material_rows = {row["item_code"]: row for row in rows.values() if row.get("row_type") == "Raw Material"}
	supplier_lead_times = get_supplier_lead_times(set(material_rows))
	fallback_lead_days = get_fallback_lead_days(plan, set(material_rows))
	for row in plan.get("mr_items") or []:
		material = material_rows.get(row.item_code)
		if material:
			row.db_set(
				"schedule_date",
				get_material_row_schedule_date(row, material, supplier_lead_times, fallback_lead_days),
				update_modified=False,
			)


def get_fallback_lead_days(plan, item_codes):
	lead_times = get_lead_time_details(plan, item_codes)
	missing = [item for item in item_codes if not lead_times.get(item)]
	master_days = {}
	if missing:
		master_days = dict(
			frappe.get_all(
				"Item", filters={"name": ("in", missing)}, fields=["name", "lead_time_days"], as_list=True
			)
		)

	days = {}
	for item in item_codes:
		lead_time = lead_times.get(item)
		if lead_time:
			days[item] = cint(lead_time.purchase_time) + cint(lead_time.buffer_time)
		else:
			days[item] = cint(master_days.get(item)) or None
	return days


def get_material_row_schedule_date(row, material, supplier_lead_times, fallback_lead_days):
	supplier = row.get("supplier")
	lead_row = (supplier_lead_times.get(row.item_code) or {}).get(supplier)
	days = None
	if lead_row:
		days = cint(lead_row.purchase_time) + cint(lead_row.buffer_time)
	elif supplier:
		days = fallback_lead_days.get(row.item_code)

	if days is None:
		return getdate(material["end"])
	return getdate(add_to_date(get_datetime(material["start"]), days=days))


def set_finished_good_start_date(fg_row, rows, use_item_dates, item_dates):
	if use_item_dates and (item_dates or {}).get(fg_row.name):
		fg_row.db_set("planned_start_date", item_dates[fg_row.name], update_modified=False)
	else:
		fg_row.db_set("planned_start_date", rows[fg_row.name]["start"], update_modified=False)
