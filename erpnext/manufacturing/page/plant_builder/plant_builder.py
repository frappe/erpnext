import frappe
from frappe import _
from frappe.permissions import has_permission
from frappe.utils import cint, flt

from erpnext.manufacturing.doctype.bom_creator.operation_plan import OperationPlan
from erpnext.manufacturing.doctype.work_order.mapper import make_work_order
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
	floors = [floor for floor in (plant_floor, machine.plant_floor) if floor]
	if not floors:
		frappe.throw(_("Choose the Plant Floor of {0}").format(frappe.bold(workstation)))

	for floor in floors:
		frappe.get_doc("Plant Floor", floor).check_permission("write")
	machine.plant_floor = plant_floor
	machine.save()
	return get_floor(floors[0])


def get_floor_data(floor):
	machines = add_machine_shapes(get_floor_machines([floor.name]))
	ptype = "write" if floor.get("creation") else "create"
	return {
		"doc": floor.as_dict(),
		"is_saved": bool(floor.get("creation")),
		"can_write": bool(has_permission("Plant Floor", ptype, floor, print_logs=False)),
		"machines": list(machines.values()),
		"work_orders": get_open_work_orders(list(machines)),
	}


def get_floor_machines(floors):
	if not floors:
		return {}

	floor_of = dict(
		frappe.get_list(
			"Workstation",
			filters={"plant_floor": ("in", floors)},
			fields=["name", "plant_floor"],
			order_by="creation",
			as_list=1,
		)
	)
	details = get_workstation_details(tuple(floor_of))
	jobs = get_running_jobs(list(floor_of))
	for name, machine in details.items():
		machine.update(plant_floor=floor_of[name], job=jobs.get(name))
	return {name: details[name] for name in floor_of if name in details}


def get_running_jobs(workstations):
	if not workstations:
		return {}

	cards = frappe.get_list(
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


@frappe.whitelist()
def check_design(doc: str | dict) -> dict:
	frappe.has_permission("BOM Creator", "read", throw=True)
	design = frappe.get_doc(
		{**frappe.parse_json(doc), "doctype": "BOM Creator", "track_semi_finished_goods": 1}
	)
	plan = OperationPlan(design)
	formula = plan.formula
	for workstation in {row.workstation for row in formula.stages if row.workstation}:
		frappe.has_permission("Workstation", doc=workstation, throw=True)
	formula.apply()
	batch = flt(design.qty) or 1
	return {
		"errors": plan.get_problems(),
		"item": formula.item,
		"machines": add_machine_shapes(formula.machines),
		"weight_factors": formula.weight_factors,
		"balance_qty": flt(flt(formula.balance_row.qty) * batch, 3) if formula.balance_row else None,
		"outputs": {
			cint(row.operation_id): flt(flt(row.output_quantity) * batch, 3) for row in formula.process_stages
		},
		"formula_weight": flt(formula.charged_weight * batch, 3) if formula.can_compute else 0,
		"items": get_items(
			[row.item_code for row in formula.materials] + [row.output_item for row in formula.stages]
		),
	}


def get_items(item_codes):
	items = frappe.get_list(
		"Item",
		filters={"name": ("in", list(filter(None, item_codes)))},
		fields=["name", "item_name", "stock_uom"],
	)
	return {item.name: item for item in items}


def add_machine_shapes(machines):
	for machine in machines.values():
		machine.shapes = get_machine_shapes(machine)
	return machines


def get_machine_shapes(machine):
	if not machine.workstation_type:
		return get_preset_shapes(machine.machine_model)
	return frappe.get_cached_doc("Workstation Type", machine.workstation_type).machine_shapes


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


@frappe.whitelist(methods=["POST"])
def repeat_work_order(work_order: str) -> str:
	source = frappe.get_doc("Work Order", work_order)
	source.check_permission("read")
	repeat = make_work_order(
		source.bom_no, source.production_item, source.qty, source.company, source.project
	)
	repeat.update({"wip_warehouse": source.wip_warehouse, "fg_warehouse": source.fg_warehouse})
	repeat.insert()
	return repeat.name


@frappe.whitelist()
def get_run(work_order: str) -> dict:
	run = get_plant_run(work_order, "read")
	state = PlantRunState(run)
	plan = state.plan
	return {
		**state.as_dict(),
		"plant": {
			"doc": plan.get_plant_doc(),
			"machines": add_machine_shapes(plan.machines),
			"item": plan.item,
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


@frappe.whitelist()
def get_serial_batch_options(work_order: str, job_card: str, row: str) -> dict:
	return get_plant_run(work_order, "read").get_pick_options(job_card, row)


@frappe.whitelist(methods=["POST"])
def consume_materials(
	work_order: str, job_card: str, quantities: str | dict, picks: str | dict | None = None
) -> dict:
	picks = frappe.parse_json(picks) if picks else None
	return run_action(work_order, lambda run: run.consume(job_card, frappe.parse_json(quantities), picks))


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
