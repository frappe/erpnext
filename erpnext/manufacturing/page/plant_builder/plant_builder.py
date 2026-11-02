from collections import Counter

import frappe
from frappe.utils import flt

from erpnext.manufacturing.doctype.plant_floor.plant_floor import (
	PACKING_MACHINE_MODELS,
	get_workstation_details,
)
from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import PlantRun
from erpnext.manufacturing.doctype.work_order.services.plant_run.state import PlantRunState
from erpnext.manufacturing.doctype.workstation_type.workstation_type import get_preset_shapes

PLANT_FIELDS = ["name", "floor_name", "production_item", "batch_size", "modified"]


@frappe.whitelist()
def get_plants() -> list[dict]:
	plants = frappe.get_list("Plant Floor", fields=PLANT_FIELDS, order_by="modified desc")
	stages = frappe.get_all(
		"Plant Floor Stage",
		filters={"parent": ("in", [plant.name for plant in plants])},
		fields=["parent", "stage_name", "workstation"],
		order_by="idx",
	)
	models = get_workstation_details(tuple({row.workstation for row in stages}))
	materials = Counter(
		frappe.get_all(
			"Plant Floor Material",
			filters={"parent": ("in", [plant.name for plant in plants])},
			pluck="parent",
		)
	)
	for plant in plants:
		plant.stages = [
			{
				"stage_name": row.stage_name,
				"machine_model": models.get(row.workstation, {}).get("machine_model"),
			}
			for row in stages
			if row.parent == plant.name
		]
		plant.material_count = materials[plant.name]
		plant.item = get_item(plant.production_item)
	return plants


@frappe.whitelist()
def get_plant(name: str) -> dict:
	plant_floor = frappe.get_doc("Plant Floor", name)
	plant_floor.check_permission("read")
	return get_plant_data(plant_floor)


@frappe.whitelist()
def check_plant(doc: str | dict) -> dict:
	plant_floor = frappe.get_doc({**frappe.parse_json(doc), "doctype": "Plant Floor"})
	frappe.has_permission("Plant Floor", "read", throw=True)
	set_item_names(plant_floor)
	return get_plant_data(plant_floor)


def set_item_names(plant_floor):
	rows = [*plant_floor.materials, *plant_floor.packing_materials]
	names = dict(
		frappe.get_all(
			"Item",
			filters={"name": ("in", [row.item_code for row in rows if row.item_code])},
			fields=["name", "item_name"],
			as_list=1,
		)
	)
	for row in rows:
		row.item_name = names.get(row.item_code)


@frappe.whitelist(methods=["POST"])
def save_plant(doc: str | dict) -> dict:
	values = frappe.parse_json(doc)
	if values.get("name") and frappe.db.exists("Plant Floor", values.name):
		plant_floor = frappe.get_doc("Plant Floor", values.name)
		plant_floor.update(values)
		plant_floor.save()
	else:
		plant_floor = frappe.get_doc({**values, "doctype": "Plant Floor"}).insert()
	return get_plant_data(plant_floor)


def get_plant_data(plant_floor):
	errors = plant_floor.setup_errors
	return {
		"doc": plant_floor.as_dict(),
		"is_saved": bool(plant_floor.get("creation")),
		"item": get_item(plant_floor.production_item),
		"machines": get_machines(tuple({row.workstation for row in plant_floor.stages})),
		"errors": errors,
		"plan": None if errors else plant_floor.get_batch_plan().as_dict(),
		"work_orders": get_work_orders(plant_floor.name) if plant_floor.get("creation") else [],
	}


def get_machines(workstations):
	machines = get_workstation_details(workstations)
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


def get_work_orders(plant_floor):
	return frappe.get_list(
		"Work Order",
		filters={"plant_floor": plant_floor, "docstatus": ("<", 2)},
		fields=["name", "status", "qty", "produced_qty", "creation"],
		order_by="creation desc",
		limit=5,
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
		"packing_models": PACKING_MACHINE_MODELS,
	}


@frappe.whitelist()
def get_workstation(name: str) -> dict:
	return get_machines((name,)).get(name)


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
def make_work_order(plant_floor: str, qty: float | None = None) -> str:
	return frappe.get_doc("Plant Floor", plant_floor).make_work_order(qty).name


@frappe.whitelist()
def get_run(work_order: str) -> dict:
	frappe.has_permission("Work Order", "read", doc=work_order, throw=True)
	run = PlantRun(work_order)
	return {**PlantRunState(run).as_dict(), "plant": get_plant_data(run.plant_floor)}


@frappe.whitelist(methods=["POST"])
def set_run_qty(work_order: str, qty: float) -> dict:
	return run_action(work_order, "set_qty", qty=flt(qty))


@frappe.whitelist(methods=["POST"])
def start_run(work_order: str, job_card: str | None = None) -> dict:
	return run_action(work_order, "start", job_card=job_card)


@frappe.whitelist(methods=["POST"])
def pause_run(work_order: str) -> dict:
	return run_action(work_order, "pause")


@frappe.whitelist(methods=["POST"])
def resume_run(work_order: str) -> dict:
	return run_action(work_order, "resume")


@frappe.whitelist(methods=["POST"])
def report_breakdown(work_order: str, job_card: str) -> dict:
	return run_action(work_order, "report_breakdown", job_card=job_card)


@frappe.whitelist(methods=["POST"])
def restart_machine(
	work_order: str,
	job_card: str,
	stop_reason: str,
	remarks: str | None = None,
	operator: str | None = None,
) -> dict:
	return run_action(
		work_order,
		"restart_machine",
		job_card=job_card,
		stop_reason=stop_reason,
		remarks=remarks,
		operator=operator,
	)


@frappe.whitelist(methods=["POST"])
def consume_materials(work_order: str, job_card: str, quantities: str | dict) -> dict:
	return run_action(work_order, "consume", job_card=job_card, quantities=frappe.parse_json(quantities))


@frappe.whitelist(methods=["POST"])
def produce_output(
	work_order: str,
	job_card: str,
	output_qty: float,
	rejected_qty: float = 0,
	readings: str | list | None = None,
) -> dict:
	return run_action(
		work_order,
		"produce",
		job_card=job_card,
		output_qty=flt(output_qty),
		rejected_qty=flt(rejected_qty),
		readings=frappe.parse_json(readings) if readings else None,
	)


def run_action(work_order, method, **kwargs):
	frappe.has_permission("Work Order", "write", doc=work_order, throw=True)
	getattr(PlantRun(work_order), method)(**kwargs)
	frappe.clear_messages()
	return get_run(work_order)
