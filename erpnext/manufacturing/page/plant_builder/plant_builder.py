import frappe
from frappe.utils import cint, flt, strip_html

from erpnext.manufacturing.doctype.bom_creator.operation_plan import OperationPlan
from erpnext.manufacturing.doctype.work_order.mapper import make_work_order
from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import PlantRun
from erpnext.manufacturing.doctype.work_order.services.plant_run.state import PlantRunState
from erpnext.manufacturing.doctype.workstation_type.workstation_type import get_preset_shapes


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
		"errors": [strip_html(problem) for problem in plan.get_problems()],
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
