# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import itertools

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime

from erpnext.manufacturing.doctype.job_card.job_card import OverlapError
from erpnext.manufacturing.scheduling.loaders import filter_covered_schedule_rows


class ProductionPlanSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		duration_mins: DF.Float
		from_time: DF.Datetime
		item_code: DF.Link | None
		item_name: DF.Data | None
		operation: DF.Link | None
		plan_row: DF.Data | None
		production_plan: DF.Link
		row_type: DF.Literal["Finished Good", "Sub Assembly", "Raw Material"]
		subject: DF.Data | None
		supplier: DF.Link | None
		task_key: DF.Data | None
		to_time: DF.Datetime
		workstation: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		if not self.flags.from_scheduler:
			frappe.throw(
				_(
					"Production Plan Schedule entries cannot be created manually. Use the Schedule Items action on the Production Plan."
				)
			)

	def validate(self):
		if get_datetime(self.from_time) >= get_datetime(self.to_time):
			frappe.throw(_("From Time must be before To Time"))

		self.validate_workstation_overlap()

	def validate_workstation_overlap(self):
		if not self.workstation:
			return

		frappe.db.get_value("Workstation", self.workstation, "name", for_update=True)
		from_time, to_time = get_datetime(self.from_time), get_datetime(self.to_time)
		bookings = get_overlapping_bookings(self, from_time, to_time)
		if not bookings:
			return

		capacity = cint(frappe.get_cached_value("Workstation", self.workstation, "production_capacity")) or 1
		conflict = get_capacity_conflict(bookings, from_time, to_time, capacity)
		if conflict:
			frappe.throw(
				_("Workstation {0} has no free capacity between {1} and {2}: overlaps with {3}").format(
					self.workstation, self.from_time, self.to_time, conflict
				),
				OverlapError,
			)


def get_overlapping_bookings(doc, from_time, to_time):
	bookings = get_schedule_bookings(doc, from_time, to_time)
	bookings += get_job_card_bookings(doc, from_time, to_time, "Job Card Scheduled Time", drafts_only=True)
	bookings += get_job_card_bookings(doc, from_time, to_time, "Job Card Time Log", drafts_only=False)
	return bookings


def get_schedule_bookings(doc, from_time, to_time):
	schedule = frappe.qb.DocType("Production Plan Schedule")
	plan = frappe.qb.DocType("Production Plan")

	rows = (
		frappe.qb.from_(schedule)
		.join(plan)
		.on(schedule.production_plan == plan.name)
		.select(
			schedule.name.as_("source"),
			schedule.from_time,
			schedule.to_time,
			schedule.production_plan,
			schedule.plan_row,
			schedule.operation,
		)
		.where(
			(schedule.workstation == doc.workstation)
			& (schedule.name != (doc.name or "New"))
			& (schedule.from_time < to_time)
			& (schedule.to_time > from_time)
			& (plan.docstatus < 2)
			& (plan.status != "Closed")
		)
		.for_update()
	).run(as_dict=True)

	return filter_covered_schedule_rows(rows)


def get_job_card_bookings(doc, from_time, to_time, doctype, drafts_only):
	child = frappe.qb.DocType(doctype)
	job_card = frappe.qb.DocType("Job Card")

	query = (
		frappe.qb.from_(child)
		.join(job_card)
		.on(child.parent == job_card.name)
		.select(job_card.name.as_("source"), child.from_time, child.to_time)
		.where(
			(job_card.workstation == doc.workstation)
			& (child.from_time < to_time)
			& (child.to_time > from_time)
		)
	)

	if drafts_only:
		query = query.where((job_card.docstatus == 0) & (job_card.total_time_in_mins == 0))
	else:
		query = query.where(job_card.docstatus < 2)

	return query.run(as_dict=True)


def get_capacity_conflict(bookings, from_time, to_time, capacity):
	points = {from_time, to_time}
	for row in bookings:
		points.add(max(get_datetime(row.from_time), from_time))
		points.add(min(get_datetime(row.to_time), to_time))

	for segment_start, segment_end in itertools.pairwise(sorted(points)):
		overlapping = [
			row
			for row in bookings
			if get_datetime(row.from_time) < segment_end and get_datetime(row.to_time) > segment_start
		]
		if len(overlapping) + 1 > capacity:
			return overlapping[0].source

	return None


def on_doctype_update():
	frappe.db.add_index("Production Plan Schedule", ["production_plan"])
	frappe.db.add_index("Production Plan Schedule", ["workstation", "from_time"])
