import frappe
from frappe.permissions import has_permission
from frappe.utils import cint, flt

from erpnext.manufacturing.doctype.bom_creator.process_formula import ProcessFormula
from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import PlantRun
from erpnext.manufacturing.doctype.work_order.services.plant_run.state import PlantRunState
from erpnext.manufacturing.doctype.workstation_type.workstation_type import (
	get_preset_shapes,
	get_workstation_details,
)

FLOOR_FIELDS = ["name", "floor_name", "company", "warehouse", "modified"]
OPEN_WORK_ORDER_STATUSES = ("Draft", "Not Started", "In Process", "On Hold")


@frappe.whitelist()
def get_floors() -> list[dict]:
	floors = frappe.get_list("Plant Floor", fields=FLOOR_FIELDS, order_by="modified desc")
	machines = get_floor_machines([floor.name for floor in floors])
	for floor in floors:
		floor.machines = [machine for machine in machines.values() if machine.plant_floor == floor.name]
	return floors


@frappe.whitelist()
def get_floor(name: str) -> dict:
	floor = frappe.get_doc("Plant Floor", name)
	floor.check_permission("read")
	return get_floor_data(floor)


@frappe.whitelist(methods=["POST"])
def save_floor(doc: str | dict) -> dict:
	values = frappe.parse_json(doc)
	if values.get("name") and frappe.db.exists("Plant Floor", values.name):
		floor = frappe.get_doc("Plant Floor", values.name)
		floor.update({field: values.get(field) for field in ("company", "warehouse")})
		floor.save()
	else:
		floor = frappe.get_doc({**values, "doctype": "Plant Floor"}).insert()
	return get_floor_data(floor)


@frappe.whitelist(methods=["POST"])
def set_machine_floor(workstation: str, plant_floor: str | None = None) -> dict:
	machine = frappe.get_doc("Workstation", workstation)
	floor = plant_floor or machine.plant_floor
	frappe.get_doc("Plant Floor", floor).check_permission("read")
	machine.plant_floor = plant_floor
	machine.save()
	return get_floor(floor)


def get_floor_data(floor):
	machines = get_floor_machines([floor.name])
	for machine in machines.values():
		machine.shapes = get_machine_shapes(machine)
	return {
		"doc": floor.as_dict(),
		"is_saved": bool(floor.get("creation")),
		"can_write": can_write("Plant Floor", floor),
		"machines": list(machines.values()),
		"work_orders": get_open_work_orders(list(machines)),
	}


def get_floor_machines(floors):
	if not floors:
		return {}

	names = frappe.get_list(
		"Workstation", filters={"plant_floor": ("in", floors)}, pluck="name", order_by="creation"
	)
	details = get_workstation_details(tuple(names))
	floor_of = dict(
		frappe.get_all(
			"Workstation", filters={"name": ("in", names)}, fields=["name", "plant_floor"], as_list=1
		)
	)
	jobs = get_running_jobs(names)
	for name, machine in details.items():
		machine.update(plant_floor=floor_of.get(name), job=jobs.get(name))
	return {name: details[name] for name in names if name in details}


def get_running_jobs(workstations):
	if not workstations:
		return {}

	cards = frappe.get_all(
		"Job Card",
		filters={
			"workstation": ("in", workstations),
			"docstatus": 0,
			"status": ("in", ["Work In Progress", "On Hold"]),
		},
		fields=["name", "workstation", "work_order", "operation", "status", "is_paused"],
		order_by="modified desc",
	)
	jobs = {}
	for card in cards:
		jobs.setdefault(card.workstation, card)
	return jobs


def get_open_work_orders(workstations):
	if not workstations:
		return []

	work_order = frappe.qb.DocType("Work Order")
	operation = frappe.qb.DocType("Work Order Operation")
	names = (
		frappe.qb.from_(work_order)
		.join(operation)
		.on(operation.parent == work_order.name)
		.select(work_order.name)
		.distinct()
		.where(
			operation.workstation.isin(workstations)
			& (work_order.docstatus < 2)
			& work_order.status.isin(OPEN_WORK_ORDER_STATUSES)
			& (work_order.track_semi_finished_goods == 1)
		)
	).run(pluck=True)
	return frappe.get_list(
		"Work Order",
		filters={"name": ("in", names)},
		fields=["name", "production_item", "item_name", "qty", "produced_qty", "status", "stock_uom"],
		order_by="creation desc",
	)


def can_write(doctype, doc):
	if not doc.get("creation"):
		return bool(has_permission(doctype, "create", print_logs=False))
	return bool(has_permission(doctype, "write", doc, print_logs=False))


@frappe.whitelist()
def check_design(doc: str | dict) -> dict:
	frappe.has_permission("BOM Creator", "read", throw=True)
	design = frappe.get_doc({**frappe.parse_json(doc), "doctype": "BOM Creator"})
	formula = ProcessFormula(design)
	for workstation in {row.workstation for row in formula.stages if row.workstation}:
		frappe.has_permission("Workstation", doc=workstation, throw=True)
	formula.apply()
	batch = flt(design.qty) or 1
	return {
		"errors": formula.get_problems(),
		"item": get_item(design.item_code),
		"machines": get_machines(tuple(row.workstation for row in formula.stages if row.workstation)),
		"weight_factors": formula.weight_factors,
		"balance_qty": flt(formula.balance_row.qty * batch, 3) if formula.balance_row else None,
		"outputs": {
			cint(row.operation_id): flt(row.output_quantity * batch, 3) for row in formula.process_stages
		},
		"item_names": get_item_names([row.item_code for row in formula.materials]),
	}


