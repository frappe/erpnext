# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Live timer state of Job Cards, for the Job Card list embedded in the Work Order."""

from collections import defaultdict
from typing import Any

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt, now_datetime, time_diff_in_seconds

from erpnext.manufacturing.doctype.job_card.job_card import CLOSED_WORK_ORDER_STATUSES

LIST_FIELDS = [
	"name",
	"status",
	"docstatus",
	"operation",
	"workstation",
	"for_quantity",
	"is_paused",
	"process_loss_qty",
	"total_completed_qty",
	"manufactured_qty",
	"pending_qty",
	"skip_material_transfer",
	"is_corrective_job_card",
]

CLOSED_STATUSES = ("Completed", "Cancelled")


@frappe.whitelist()
def get_work_order_job_cards(work_order: str) -> list[dict]:
	"""Return the Job Cards of a Work Order, each with its elapsed time and next timer action."""
	frappe.has_permission("Work Order", "read", doc=work_order, throw=True)
	return get_timer_rows({"work_order": work_order})


@frappe.whitelist()
def get_job_card_timer(job_card: str) -> dict:
	"""Return one Job Card's list row with its timer state, to refresh it after a timer action."""
	frappe.has_permission("Job Card", "read", doc=job_card, throw=True)
	return get_timer_rows({"name": job_card})[0]


def get_timer_rows(filters: dict) -> list[dict]:
	"""Return the matching Job Cards as list rows carrying their timer state."""
	job_cards = frappe.get_list(
		"Job Card", filters=filters, fields=[*LIST_FIELDS, "work_order"], order_by="creation desc"
	)
	attach_timer_summary(job_cards)

	return [JobCardTimer(job_card).as_list_row() for job_card in job_cards]


def attach_timer_summary(job_cards: list[dict]) -> None:
	"""Attach what the timer needs to each Job Card without loading its time log history.

	Closed logs are summed in the database; only open logs (one per active employee)
	and assigned employees come back as rows.
	"""
	names = [job_card.name for job_card in job_cards]
	if not names:
		return

	logged_minutes = get_logged_minutes(names)
	open_log_starts = get_child_values("Job Card Time Log", "time_logs", "from_time", names, open_only=True)
	employees = get_child_values("Job Card Time Log", "employee", "employee", names)
	pending_transfer = get_parents_with_pending_transfer(names)
	with_sub_operations = get_parents_with_rows("Job Card Operation", "sub_operations", names)
	work_order_statuses = get_work_order_statuses(job_cards)

	for job_card in job_cards:
		job_card.update(
			has_time_logs=job_card.name in logged_minutes,
			logged_minutes=logged_minutes.get(job_card.name, 0),
			open_log_starts=open_log_starts[job_card.name],
			employees=employees[job_card.name],
			has_pending_transfer=job_card.name in pending_transfer,
			has_sub_operations=job_card.name in with_sub_operations,
			work_order_status=work_order_statuses.get(job_card.work_order),
		)


def get_work_order_statuses(job_cards: list[dict]) -> dict[str, str]:
	work_orders = {job_card.work_order for job_card in job_cards if job_card.work_order}
	if not work_orders:
		return {}

	rows = frappe.get_all(
		"Work Order", filters={"name": ("in", list(work_orders))}, fields=["name", "status"]
	)
	return {row.name: row.status for row in rows}


def get_logged_minutes(names: list[str]) -> dict[str, float]:
	"""Minutes of closed time logs per Job Card; a card with only open logs maps to 0."""
	time_log = frappe.qb.DocType("Job Card Time Log")
	rows = (
		frappe.qb.from_(time_log)
		.select(time_log.parent, Sum(IfNull(time_log.time_in_mins, 0)))
		.where(child_rows_criterion(time_log, "time_logs", names))
		.groupby(time_log.parent)
		.run()
	)
	return {parent: flt(minutes) for parent, minutes in rows}


def get_child_values(
	child_doctype: str, parentfield: str, fieldname: str, names: list[str], open_only: bool = False
) -> dict[str, list]:
	"""One field of a child table per Job Card, in table order. `open_only` keeps logs without a to time."""
	filters = {"parenttype": "Job Card", "parentfield": parentfield, "parent": ("in", names)}
	if open_only:
		filters["to_time"] = ("is", "not set")

	values = defaultdict(list)
	for row in frappe.get_all(child_doctype, filters=filters, fields=["parent", fieldname], order_by="idx"):
		if row[fieldname]:
			values[row.parent].append(row[fieldname])
	return values


def get_parents_with_pending_transfer(names: list[str]) -> set[str]:
	item = frappe.qb.DocType("Job Card Item")
	return get_parents_with_rows(
		"Job Card Item", "items", names, IfNull(item.transferred_qty, 0) < item.required_qty
	)


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


class JobCardTimer:
	"""Elapsed time and the Start / Pause / Resume action available for a Job Card.

	Mirrors the rules of the Job Card form dashboard. Works on a Job Card list row
	carrying the summary from `attach_timer_summary`.
	"""

	def __init__(self, job_card: dict) -> None:
		self.job_card = job_card

	def as_list_row(self) -> dict:
		"""Return the Job Card's list fields with its timer state."""
		row = {fieldname: self.job_card.get(fieldname) for fieldname in LIST_FIELDS}
		row.update(
			elapsed_seconds=self.get_elapsed_seconds(),
			is_running=self.is_running(),
			timer_action=self.get_action(),
			employees=self.job_card.employees,
		)
		return row

	def get_elapsed_seconds(self) -> int:
		"""Total time logged on the Job Card, counting open logs up to now."""
		now = now_datetime()
		open_seconds = sum(time_diff_in_seconds(now, start) for start in self.job_card.open_log_starts)
		return int(flt(self.job_card.logged_minutes) * 60 + open_seconds)

	def has_open_log(self) -> bool:
		return bool(self.job_card.open_log_starts)

	def is_running(self) -> bool:
		"""Whether the clock is ticking: a log is open and the job is not on hold."""
		if not self.has_open_log():
			return False
		return not self.job_card.is_paused and self.job_card.status != "On Hold"

	def get_action(self) -> str | None:
		"""Return "start", "pause" or "resume", whichever the operator can take now, else None."""
		if self.job_card.docstatus != 0 or self.job_card.status in CLOSED_STATUSES:
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
		return has_cycles and not self.has_open_log()

	def qty_yet_to_manufacture(self) -> float:
		job_card = self.job_card
		manufactured_qty = flt(job_card.manufactured_qty) or flt(job_card.total_completed_qty)
		return flt(job_card.for_quantity) - (manufactured_qty + flt(job_card.process_loss_qty))
