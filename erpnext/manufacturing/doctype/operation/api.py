from erpnext.manufacturing.doctype.job_card.constants import LOW_PRIORITY
import re
from copy import deepcopy

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import BOM
from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.manufacturing_process.constants import MFG_PROCESS_MAP, MIXING_PROCESS
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


@frappe.whitelist()
def transfer_to_next_process(current_job_card, current_work_order, qty=None, process=None, mixer_number=None):
	"""Transfer FG from Mixing → Next Process Source Warehouse."""
	wo: WorkOrder = frappe.get_doc("Work Order", current_work_order)  # pyright: ignore
	fg_item = wo.production_item
	fg_qty = flt(qty or wo.produced_qty)

	process_mapping = deepcopy(MFG_PROCESS_MAP)
	process_mapping["Mixing Operation - SJ"] = process_mapping[
		MIXING_PROCESS
	]  # TODO: Find a better way to do this rather than hardcoding the process name

	current_process = wo.operations[0].operation if wo.operations else ""

	next_process = process_mapping.get(current_process)

	if not next_process:
		frappe.throw(_("No next process found after {0}").format(current_process))

	bom_doc: BOM = frappe.get_doc("BOM", wo.bom_no)  # pyright: ignore

	slab_template = _get_slab_template_from_bom(bom_doc)

	next_wos = frappe.db.get_list(
		"Work Order",
		filters={
			"production_plan": wo.production_plan,
			"docstatus": ["<", 2],
			"production_item": ["like", f"%{slab_template}%"],
			"production_line": wo.production_line,
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
		next_wo = frappe.db.get_value(
			"Work Order",
			{
				"production_plan": wo.production_plan,
				"item_name": ["like", f"%{next_process}%"],
				"docstatus": ["<", 2],
				"production_item": ["like", f"%{slab_template}%"],
			},
			"name",
		)

	if not next_wo:
		frappe.throw(f"Next WO for '{next_process}' not found.")

	next_wo_doc = frappe.get_doc("Work Order", next_wo)
	open_job_card = frappe.db.get_value(
		"Job Card", {"work_order": next_wo, "status": "Open", "docstatus": 0}, "name", order_by="creation asc"
	)

	if not open_job_card:
		frappe.throw(f"No open job cards available")
	bom_doc = frappe.get_doc("BOM", next_wo_doc.bom_no)

	transfer_qty = 0
	for bom_item in bom_doc.items:
		if bom_item.item_code == fg_item:
			transfer_qty = flt(bom_item.stock_qty)
			break

	_set_job_card_completion_status(current_job_card, transfer_qty, fg_qty)

	if transfer_qty == 0:
		frappe.throw(f"BOM qty for {fg_item} not found in {next_wo} BOM")

	job_card_item = frappe.db.get_value(
		"Job Card Item", {"parent": open_job_card, "item_code": fg_item, "parenttype": "Job Card"}, "name"
	)

	if not job_card_item:
		frappe.throw(f"No Job Card Item found for {fg_item} in {open_job_card}")

	se: StockEntry = frappe.new_doc("Stock Entry")  # pyright: ignore
	se.purpose = "Material Transfer for Manufacture"
	se.work_order = next_wo  # pyright: ignore
	se.job_card = open_job_card  # pyright: ignore # No job card for inter-process transfer
	se.company = wo.company
	se.fg_completed_qty = transfer_qty
	se.previous_job_card = current_job_card

	se.append(
		"items",
		{
			"item_code": fg_item,
			"qty": transfer_qty,
			"stock_uom": wo.stock_uom,
			"uom": wo.stock_uom,
			"conversion_factor": 1.0,
			"s_warehouse": wo.fg_warehouse,
			"t_warehouse": next_wo_doc.wip_warehouse,
			"basic_rate": 0,
			"job_card_item": job_card_item,
		},
	)

	se.set_stock_entry_type()
	se.set_missing_values()
	se.submit()

	job_card_item_doc = frappe.get_doc("Job Card Item", job_card_item)
	job_card_item_doc.transferred_qty = transfer_qty
	job_card_item_doc.save(ignore_permissions=True)

	open_jc_doc = frappe.get_doc("Job Card", open_job_card)
	open_jc_doc.transferred_qty = sum(item.transferred_qty for item in open_jc_doc.items)
	if mixer_number:
		open_jc_doc.mixer_number = mixer_number
	open_jc_doc.save(ignore_permissions=True)

	frappe.db.commit()

	if process == "Mixing":
		frappe.publish_realtime("refresh_operator_station")

	return {
		"status": "Success",
		"transfer_se": se.name,
		"next_work_order": next_wo,
		"job_card": open_job_card,
		"job_card_item": job_card_item,
		"qty_transferred": transfer_qty,
		"from_warehouse": wo.fg_warehouse,
		"to_warehouse": next_wo_doc.wip_warehouse,
		"transferred_qty_updated": job_card_item_doc.transferred_qty,  # ✅ New!
		"header_transferred_qty": open_jc_doc.transferred_qty,
		"message": f"Transferred {fg_qty} {fg_item} to {next_wo}",
		"mixer_number": mixer_number,
	}


@frappe.whitelist()
def get_recent_job_card(operation, production_line=None):
	if operation == "Mixing":
		filters = {
			"status": ["in", ["Open", "Material Transferred", "Work In Progress", "Completed"]],
			"docstatus": [">=", 0],
			"operation": ["like", "%Mixing%"],
		}
	else:
		filters = {
			"status": ["in", ["Material Transferred", "Work In Progress"]],
			"docstatus": 0,
			"operation": ["like", f"%{operation}%"],
		}

	if production_line:
		filters["production_line"] = production_line

	job_cards = frappe.db.get_list(
		"Job Card",
		filters=filters,
		fields=["name", "operation", "status", "work_order"],
		order_by="creation asc",
	)

	if len(job_cards) == 0:
		frappe.throw(_("No job cards found for operation {0}").format(operation))
	return job_cards[0]


@frappe.whitelist()
def get_open_job_cards(
	process,
	line=None,
	include_wip=True,
	include_material_transferred=True,
	include_paused=True,
	item_code=None,, slab_template="", limit = 0
):
	is_mixing = process == "Mixing"
	if is_mixing:
		filters = {
			"status": ["in", ["Open", "Material Transferred", "Work In Progress", "Completed"]],
			"docstatus": [">=", 0],
			"operation": ["like", "%Mixing%"],
			"is_finished": ["=", "0"],
		}
	else:
		workstation_names = [x.workstation_name for x in _get_workstations(process)]

		if workstation_names:
			ws_query = ["in", workstation_names]
		else:
			ws_query = ["like", f"%{process}%"]

		in_query = []

		if include_material_transferred:
			in_query.append("Material Transferred")

		if include_wip:
			in_query.append("Work In Progress")

		if include_paused:
			in_query.append("On Hold")

		filters = {
			"status": ["in", in_query],
			"docstatus": ["=", "0"],
			"workstation": ws_query,
		}

	if slab_template:
		filters["production_item"] = ["like", f"{slab_template} - %"]

	if line:
		if isinstance(line, list):
			filters["production_line"] = ["in", line]
		else:
			filters["production_line"] = line

	if item_code:
		filters["production_item"] = ["like", f"%{item_code}%"]

	limit = limit or (
		9999999
		if not is_mixing
		or frappe.get_single_value("Mahi Granites Settings", "show_job_card_queue_to_mixer_operators")
		else 1
	)

	job_cards = frappe.get_all(
		"Job Card",
		limit=limit,
		filters=filters,
		fields=[
			"name",
			"work_order",
			"status",
			"production_item",
			"slab",
			"slab_template",
			"workstation",
			"workstation_type",
			"started_time",
			"creation",
			"modified",
			"production_line",
		],
		order_by="priority asc, status asc, creation asc",
		ignore_permissions=True,
	)

	return job_cards


def _get_workstations(workstation_type: str):
	return frappe.get_all(
		"Workstation",
		filters={"workstation_type": ["like", f"%{workstation_type}%"]},
		fields=["workstation_name"],
	)


@frappe.whitelist()
def get_operators(designation, production_line):
	filters = {
		"designation": designation,
		"production_line": production_line,
	}

	employee_name = frappe.db.get_value("Employee", filters, "name")

	if not employee_name:
		frappe.throw(f"No operator found: designation={designation}, line={production_line}")

	return employee_name


def _get_slab_template_from_bom(bom_doc):
	# template_components = bom_doc.slab_template.split("-") if bom_doc.slab_template else []
	# size_index = 2  # TODO: This depends on the template's naming structure. Use a reliable way to do it like fetching the slab template and then the size from within it.
	# for index, _ in enumerate(template_components):
	# 	if index == size_index:
	# 		temp = re.sub(r"0", "00", template_components[index])
	# 		template_components[index] = re.sub(r"00", "CM", temp)
	# slab_template = "-".join(template_components)
	return bom_doc.slab_template


def _set_job_card_completion_status(jc_name: str, bom_qty: float, fg_qty: float):
	jc: JobCard = frappe.get_doc("Job Card", jc_name)  # pyright: ignore
	prepared_qty = (fg_qty if fg_qty else jc.total_completed_qty) or 0  # pyright: ignore

	display_qty = flt(prepared_qty - bom_qty, 3)
	bom_qty = flt(bom_qty, 2)
	is_job_card_finished = display_qty < bom_qty and jc.status == "Completed"

	if is_job_card_finished:
		jc.is_finished = 1
		jc.priority = LOW_PRIORITY
		jc.save(ignore_permissions=True)
		jc.reload()
