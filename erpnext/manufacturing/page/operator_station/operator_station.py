from erpnext.manufacturing.doctype.job_card.constants import HIGH_PRIORITY
from copy import deepcopy

import frappe
from frappe import _
from frappe import utils as frappe_utils
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import BOM
from erpnext.manufacturing.doctype.job_card.job_card import (
	JobCard,
	make_time_log,
)
from erpnext.manufacturing.doctype.manufacturing_process.constants import (
	DISTRIBUTION_PROCESS,
	MFG_PROCESS_MAP,
	MIXING_PROCESS,
)
from erpnext.manufacturing.doctype.operation.api import get_open_job_cards, transfer_to_next_process
from erpnext.manufacturing.doctype.production_line.production_line import (
	ProductionLine,
	get_all_child_lines,
	get_parent_line,
)
from erpnext.manufacturing.doctype.slab.api import (
	checkout_slab,
	create_slab,
	get_slabs_for,
	move_slab_to,
	pause_or_resume_slab_operation,
)
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory
from erpnext.manufacturing.doctype.work_order.work_order import (
	WorkOrder,
)
from erpnext.manufacturing.doctype.work_order.work_order import (
	make_stock_entry as wo_make_stock_entry,
)
from erpnext.manufacturing.doctype.workstation.workstation import Workstation
from erpnext.setup.doctype.employee.api import get_current_user_context
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


@frappe.whitelist()
def start_process(job_card, slab_name="", slab_template="", process_name="operator"):
	"""Start the Job Card when mixing starts."""

	jc: JobCard = frappe.get_doc("Job Card", job_card)  # pyright: ignore[reportAssignmentType]
	start_time = frappe.utils.now_datetime()  # pyright: ignore[reportAttributeAccessIssue]
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
		if not process_name or process_name.lower() != DISTRIBUTION_PROCESS.lower():
			raise Exception("Cannot create a new slab outside distribution")

		parent_line = get_parent_line(jc.production_line or "")
		child_line = ""
		if parent_line and parent_line != jc.production_line:
			child_line = jc.production_line

		slab_history = _get_mixing_slab_history(jc.name or "")
		new_slab = create_slab(parent_line or "", child_line or "", slab_template or "", jc.name, slab_history)
		slab_name = new_slab.name
		slab_template = new_slab.template

	update_slab_number_on_job_card(jc.name, slab_name, slab_template)

	jc.reload()
	jc.job_started = 1
	jc.priority = HIGH_PRIORITY
	jc.save(ignore_permissions=True)

	start_machine(process_name, jc.production_line, None)

	return {
		"status": jc.status,
		f"{process_name}_started": jc.job_started,
		f"{process_name}_start_time": jc.started_time,
		"current_time": jc.current_time,
		"slab_name": jc.slab,
		"slab_template": jc.slab_template,
	}


@frappe.whitelist()
def pause_process(job_card_name):
	"""Pause the Job Card when mixing is paused."""
	job_card: JobCard = frappe.get_doc("Job Card", job_card_name)  # pyright: ignore[reportAssignmentType]

	# 1. Update the Job Card status to "On Hold"
	args = {
		"status": "On Hold",
		"job_card_id": job_card_name,
		"complete_time": frappe_utils.now_datetime(),
	}

	make_time_log(args)
	job_card.reload()

	# 2. Add a time log on the slab for the paused time
	pause_or_resume_slab_operation(job_card.slab or "", True)

	return {
		"status": "On Hold",
		"job_card": job_card,
	}


@frappe.whitelist()
def resume_process(job_card_name):
	"""Resume the Job Card when mixing is resumed."""
	job_card: JobCard = frappe.get_doc("Job Card", job_card_name)  # pyright: ignore[reportAssignmentType]

	# 1. Update the Job Card status.
	args = {
		"job_card_id": job_card_name,
		"start_time": frappe_utils.now_datetime(),
		"employees": job_card.employee,
		"status": "Resume Job",
	}

	make_time_log(args)
	job_card.reload()

	# 2. Add a time log on the slab for the resumed time.
	pause_or_resume_slab_operation(job_card.slab or "", False)

	return {
		"status": "Work In Progress",
		"job_card": job_card,
	}


