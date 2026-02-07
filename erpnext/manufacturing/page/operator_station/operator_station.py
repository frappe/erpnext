import frappe
from frappe.utils import flt

from erpnext.manufacturing.doctype.job_card.job_card import (
	JobCard,
	make_time_log,
)
from erpnext.manufacturing.doctype.operation.api import get_open_job_cards, transfer_to_next_process
from erpnext.manufacturing.doctype.slab.api import checkout_slab, create_slab, get_slabs_for, move_slab_to
from erpnext.manufacturing.doctype.work_order.work_order import (
	WorkOrder,
)
from erpnext.manufacturing.doctype.work_order.work_order import (
	make_stock_entry as wo_make_stock_entry,
)


@frappe.whitelist()
def get_machine_state(job_card, process_name="operator"):
	jc = frappe.get_doc("Job Card", job_card)
	if jc.work_order:
		wo = frappe.get_doc("Work Order", jc.work_order)
	else:
		None

	state = {
		f"{process_name}_started": 1 if jc.time_logs else 0,
		f"{process_name}_start_time": jc.started_time,
		"job_card_submitted": jc.docstatus == 1 or jc.status == "Completed",
		"stock_entry_name": wo.produced_qty > 0 and f"MFG-SE-{process_name.upper()}-*" or "",
		"process_name": process_name,
		"status": jc.status,
		"current_process": wo.item_name.rsplit("-", 1)[-1].strip()
		if wo and "-" in wo.item_name
		else process_name,
	}

	return state


@frappe.whitelist()
def start_process(job_card, slab_name="", slab_template = "", process_name="operator"):
	"""Start the Job Card when mixing starts."""

	jc: JobCard = frappe.get_doc("Job Card", job_card)
	start_time = frappe.utils.now_datetime()
	# employee_id = get_operators("Mixer Operator", jc.production_line)

	args = {
		"job_card_id": jc.name,
		"start_time": start_time,
		# "employees": [{"employee": "HR-EMP-00002"}],  # TODO - update operator
		"status": "Work In Progress",
	}

	make_time_log(args)

	if slab_name:
		move_slab_to(
			slab_number=slab_name,
			next_stage=process_name.lower(),
			job_card_number=jc.name,
		)

	else:
		new_slab = create_slab(jc.production_line or "", slab_template or "", jc.name)
		slab_name = new_slab.name
		slab_template = new_slab.template

	update_slab_number_on_job_card(jc.name, slab_name, slab_template)

	jc.reload()
	jc.job_started = 1
	jc.save(ignore_permissions=True)

	return {
		"status": jc.status,
		f"{process_name}_started": jc.job_started,
		f"{process_name}_start_time": jc.started_time,
		"current_time": jc.current_time,
		"slab_name": jc.slab,
		"slab_template": jc.slab_template,
	}


