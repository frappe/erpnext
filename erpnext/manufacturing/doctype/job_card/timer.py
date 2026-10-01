# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Live timer state of Job Cards, for the Job Card list embedded in the Work Order."""

from collections import defaultdict
from typing import Any

import frappe
from frappe.core.doctype.user_permission.user_permission import get_user_permissions
from frappe.permissions import get_role_permissions
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Max, Sum
from frappe.utils import cint, flt, now_datetime, time_diff_in_seconds

from erpnext.manufacturing.doctype.job_card.job_card import CLOSED_WORK_ORDER_STATUSES

# shown in the list
LIST_FIELDS = ["name", "status", "docstatus", "operation", "workstation", "for_quantity"]

# only needed to work out the timer state
TIMER_FIELDS = [
	"work_order",
	"is_paused",
	"process_loss_qty",
	"total_completed_qty",
	"manufactured_qty",
	"pending_qty",
	"skip_material_transfer",
	"is_corrective_job_card",
]

# the list's search box matches these visible columns (kept in step with work_order.js)
SEARCH_FIELDS = ["name", "operation", "workstation", "status"]

# upper bound on one page, so a caller cannot ask for every Job Card at once
MAX_PAGE_LENGTH = 100


@frappe.whitelist()
def get_work_order_job_cards(
	work_order: str, start: int = 0, page_length: int = 20, txt: str | None = None
) -> list[dict]:
	"""Return one page of a Work Order's Job Cards, each with its elapsed time and next timer action.

	Follows the EmbeddedList `get_page` contract; `txt` searches the visible columns.
	"""
	frappe.has_permission("Work Order", "read", doc=work_order, throw=True)

	return get_timer_rows(
		{"work_order": work_order},
		or_filters=[[field, "like", f"%{txt}%"] for field in SEARCH_FIELDS] if txt else None,
		start=cint(start),
		page_length=min(max(cint(page_length), 1), MAX_PAGE_LENGTH),
	)


@frappe.whitelist()
def get_job_card_timer(job_card: str) -> dict:
	"""Return one Job Card's list row with its timer state, to refresh it after a timer action."""
	frappe.has_permission("Job Card", "read", doc=job_card, throw=True)
	return get_timer_rows({"name": job_card})[0]


def get_timer_rows(
	filters: dict, or_filters: list | None = None, start: int = 0, page_length: int = 1
) -> list[dict]:
	"""Return the matching Job Cards as list rows carrying their timer state."""
	job_cards = frappe.get_list(
		"Job Card",
		filters=filters,
		or_filters=or_filters,
		fields=[*LIST_FIELDS, *TIMER_FIELDS],
		order_by="creation desc, name desc",
		start=start,
		page_length=page_length,
	)
	attach_timer_summary(job_cards)

	timers = [JobCardTimer(job_card) for job_card in job_cards]
	# only cards that would offer an action need the write check
	writable = get_writable_job_cards([timer.job_card.name for timer in timers if timer.get_action()])

	return [timer.as_list_row(can_write=timer.job_card.name in writable) for timer in timers]


def get_writable_job_cards(names: list[str]) -> set[str]:
	"""The given Job Cards the session user may write, decided for the doctype where possible.

	Gives the same answer as a document-level `has_permission` per card: permission hooks
	and User Permissions can only deny, and a share can only grant, so the per-card check
	is needed only when roles grant write and something document-specific could deny it.
	"""
	if not names:
		return set()

	role_permissions = get_role_permissions(frappe.get_meta("Job Card"))
	write_if_owner = "write" in role_permissions.get("if_owner", {})
	if not role_permissions.get("write") and not write_if_owner:
		return set(
			frappe.share.get_shared("Job Card", rights=["write"], filters=[["share_name", "in", names]])
		)

	if role_permissions.get("write") and not has_document_specific_permission_rules():
		return set(names)

	return {name for name in names if frappe.has_permission("Job Card", "write", doc=name)}