def get_item_names(item_codes):
	return dict(
		frappe.get_all(
			"Item",
			filters={"name": ("in", list(filter(None, item_codes)))},
			fields=["name", "item_name"],
			as_list=1,
		)
	)


def get_machines(workstations):
	machines = get_workstation_details(tuple(sorted(set(workstations))))
	for machine in machines.values():
		machine.shapes = get_machine_shapes(machine)
	return machines


def get_machine_shapes(machine):
	if not machine.workstation_type:
		return get_preset_shapes(machine.machine_model)
	return frappe.get_cached_doc("Workstation Type", machine.workstation_type).machine_shapes


def get_item(item_code):
	if not item_code:
		return None

	return frappe.get_cached_value(
		"Item", item_code, ["item_name", "stock_uom", "weight_per_unit", "weight_uom"], as_dict=True
	)


@frappe.whitelist()
def get_machine_catalog() -> dict:
	designed = frappe.get_all(
		"Workstation Type Shape", filters={"parenttype": "Workstation Type"}, pluck="parent", distinct=True
	)
	return {
		"workstation_types": frappe.get_list(
			"Workstation Type",
			or_filters={"machine_model": ("is", "set"), "name": ("in", designed)},
			fields=["name", "machine_model"],
			order_by="name",
		),
	}


@frappe.whitelist()
def get_machine_design(workstation_type: str) -> dict:
	doc = frappe.get_doc("Workstation Type", workstation_type)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"machine_model": doc.machine_model,
		"shapes": doc.machine_shapes,
		"is_custom": bool(doc.shapes),
		"can_write": bool(doc.has_permission("write")),
	}


@frappe.whitelist(methods=["POST"])
def save_machine_design(workstation_type: str, shapes: str | list) -> dict:
	doc = frappe.get_doc("Workstation Type", workstation_type)
	doc.set("shapes", frappe.parse_json(shapes))
	doc.save()
	return get_machine_design(doc.name)


@frappe.whitelist()
def get_run(work_order: str) -> dict:
	run = get_plant_run(work_order, "read")
	state = PlantRunState(run)
	plan = state.plan
	return {
		**state.as_dict(),
		"plant": {
			"doc": plan.get_plant_doc(),
			"machines": get_machines(tuple(plan.machines)),
			"item": get_item(run.work_order.production_item),
		},
	}


def get_plant_run(work_order, ptype):
	frappe.has_permission("Work Order", ptype, doc=work_order, throw=True)
	return PlantRun(work_order)


@frappe.whitelist(methods=["POST"])
def set_run_qty(work_order: str, qty: float) -> dict:
	return run_action(work_order, lambda run: run.set_qty(flt(qty)))


@frappe.whitelist(methods=["POST"])
def start_run(work_order: str, job_card: str | None = None) -> dict:
	return run_action(work_order, lambda run: run.start(job_card))


@frappe.whitelist(methods=["POST"])
def pause_run(work_order: str) -> dict:
	return run_action(work_order, lambda run: run.pause())


@frappe.whitelist(methods=["POST"])
def resume_run(work_order: str) -> dict:
	return run_action(work_order, lambda run: run.resume())


@frappe.whitelist(methods=["POST"])
def report_breakdown(work_order: str, job_card: str) -> dict:
	return run_action(work_order, lambda run: run.report_breakdown(job_card))


@frappe.whitelist(methods=["POST"])
def restart_machine(
	work_order: str,
	job_card: str,
	stop_reason: str,
	remarks: str | None = None,
	operator: str | None = None,
) -> dict:
	return run_action(work_order, lambda run: run.restart_machine(job_card, stop_reason, remarks, operator))


@frappe.whitelist()
def preview_lot(work_order: str, job_card: str, quantities: str | dict | None = None) -> dict:
	run = get_plant_run(work_order, "read")
	return run.preview(job_card, frappe.parse_json(quantities) if quantities else {})


@frappe.whitelist(methods=["POST"])
def consume_materials(work_order: str, job_card: str, quantities: str | dict) -> dict:
	return run_action(work_order, lambda run: run.consume(job_card, frappe.parse_json(quantities)))


@frappe.whitelist(methods=["POST"])
def produce_output(
	work_order: str,
	job_card: str,
	output_qty: float,
	rejected_qty: float = 0,
	readings: str | list | None = None,
) -> dict:
	readings = frappe.parse_json(readings) if readings else None
	return run_action(
		work_order, lambda run: run.produce(job_card, flt(output_qty), flt(rejected_qty), readings)
	)


def run_action(work_order, action):
	action(get_plant_run(work_order, "write"))
	frappe.clear_messages()
	return get_run(work_order)