@frappe.whitelist()
def finish_process(job_card, transfer_materials=True):
	"""Complete the Job Card when mixing is finished."""

	if isinstance(transfer_materials, str):
		transfer_materials = transfer_materials.lower() == "true"

	jc = frappe.get_doc("Job Card", job_card)
	job_card_qty = flt(jc.total_completed_qty or jc.for_quantity, 3)

	args = {
		"job_card_id": jc.name,
		"complete_time": frappe.utils.now_datetime(),
		"completed_qty": job_card_qty,
		"status": "Completed",
	}

	make_time_log(args)
	last_tl = frappe.get_last_doc("Job Card Time Log", filters={"parent": jc.name})
	if last_tl:
		frappe.db.set_value("Job Card Time Log", last_tl.name, "completed_qty", job_card_qty)

	jc.reload()
	jc.status = "Completed"
	jc.completed_qty = job_card_qty
	jc.job_started = 0
	if jc.docstatus == 0:
		jc.submit()
	else:
		jc.save(ignore_permissions=True)

	jc.reload()
	jc.db_set("status", "Completed")
	jc.reload()

	work_order = jc.work_order
	wo = frappe.get_doc("Work Order", work_order)
	wo.material_transferred_for_manufacturing = job_card_qty
	wo.flags.ignore_validate_update_after_submit = True
	wo.save()
	wo.reload()

	se_doc = wo_make_stock_entry(work_order, "Manufacture", qty=job_card_qty)
	if isinstance(se_doc, dict):
		stock_entry_manufacture = frappe.get_doc(se_doc)
	else:
		stock_entry_manufacture = se_doc

	fg_item = next((item for item in stock_entry_manufacture.items if item.is_finished_item), None)
	if fg_item:
		fg_item.qty = job_card_qty
		fg_item.stock_qty = job_card_qty

	stock_entry_manufacture.fg_completed_qty = job_card_qty
	stock_entry_manufacture.save()
	stock_entry_manufacture.submit()
	wo.update_work_order_qty()
	wo.reload()
	wo_status = wo.get_status()

	checkout_slab(jc.slab)

	if transfer_materials:
		transfer_to_next_process(work_order, job_card_qty)

	return {
		"status": wo_status,
		"work_order_status": wo_status,
		"work_order": work_order,
		"job_card_qty": job_card_qty,
		"total_qty": wo.qty,
		"stock_entry": stock_entry_manufacture.name,
		"message": f"SE {stock_entry_manufacture.name} ({job_card_qty} qty). WO: {wo_status}",
	}


@frappe.whitelist()
def get_next_process_bom_qty(current_work_order):
	"""Get BOM qty required for NEXT process"""
	wo: WorkOrder = frappe.get_doc("Work Order", current_work_order)  # pyright: ignore[reportUnknownParameterType]
	current_process = wo.item_name.rsplit("-", 1)[-1].strip() if wo.item_name else ""
	process_mapping = {
		"mixing": "distribution",
		"distribution": "pressed slab",
		"pressed slab": "heated slab",
		"heated slab": "cooled slab",
		"cooled slab": "trimmed slab",
		"trimmed slab": "calibrated slab",
		"calibrated slab": "polished slab",
		"polished slab": "inspected slab",
	}

	next_process = process_mapping.get(current_process)

	next_wo = frappe.db.get_value(
		"Work Order",
		{
			"production_plan": wo.production_plan,
			"production_item": ["like", f"%{next_process}%"],
			"docstatus": ["<", 2],
		},
		"name",
	)

	if not next_wo:
		return {"bom_qty": 0}

	next_wo_doc = frappe.get_doc("Work Order", next_wo)
	bom_doc = frappe.get_doc("BOM", next_wo_doc.bom_no)
	fg_item = wo.production_item

	for bom_item in bom_doc.items:
		if bom_item.item_code == fg_item:
			return {
				"bom_qty": flt(bom_item.stock_qty),
				"next_work_order": next_wo,
				"next_process": next_process,
			}

	return {"bom_qty": 0}



@frappe.whitelist()
def get_next_work_item(process, line="", include_wip = True):
	if isinstance(include_wip, str):
		include_wip = include_wip.lower() == "true"

	job_card = get_top_job_card_for_process(process, line, include_wip)

	slabs_for_process = get_slabs_for(line, process)
	slab = slabs_for_process[0] if slabs_for_process else None

	return {
		"slab": slab,
		"job_card": job_card,
	}


def get_top_job_card_for_process(process, line="", include_wip = True):
	job_cards = get_open_job_cards(process, line, include_wip)
	return job_cards[-1] if job_cards else None # TODO: Replace -1 with 0 EVERYWHERE


def update_slab_number_on_job_card(job_card_name, slab_name, slab_template):
	jc: JobCard = frappe.get_doc("Job Card", job_card_name)
	jc.slab = slab_name
	jc.slab_template = slab_template
	jc.save(ignore_permissions=True)
	jc.reload()