@frappe.whitelist()
def finish_process(
	job_card,
	process_name,
	transfer_materials=True,
	should_stop_machine=True,
	slab_number=None,
	slab_grade=None,
):
	"""Complete the Job Card when mixing is finished."""

	if isinstance(transfer_materials, str):
		transfer_materials = transfer_materials.lower() == "true"

	if isinstance(should_stop_machine, str):
		should_stop_machine = should_stop_machine.lower() == "true"

	jc: JobCard = frappe.get_doc("Job Card", job_card)  # pyright: ignore[reportAssignmentType]
	job_card_qty = flt(jc.total_completed_qty or jc.for_quantity, 3)

	args = {
		"job_card_id": jc.name,
		"complete_time": frappe.utils.now_datetime(),  # pyright: ignore[reportAttributeAccessIssue]
		"completed_qty": job_card_qty,
		"status": "Completed",
	}

	make_time_log(args)

	jc.reload()
	jc.status = "Completed"
	jc.job_started = 0
	if jc.docstatus == 0:
		jc.submit()
	else:
		jc.save(ignore_permissions=True)

	jc.reload()
	jc.db_set("status", "Completed")
	jc.reload()

	work_order = jc.work_order
	wo: WorkOrder = frappe.get_doc("Work Order", work_order)  # pyright: ignore[reportAssignmentType]
	wo.material_transferred_for_manufacturing = job_card_qty
	wo.flags.ignore_validate_update_after_submit = True
	wo.save()
	wo.reload()

	se_doc = wo_make_stock_entry(work_order, "Manufacture", qty=job_card_qty)
	if isinstance(se_doc, dict):
		stock_entry_manufacture: StockEntry = frappe.get_doc(se_doc)  # pyright: ignore[reportAssignmentType]
	else:
		stock_entry_manufacture = se_doc

	fg_item = next((item for item in stock_entry_manufacture.items if item.is_finished_item), None)
	if fg_item:
		fg_item.qty = job_card_qty

	if process_name == "Quality Check":
		stock_entry_manufacture.slab_grade = slab_grade
		stock_entry_manufacture.slab_serial_no = slab_number.split("-")[-1]
		stock_entry_manufacture.slab_batch_no = slab_number.split("-")[0]

		for item in stock_entry_manufacture.items:
			if item.is_finished_item:
				item.slab_no = slab_number
				item.to_slab_no = slab_number

	stock_entry_manufacture.fg_completed_qty = job_card_qty
	stock_entry_manufacture.save()
	stock_entry_manufacture.submit()
	wo.update_work_order_qty()
	wo.reload()
	wo_status = wo.get_status()

	if jc.slab:
		checkout_slab(jc.slab)

	if transfer_materials:
		transfer_to_next_process(job_card, work_order, job_card_qty, mixer_number=jc.mixer_number)

	if should_stop_machine:
		stop_machine(process_name, jc.production_line, None)

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
def get_next_process_bom_qty(current_work_order: str):
	"""Get BOM qty required for NEXT process"""
	wo: WorkOrder = frappe.get_doc("Work Order", current_work_order)  # pyright: ignore

	current_process = wo.operations[0].operation if wo.operations else ""

	process_mapping = deepcopy(MFG_PROCESS_MAP)
	process_mapping["Mixing Operation - SJ"] = process_mapping[
		MIXING_PROCESS
	]  # TODO: Find a better way to do this rather than hardcoding the process name

	next_process = process_mapping.get(current_process)

	if not next_process:
		frappe.throw(_("No next process found after {0}").format(current_process))

	next_wos = frappe.db.get_list(
		"Work Order",
		filters={
			"production_plan": wo.production_plan,
			"docstatus": ["<", 2],
		},
		fields=["name"],
		ignore_permissions=True,
	)

	wo_names = [wo.name for wo in next_wos]
	wo_ops = frappe.db.get_list(
		"Work Order Operation",
		filters={
			"parent": ["in", wo_names],
			"operation": ["=", next_process],
		},
		fields=["parent"],
		ignore_permissions=True,
	)

	next_wo = wo_ops[0].parent if wo_ops else None

	if not next_wo:
		return {"bom_qty": 0}

	next_wo_doc: WorkOrder = frappe.get_doc("Work Order", next_wo)  # pyright: ignore[reportAssignmentType]
	bom_doc: BOM = frappe.get_doc("BOM", next_wo_doc.bom_no)  # pyright: ignore[reportAssignmentType]
	fg_item = wo.production_item

	for bom_item in bom_doc.items:
		if bom_item.item_code == fg_item:
			return {
				"bom_qty": flt(bom_item.stock_qty),
				"next_work_order": next_wo,
				"next_process": next_process,
			}

	return {"bom_qty": 0}


def get_machine(
	station: str, line_name: str | None = None, machine_name: str | None = None
) -> Workstation | None:
	if not line_name or not machine_name:
		# Get the machine and line from the work context.
		work_context = get_current_user_context()
		line_name = line_name or (work_context.get("production_line") if work_context else None)
		machine_name = machine_name or (work_context.get("workstation_type") if work_context else None)

	if machine_name:
		return frappe.get_doc("Workstation", machine_name)  # pyright: ignore[reportReturnType]

	if not machine_name and station and line_name:
		line: ProductionLine = frappe.get_doc("Production Line", line_name)  # pyright: ignore[reportAssignmentType]
		# Get the machine from the station and line.

		# Filters should be workstation_type like '%station%' and production_line = line.name or production_line = line.parent
		return frappe.get_last_doc(  # pyright: ignore[reportReturnType]
			"Workstation",
			filters={
				"workstation_type": ["like", f"%{station}%"],
				"production_line": ["in", [line.name, line.parent_line]],
			},
		)

	return None


