# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict
from typing import Any

import frappe
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import IfNull, Max, Sum
from frappe.utils import cint, flt, now_datetime, time_diff_in_seconds

from erpnext.manufacturing.doctype.job_card.job_card import CLOSED_WORK_ORDER_STATUSES

LIST_FIELDS = ["name", "status", "docstatus", "operation", "workstation", "for_quantity"]

TIMER_FIELDS = [
	"work_order",
	"is_paused",
	"process_loss_qty",
	"total_completed_qty",
	"manufactured_qty",
	"pending_qty",
	"skip_material_transfer",
	"is_corrective_job_card",
	"is_subcontracted",
]

# keep in sync with JOB_CARD_SEARCH_FIELDS in work_order.js
SEARCH_FIELDS = ["name", "operation", "workstation", "status"]

MAX_PAGE_LENGTH = 100


@frappe.whitelist()
def get_work_order_job_cards(
	work_order: str, start: int = 0, page_length: int = 20, txt: str | None = None
) -> list[dict]:
	frappe.has_permission("Work Order", "read", doc=work_order, throw=True)

	return get_timer_rows(
		{"work_order": work_order},
		or_filters=[[field, "like", f"%{txt}%"] for field in SEARCH_FIELDS] if txt else None,
		start=cint(start),
		page_length=min(max(cint(page_length), 1), MAX_PAGE_LENGTH),
	)


@frappe.whitelist()
def get_job_card_timer(job_card: str) -> dict:
	frappe.has_permission("Job Card", "read", doc=job_card, throw=True)
	return get_timer_rows({"name": job_card})[0]


def get_timer_rows(
	filters: dict, or_filters: list | None = None, start: int = 0, page_length: int = 1
) -> list[dict]:
	job_card = frappe.qb.DocType("Job Card")
	job_cards = (
		frappe.qb.get_query(
			"Job Card",
			fields=[*LIST_FIELDS, *TIMER_FIELDS],
			filters=filters,
			or_filters=or_filters,
			offset=start,
			limit=page_length,
			ignore_permissions=False,
		)
		# by sequence, unsequenced last; loaded pages are a prefix, so the list trusts its first startable row
		.orderby(Case().when(IfNull(job_card.sequence_id, 0) == 0, 1).else_(0))
		.orderby(job_card.sequence_id, job_card.creation, job_card.name)
		.run(as_dict=True)
	)
	attach_timer_summary(job_cards)

	timers = [JobCardTimer(job_card) for job_card in job_cards]
	return [timer.as_list_row(can_write=can_write(timer)) for timer in timers]


def can_write(timer: "JobCardTimer") -> bool:
	# only cards that would show a button need the per-card check
	return bool(timer.get_action()) and frappe.has_permission("Job Card", "write", doc=timer.job_card.name)


def attach_timer_summary(job_cards: list[dict]) -> None:
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
			# matches the Job Card form, which goes by the last log
			last_log_open=bool(summary) and any(log.idx == summary.last_idx for log in card_open_logs),
			employees=employees.get(job_card.name, []),
			has_pending_transfer=job_card.name in pending_transfer,
			has_sub_operations=job_card.name in with_sub_operations,
			work_order_status=work_order_statuses.get(job_card.work_order),
		)


def get_time_log_summary(names: list[str]) -> dict[str, frappe._dict]:
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
	"""Timer rules of the Job Card form dashboard, applied to a list row."""

	def __init__(self, job_card: dict) -> None:
		self.job_card = job_card

	def as_list_row(self, can_write: bool) -> dict:
		row = {fieldname: self.job_card.get(fieldname) for fieldname in LIST_FIELDS}
		row.update(
			elapsed_seconds=self.get_elapsed_seconds(),
			is_running=self.is_running(),
			open_log_count=len(self.job_card.open_log_starts),
			timer_action=self.get_action() if can_write else None,
			employees=self.job_card.employees,
		)
		return row

	def get_elapsed_seconds(self) -> int:
		now = now_datetime()
		open_seconds = sum(time_diff_in_seconds(now, start) for start in self.job_card.open_log_starts)
		return int(flt(self.job_card.logged_minutes) * 60 + open_seconds)

	def is_running(self) -> bool:
		return self.job_card.last_log_open and not self.job_card.is_paused

	def get_action(self) -> str | None:
		# the supplier does subcontracted work; the form shows no timer for it
		if self.job_card.docstatus != 0 or self.job_card.is_subcontracted:
			return None
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
		if not self.job_card.has_time_logs:
			return True
		has_cycles = flt(self.job_card.pending_qty) > 0 or self.job_card.has_sub_operations
		return has_cycles and not self.job_card.last_log_open

	def qty_yet_to_manufacture(self) -> float:
		job_card = self.job_card
		manufactured_qty = flt(job_card.manufactured_qty) or flt(job_card.total_completed_qty)
		return flt(job_card.for_quantity) - (manufactured_qty + flt(job_card.process_loss_qty))