def has_document_specific_permission_rules() -> bool:
	"""Whether a permission hook or a User Permission could deny write on some Job Cards."""
	hooks = frappe.get_hooks("has_permission")
	return bool(hooks.get("Job Card") or hooks.get("*") or get_user_permissions())


def attach_timer_summary(job_cards: list[dict]) -> None:
	"""Attach what the timer needs to each Job Card without loading its time log history.

	Closed logs are summed in the database; only open logs (one per active employee)
	and assigned employees come back as rows.
	"""
	names = [job_card.name for job_card in job_cards]
	if not names:
		return

	item = frappe.qb.DocType("Job Card Item")

	time_log_summary = get_time_log_summary(names)
	open_logs = get_open_time_logs(names)
	employees = get_assigned_employees(names)
	pending_transfer = get_parents_with_rows(
		"Job Card Item", "items", names, IfNull(item.transferred_qty, 0) < item.required_qty
	)
	with_sub_operations = get_parents_with_rows("Job Card Operation", "sub_operations", names)
	work_order_statuses = get_work_order_statuses(job_cards)

	for job_card in job_cards:
		summary = time_log_summary.get(job_card.name)
		card_open_logs = open_logs[job_card.name]
		job_card.update(
			has_time_logs=summary is not None,
			logged_minutes=summary.logged_minutes if summary else 0,
			open_log_starts=[log.from_time for log in card_open_logs],
			# the Job Card form judges running / restartable by the last log only
			last_log_open=bool(summary) and any(log.idx == summary.last_idx for log in card_open_logs),
			employees=employees.get(job_card.name, []),
			has_pending_transfer=job_card.name in pending_transfer,
			has_sub_operations=job_card.name in with_sub_operations,
			work_order_status=work_order_statuses.get(job_card.work_order),
		)


def get_time_log_summary(names: list[str]) -> dict[str, frappe._dict]:
	"""Per Job Card: minutes of closed time logs and the idx of its last log."""
	time_log = frappe.qb.DocType("Job Card Time Log")
	rows = (
		frappe.qb.from_(time_log)
		.select(
			time_log.parent,
			Sum(IfNull(time_log.time_in_mins, 0)).as_("logged_minutes"),
			Max(time_log.idx).as_("last_idx"),
		)
		.where(child_rows_criterion(time_log, "time_logs", names))
		.groupby(time_log.parent)
		.run(as_dict=True)
	)
	return {row.parent: row for row in rows}


def get_open_time_logs(names: list[str]) -> dict[str, list[frappe._dict]]:
	"""Time logs without a to time (one per active employee), per Job Card."""
	time_log = frappe.qb.DocType("Job Card Time Log")
	rows = (
		frappe.qb.from_(time_log)
		.select(time_log.parent, time_log.idx, time_log.from_time)
		.where(child_rows_criterion(time_log, "time_logs", names) & time_log.to_time.isnull())
		.where(time_log.from_time.isnotnull())
		.run(as_dict=True)
	)
	return group_by_parent(rows)


def get_assigned_employees(names: list[str]) -> dict[str, list[str]]:
	time_log = frappe.qb.DocType("Job Card Time Log")
	rows = (
		frappe.qb.from_(time_log)
		.select(time_log.parent, time_log.employee)
		.where(child_rows_criterion(time_log, "employee", names) & time_log.employee.isnotnull())
		.orderby(time_log.idx)
		.run(as_dict=True)
	)
	return {parent: [row.employee for row in rows] for parent, rows in group_by_parent(rows).items()}


def group_by_parent(rows: list[frappe._dict]) -> dict[str, list[frappe._dict]]:
	grouped = defaultdict(list)
	for row in rows:
		grouped[row.parent].append(row)
	return grouped


def get_parents_with_rows(
	child_doctype: str, parentfield: str, names: list[str], condition: Criterion | None = None
) -> set[str]:
	"""Job Cards having at least one row in the child table, optionally matching `condition`."""
	child = frappe.qb.DocType(child_doctype)
	query = (
		frappe.qb.from_(child)
		.select(child.parent)
		.distinct()
		.where(child_rows_criterion(child, parentfield, names))
	)
	if condition is not None:
		query = query.where(condition)
	return set(query.run(pluck=True))


