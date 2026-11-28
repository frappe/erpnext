from collections import defaultdict

import frappe
from frappe.query_builder.functions import Date
from frappe.utils import flt, get_datetime, getdate, now_datetime

from erpnext.manufacturing.doctype.job_card.job_card import get_workstation_minutes


def get_workstation_oee(workstation: str) -> dict | None:
	"""
	OEE = Availability X Performance X Quality, computed for today only.

	Caveat: without a downtime-reason capture step, Availability is just
	(actual_run_time / scheduled_time) — it cannot distinguish planned breaks
	from unplanned breakdowns. The number is directional, not audit-grade.
	"""
	today = getdate()
	scheduled_min = flt(frappe.db.get_value("Workstation", workstation, "total_working_hours")) * 60
	actual_run_min, ideal_min, worked_job_cards = _get_run_and_ideal_minutes(workstation, today)
	completed_jcs = _get_completed_jcs_today(workstation, today)
	ideal_min += sum(
		flt(j.time_required) / flt(j.for_quantity) * flt(j.process_loss_qty)
		for j in completed_jcs
		if flt(j.for_quantity) and j.name in worked_job_cards
	)

	# No activity at all today — nothing to display.
	if actual_run_min == 0 and not completed_jcs:
		return None
	return _build_oee(scheduled_min, actual_run_min, ideal_min, completed_jcs)


def _get_run_and_ideal_minutes(workstation, today) -> tuple[float, float, set]:
	"""Sum actual run minutes (clipped to today) and the ideal minutes for produced qty."""
	today_start = get_datetime(f"{today} 00:00:00")
	today_end = get_datetime(f"{today} 23:59:59")
	now = now_datetime()
	ideal_min = 0.0
	run_intervals = defaultdict(list)
	for log in _get_oee_time_logs(workstation, today_start, today_end):
		# Clip the log's interval to today's window for fair attribution.
		start = max(get_datetime(log.from_time), today_start)
		end = min(get_datetime(log.to_time) if log.to_time else now, today_end)
		if end > start:
			run_intervals[log.job_card].append(frappe._dict(from_time=start, to_time=end))
		if log.completed_qty and log.for_quantity and log.time_required:
			ideal_min += (flt(log.time_required) / flt(log.for_quantity)) * flt(log.completed_qty)
	actual_run_min = sum(get_workstation_minutes(intervals) for intervals in run_intervals.values())
	return actual_run_min, ideal_min, set(run_intervals)


def _get_oee_time_logs(workstation, today_start, today_end) -> list[dict]:
	"""Job Card time logs whose interval overlaps today's window."""
	tl = frappe.qb.DocType("Job Card Time Log")
	jc = frappe.qb.DocType("Job Card")
	return (
		frappe.qb.from_(tl)
		.inner_join(jc)
		.on(jc.name == tl.parent)
		.select(
			jc.name.as_("job_card"),
			tl.from_time,
			tl.to_time,
			tl.completed_qty,
			jc.for_quantity,
			jc.time_required,
		)
		.where(jc.workstation == workstation)
		.where(jc.docstatus < 2)
		.where(tl.from_time <= today_end)
		.where(tl.to_time.isnull() | (tl.to_time >= today_start))
	).run(as_dict=True)


def _get_completed_jcs_today(workstation, today) -> list[dict]:
	"""Job cards completed/submitted today — process loss is finalized at submission."""
	jc = frappe.qb.DocType("Job Card")
	return (
		frappe.qb.from_(jc)
		.select(jc.name, jc.total_completed_qty, jc.process_loss_qty, jc.for_quantity, jc.time_required)
		.where(jc.workstation == workstation)
		.where(jc.status.isin(["Completed", "Submitted"]))
		.where(Date(jc.modified) == today)
	).run(as_dict=True)


def _build_oee(scheduled_min, actual_run_min, ideal_min, completed_jcs) -> dict:
	"""Combine the three OEE factors into the response payload."""
	total_completed = sum(flt(j.total_completed_qty) for j in completed_jcs)
	total_loss = sum(flt(j.process_loss_qty) for j in completed_jcs)
	availability = min(actual_run_min / scheduled_min, 1.0) if scheduled_min > 0 else None
	performance = min(ideal_min / actual_run_min, 1.0) if actual_run_min > 0 else 0.0
	total_made = total_completed + total_loss
	quality = total_completed / total_made if total_made > 0 else 1.0
	# OEE requires all three factors; without a schedule, Availability is unknown.
	oee_val = round(availability * performance * quality * 100, 1) if availability is not None else None
	return {
		"oee": oee_val,
		"availability": round(availability * 100, 1) if availability is not None else None,
		"performance": round(performance * 100, 1),
		"quality": round(quality * 100, 1),
	}
