import frappe
from frappe import _, bold
from frappe.utils import flt, now_datetime

from erpnext.manufacturing.page.shop_floor.services.job_cards import is_manager
from erpnext.manufacturing.page.shop_floor.services.station import BREAKDOWN, get_breakdown


def get_job_card(name, employee=None):
	doc = frappe.get_doc("Job Card", name)
	assigned = {row.employee for row in doc.employee}
	if employee and not is_manager() and employee not in assigned:
		frappe.throw(_("Job Card {0} is not assigned to {1}.").format(bold(name), bold(employee)))
	return doc


def start_job(job_card, employees, employee=None):
	doc = get_job_card(job_card, employee)
	if is_broken_down(doc.workstation):
		frappe.throw(
			_("{0} is stopped for a breakdown. Restart the machine first.").format(bold(doc.workstation))
		)
	doc.start_timer(start_time=now_datetime(), employees=[{"employee": name} for name in employees])


def resume_job(job_card, employee=None):
	doc = get_job_card(job_card, employee)
	if is_broken_down(doc.workstation):
		frappe.throw(
			_("{0} is stopped for a breakdown. Restart the machine first.").format(bold(doc.workstation))
		)
	doc.resume_job(start_time=now_datetime())


def complete_job(job_card, employee=None):
	doc = get_job_card(job_card, employee)
	left = flt(doc.for_quantity) - flt(doc.total_completed_qty) - flt(doc.process_loss_qty)
	if flt(left, doc.precision("total_completed_qty")) > 0:
		frappe.throw(
			_("{0} is still left on Job Card {1}.").format(bold(doc.get_qty_with_uom(left)), bold(doc.name))
		)
	doc.complete_job_card(end_time=now_datetime(), qty=0, auto_submit=1)


def assign_job_card(job_card, employees):
	if not is_manager():
		frappe.throw(_("Only a Shop Floor Manager can assign job cards."), frappe.PermissionError)

	doc = frappe.get_doc("Job Card", job_card)
	doc.set("employee", [{"employee": name} for name in employees])
	doc.save()
	return [row.employee for row in doc.employee]


def is_broken_down(workstation):
	return frappe.db.get_value("Workstation", workstation, "status") == "Problem"


def report_breakdown(workstation):
	running = get_running_job_cards(workstation)
	if not running:
		frappe.throw(_("Only a running machine can be stopped for a breakdown."))

	for doc in running:
		doc.pause_job(end_time=now_datetime(), reason=BREAKDOWN)
	frappe.get_doc("Workstation", workstation).db_set("status", "Problem", notify=True)


def get_running_job_cards(workstation):
	names = frappe.get_all(
		"Job Card", filters={"workstation": workstation, "docstatus": 0, "is_paused": 0}, pluck="name"
	)
	docs = [frappe.get_doc("Job Card", name) for name in names]
	return [doc for doc in docs if any(not log.to_time for log in doc.time_logs)]


def restart_machine(workstation, stop_reason, operator, remarks=None):
	if not is_broken_down(workstation):
		frappe.throw(_("{0} is not stopped for a breakdown.").format(bold(workstation)))

	breakdown = get_breakdown(workstation)
	downtime = frappe.get_doc(
		{
			"doctype": "Downtime Entry",
			"workstation": workstation,
			"operator": operator,
			"from_time": breakdown.to_time if breakdown else now_datetime(),
			"to_time": now_datetime(),
			"stop_reason": stop_reason,
			"remarks": remarks,
		}
	).insert()

	frappe.get_doc("Workstation", workstation).db_set("status", "Idle", notify=True)
	for doc in get_breakdown_job_cards(workstation):
		doc.resume_job(start_time=now_datetime())
	return downtime.name


def get_breakdown_job_cards(workstation):
	names = frappe.get_all(
		"Job Card", filters={"workstation": workstation, "docstatus": 0, "is_paused": 1}, pluck="name"
	)
	docs = [frappe.get_doc("Job Card", name) for name in names]
	return [doc for doc in docs if doc.time_logs and doc.time_logs[-1].pause_reason == BREAKDOWN]