def child_rows_criterion(child: Any, parentfield: str, names: list[str]) -> Criterion:
	"""Rows of the given Job Card child table belonging to the given Job Cards."""
	return (child.parenttype == "Job Card") & (child.parentfield == parentfield) & child.parent.isin(names)


def get_work_order_statuses(job_cards: list[dict]) -> dict[str, str]:
	work_orders = {job_card.work_order for job_card in job_cards if job_card.work_order}
	if not work_orders:
		return {}

	rows = frappe.get_all(
		"Work Order", filters={"name": ("in", list(work_orders))}, fields=["name", "status"]
	)
	return {row.name: row.status for row in rows}


class JobCardTimer:
	"""Elapsed time and the Start / Pause / Resume action available for a Job Card.

	Mirrors the rules of the Job Card form dashboard. Works on a Job Card list row
	carrying the summary from `attach_timer_summary`.
	"""

	def __init__(self, job_card: dict) -> None:
		self.job_card = job_card

	def as_list_row(self, can_write: bool) -> dict:
		"""Return the Job Card's list fields with its timer state.

		Timer actions write to the Job Card, so a read-only user only sees the time.
		"""
		row = {fieldname: self.job_card.get(fieldname) for fieldname in LIST_FIELDS}
		row.update(
			elapsed_seconds=self.get_elapsed_seconds(),
			is_running=self.is_running(),
			# elapsed time grows by one second per open log, whether or not the last log is open
			open_log_count=len(self.job_card.open_log_starts),
			timer_action=self.get_action() if can_write else None,
			employees=self.job_card.employees,
		)
		return row

	def get_elapsed_seconds(self) -> int:
		"""Total time logged on the Job Card, counting open logs up to now."""
		now = now_datetime()
		open_seconds = sum(time_diff_in_seconds(now, start) for start in self.job_card.open_log_starts)
		return int(flt(self.job_card.logged_minutes) * 60 + open_seconds)

	def is_running(self) -> bool:
		"""Whether the clock is ticking: the last log is open and the job is not paused (On Hold)."""
		return self.job_card.last_log_open and not self.job_card.is_paused

	def get_action(self) -> str | None:
		"""Return "start", "pause" or "resume", whichever the operator can take now, else None.

		Only drafts qualify: a Completed Job Card is always submitted and a Cancelled one cancelled.
		"""
		if self.job_card.docstatus != 0:
			return None
		# the Job Card refuses any change once its Work Order is closed or stopped
		if self.job_card.work_order_status in CLOSED_WORK_ORDER_STATUSES:
			return None
		if not self.has_remaining_qty() or not self.materials_ready():
			return None
		if self.job_card.is_paused:
			return "resume"
		if self.can_start():
			return "start"
		if self.qty_yet_to_manufacture() > 0:
			return "pause"
		return None

	def has_remaining_qty(self) -> bool:
		job_card = self.job_card
		return flt(job_card.for_quantity) + flt(job_card.process_loss_qty) > flt(job_card.total_completed_qty)

	def materials_ready(self) -> bool:
		if self.job_card.skip_material_transfer or self.job_card.is_corrective_job_card:
			return True
		return not self.job_card.has_pending_transfer

	def can_start(self) -> bool:
		"""A job starts fresh, or again once a pending-qty or sub-operation cycle has closed."""
		if not self.job_card.has_time_logs:
			return True
		has_cycles = flt(self.job_card.pending_qty) > 0 or self.job_card.has_sub_operations
		return has_cycles and not self.job_card.last_log_open

	def qty_yet_to_manufacture(self) -> float:
		job_card = self.job_card
		manufactured_qty = flt(job_card.manufactured_qty) or flt(job_card.total_completed_qty)
		return flt(job_card.for_quantity) - (manufactured_qty + flt(job_card.process_loss_qty))
