from collections import defaultdict

import frappe
from frappe import _
from frappe.core.doctype.user_permission.user_permission import get_user_permissions
from frappe.utils import flt, get_datetime, now_datetime, time_diff_in_seconds

MANAGER_ROLES = {"Shop Floor Manager", "Manufacturing Manager", "System Manager"}

JOB_CARD_FIELDS = [
	"name",
	"work_order",
	"operation",
	"workstation",
	"production_item",
	"item_name",
	"finished_good",
	"for_quantity",
	"total_completed_qty",
	"process_loss_qty",
	"stock_uom",
	"status",
	"is_paused",
	"sequence_id",
	"track_semi_finished_goods",
	"expected_start_date",
]

LOG_FIELDS = ["parent", "parentfield", "employee", "from_time", "to_time", "time_in_mins", "completed_qty"]


def is_manager():
	return bool(set(frappe.get_roles()) & MANAGER_ROLES)


def get_open_job_cards(filters, limit=500):
	job_cards = frappe.get_list(
		"Job Card",
		filters={"docstatus": 0, "status": ("!=", "Cancelled"), **filters},
		fields=JOB_CARD_FIELDS,
		order_by="expected_start_date asc, sequence_id asc, creation asc",
		limit=limit,
	)
	add_people(job_cards)
	return job_cards


def add_people(job_cards):
	rows = get_people_rows([row.name for row in job_cards])
	names = get_employee_names({row.employee for logs in rows.values() for row in logs if row.employee})
	now = now_datetime()
	for job_card in job_cards:
		job_card.names = {
			row.employee: names.get(row.employee) for row in rows[job_card.name] if row.employee
		}
		logs = [row for row in rows[job_card.name] if row.parentfield == "time_logs"]
		running = [row for row in logs if row.from_time and not row.to_time]
		job_card.update(
			assigned=[row.employee for row in rows[job_card.name] if row.parentfield == "employee"],
			crew=[row.employee for row in running if row.employee],
			worked_seconds=get_worked_seconds(logs, now),
			running=bool(running),
			phase=get_phase(job_card, running),
		)


def get_people_rows(names):
	rows = defaultdict(list)
	if not names:
		return rows

	for row in frappe.get_all(
		"Job Card Time Log",
		filters={"parenttype": "Job Card", "parent": ("in", names)},
		fields=LOG_FIELDS,
		order_by="idx asc",
	):
		rows[row.parent].append(row)
	return rows


def get_worked_seconds(logs, now):
	seconds = 0.0
	for log in logs:
		if log.to_time:
			seconds += flt(log.time_in_mins) * 60
		elif log.from_time:
			seconds += time_diff_in_seconds(now, get_datetime(log.from_time))
	return int(seconds)


def get_phase(job_card, running):
	if job_card.is_paused:
		return "paused"
	if running:
		return "running"
	if job_card.status == "Completed":
		return "done"
	return "open"


def get_assigned_job_card_names(employee):
	return frappe.get_all(
		"Job Card Time Log",
		filters={"parenttype": "Job Card", "parentfield": "employee", "employee": employee},
		pluck="parent",
	)


def get_employee_names(employees):
	if not employees:
		return {}
	return dict(
		frappe.get_all(
			"Employee",
			filters={"name": ("in", list(employees))},
			fields=["name", "employee_name"],
			as_list=True,
		)
	)


def get_allowed_employees():
	if is_manager():
		return None
	rows = get_user_permissions(frappe.session.user).get("Employee") or []
	return sorted({row.get("doc") for row in rows}) or None


def validate_employees(employees):
	allowed = get_allowed_employees()
	if allowed is None:
		return

	if others := [name for name in employees if name and name not in allowed]:
		frappe.throw(
			_("You cannot work on the Shop Floor as {0}.").format(", ".join(others)), frappe.PermissionError
		)