def start_machine(station: str, line_name: str | None, machine_name: str | None):
	set_machine_status("Production", station, line_name, machine_name)


def stop_machine(station: str, line_name: str | None, machine_name: str | None):
	set_machine_status("Idle", station, line_name, machine_name)


def set_machine_status(status: str, station: str, line_name: str | None, machine_name: str | None):
	machine = get_machine(station, line_name, machine_name)
	if not machine:
		return

	machine.status = status  # pyright: ignore[reportAttributeAccessIssue]
	machine.save(ignore_permissions=True)
	machine.reload()


def _get_job_card_for_line_and_process(line_name: str, process: str, include_wip=True):
	child_lines = get_all_child_lines(line_name) or []
	job_card_data = get_top_job_card_for_process(
		process, child_lines if child_lines else line_name, include_wip
	)
	return job_card_data


@frappe.whitelist()
def get_next_work_item(process, line="", include_wip=True):
	if isinstance(include_wip, str):
		include_wip = include_wip.lower() == "true"

	job_card_data = _get_job_card_for_line_and_process(line, process, include_wip)
	job_card = job_card_data["top_job_card"]
	available_job_cards_count = job_card_data["available_job_cards_count"]

	is_wip = job_card and job_card.status == "Work In Progress"
	slab = frappe.get_doc("Slab", job_card.slab) if is_wip and job_card.slab else None

	slabs_for_process = get_slabs_for(
		line, process, limit=1000
	)  # Giving an arbitrarily high limit to make sure that the exact number of slabs is fetched.

	slab = slab if slab else (slabs_for_process[0] if slabs_for_process else None)
	available_slabs_count = len(slabs_for_process)

	return {
		"slab": slab,
		"available_slabs_count": available_slabs_count,
		"job_card": job_card,
		"available_job_cards_count": available_job_cards_count,
	}


def get_top_job_card_for_process(process, line: str | list = "", include_wip=True, include_paused=True):
	if line and not isinstance(line, list):
		child_lines = get_all_child_lines(line)
		if child_lines:
			line = child_lines

	job_cards = get_open_job_cards(process, line, include_wip, include_paused=include_paused)
	return {
		"top_job_card": job_cards[0] if job_cards else None,
		"available_job_cards_count": len(job_cards),
	}
	# return job_cards[0] if job_cards else None


def update_slab_number_on_job_card(job_card_name, slab_name, slab_template):
	jc: JobCard = frappe.get_doc("Job Card", job_card_name)  # pyright: ignore[reportAssignmentType]
	jc.slab = slab_name
	jc.slab_template = slab_template
	jc.save(ignore_permissions=True)
	jc.reload()


@frappe.whitelist()
def get_job_card_for_slab(slab_name: str, process_name: str):
	slab: Slab = frappe.get_doc("Slab", slab_name)  # pyright: ignore[reportAssignmentType]
	job_card_data = _get_job_card_for_line_and_process(slab.line, process_name, include_wip=True)
	job_card = job_card_data["top_job_card"]
	return job_card


def _get_mixing_slab_history(job_card_name: str):
	# 1. Get the ID of the Mixing Job Card that transferred the material to this distribution using the current job card's stock entry.
	stock_entry = frappe.get_all("Stock Entry", filters={"job_card": job_card_name}, limit=1, fields=["name", "job_card", "previous_job_card"])
	if stock_entry:
		stock_entry = stock_entry[0]
	else:
		stock_entry = None

	# 2. Get the time logs of the mixing job card.
	if stock_entry and stock_entry.previous_job_card:
		mixing_job_card = frappe.get_doc("Job Card", stock_entry.previous_job_card)
	else:
		mixing_job_card = None

	# 3. Append the time logs to the slab.
	time_logs = []
	if mixing_job_card:
		time_logs = frappe.get_all("Job Card Time Log", filters={"parent": mixing_job_card.name}, fields=["from_time", "to_time", "time_in_mins"], order_by="idx asc")

	slab_history = []
	if time_logs:
		for i, log in enumerate(time_logs):
			slab_history_item: SlabHistory = frappe.new_doc("Slab History")  # pyright: ignore[reportAssignmentType]
			slab_history_item.idx = i + 1
			slab_history_item.in_time = log.from_time
			slab_history_item.out_time = log.to_time
			slab_history_item.total_time_in_minutes = log.time_in_mins
			slab_history_item.station = MIXING_PROCESS
			slab_history_item.job_card_number = mixing_job_card.name if mixing_job_card else None
			slab_history.append(slab_history_item)

	return slab_history
