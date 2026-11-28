from collections import defaultdict

import frappe
from frappe.utils import flt, getdate

from erpnext.manufacturing.page.shop_floor.services.job_cards import (
	get_employee_names,
	get_open_job_cards,
	is_manager,
)
from erpnext.manufacturing.page.shop_floor.services.oee import get_workstation_oee

BREAKDOWN = "Breakdown"


def get_station(workstation, employee=None):
	frappe.has_permission("Workstation", "read", doc=workstation, throw=True)
	job_cards = get_open_job_cards({"workstation": workstation})
	visible = [row for row in job_cards if can_see(row, employee)]
	current = next((row for row in job_cards if row.phase in ("running", "paused")), None)
	shown = current if current in visible else next((row for row in visible if row is not current), None)

	return {
		"workstation": get_workstation(workstation),
		"oee": get_workstation_oee(workstation),
		"busy": bool(current) and current not in visible,
		"job_card": get_job_card_detail(shown.name, shown) if shown else None,
		"queue": [row for row in visible if row is not shown],
		"done": get_done_today(workstation, employee),
		"activity": get_activity(workstation) if is_manager() or not current or current in visible else [],
	}


def can_see(job_card, employee):
	return is_manager() or (employee and employee in job_card.assigned)


def get_workstation(name):
	workstation = frappe.db.get_value(
		"Workstation", name, ["name", "workstation_name", "status", "warehouse", "plant_floor"], as_dict=True
	)
	workstation.breakdown = get_breakdown(name) if workstation.status == "Problem" else None
	workstation.stop_reasons = [
		row for row in (frappe.get_meta("Downtime Entry").get_options("stop_reason") or "").split("\n") if row
	]
	return workstation


def get_breakdown(workstation):
	log = frappe.qb.DocType("Job Card Time Log")
	job_card = frappe.qb.DocType("Job Card")
	rows = (
		frappe.qb.from_(log)
		.inner_join(job_card)
		.on(log.parent == job_card.name)
		.select(log.to_time, log.employee, job_card.name)
		.where(
			(job_card.workstation == workstation)
			& (job_card.docstatus == 0)
			& (log.parentfield == "time_logs")
			& (log.pause_reason == BREAKDOWN)
		)
		.orderby(log.to_time, order=frappe.qb.desc)
		.limit(1)
	).run(as_dict=True)
	return rows[0] if rows else None


def get_job_card_detail(name, summary):
	doc = frappe.get_doc("Job Card", name)
	left = flt(doc.for_quantity) - flt(doc.total_completed_qty) - flt(doc.process_loss_qty)
	max_qty = doc.get_max_completable_qty()
	return {
		**summary,
		"left_qty": flt(left, doc.precision("total_completed_qty")),
		"ready_qty": left if max_qty is None else max(flt(max_qty) - flt(doc.process_loss_qty), 0),
		"operation_count": frappe.db.count("Work Order Operation", {"parent": doc.work_order}),
		"is_process": bool(doc.track_semi_finished_goods),
		"items": get_items(doc),
		"pieces": get_pieces(doc),
		"loss_reasons": get_loss_reasons(doc.operation),
		"instructions": get_instructions(doc.operation),
		"needs_transfer": doc.is_material_transfer_pending(),
		"quality_required": is_quality_required(doc),
		"quality_inspection": doc.quality_inspection,
	}


def is_quality_required(doc):
	if doc.quality_inspection or not frappe.get_cached_value("BOM", doc.bom_no, "inspection_required"):
		return False
	return bool(frappe.db.get_value("Work Order Operation", doc.operation_id, "quality_inspection_required"))


def get_items(doc):
	return [
		{
			"item_code": row.item_code,
			"item_name": row.item_name,
			"required_qty": row.required_qty,
			"transferred_qty": row.transferred_qty,
			"uom": row.uom or row.stock_uom,
		}
		for row in doc.items
	]


def get_pieces(doc):
	totals = defaultdict(lambda: {"completed_qty": 0.0, "process_loss_qty": 0.0})
	for log in doc.time_logs:
		if log.employee:
			totals[log.employee]["completed_qty"] += flt(log.completed_qty)
			totals[log.employee]["process_loss_qty"] += flt(log.process_loss_qty)
	names = get_employee_names(set(totals))
	return [
		{"employee": employee, "employee_name": names.get(employee), **qty}
		for employee, qty in totals.items()
	]


def get_loss_reasons(operation):
	log = frappe.qb.DocType("Job Card Time Log")
	job_card = frappe.qb.DocType("Job Card")
	rows = (
		frappe.qb.from_(log)
		.inner_join(job_card)
		.on(log.parent == job_card.name)
		.select(log.loss_reason)
		.distinct()
		.where((job_card.operation == operation) & log.loss_reason.isnotnull() & (log.loss_reason != ""))
		.limit(12)
	).run(pluck=True)
	return rows


def get_instructions(operation):
	if not operation:
		return None
	return frappe.get_cached_value("Operation", operation, ["description", "work_instruction"], as_dict=True)


def get_done_today(workstation, employee):
	job_cards = frappe.get_all(
		"Job Card",
		filters={"workstation": workstation, "docstatus": 1, "actual_end_date": (">=", getdate())},
		fields=[
			"name",
			"work_order",
			"operation",
			"production_item",
			"item_name",
			"for_quantity",
			"total_completed_qty",
			"process_loss_qty",
			"stock_uom",
		],
		order_by="actual_end_date desc",
		limit=20,
	)
	if is_manager() or not employee:
		return job_cards
	mine = (
		set(
			frappe.get_all(
				"Job Card Time Log",
				filters={"parent": ("in", [row.name for row in job_cards]), "employee": employee},
				pluck="parent",
			)
		)
		if job_cards
		else set()
	)
	return [row for row in job_cards if row.name in mine]


def get_activity(workstation):
	log = frappe.qb.DocType("Job Card Time Log")
	job_card = frappe.qb.DocType("Job Card")
	rows = (
		frappe.qb.from_(log)
		.inner_join(job_card)
		.on(log.parent == job_card.name)
		.select(
			job_card.name.as_("job_card"),
			job_card.operation,
			log.employee,
			log.from_time,
			log.to_time,
			log.completed_qty,
			log.process_loss_qty,
			log.loss_reason,
			log.pause_reason,
		)
		.where(
			(job_card.workstation == workstation)
			& (log.parentfield == "time_logs")
			& (log.from_time >= getdate())
		)
		.orderby(log.from_time, order=frappe.qb.desc)
		.limit(40)
	).run(as_dict=True)
	downtime = frappe.get_all(
		"Downtime Entry",
		filters={"workstation": workstation, "from_time": (">=", getdate())},
		fields=["name", "from_time", "to_time", "downtime", "stop_reason", "operator"],
		order_by="from_time desc",
	)
	names = get_employee_names({row.employee for row in rows if row.employee})
	return {"logs": rows, "downtime": downtime, "names": names}
