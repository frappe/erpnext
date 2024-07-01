# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	cint,
	comma_and,
	flt,
	formatdate,
	get_link_to_form,
	get_time,
	get_url_to_form,
	getdate,
	time_diff_in_hours,
	time_diff_in_seconds,
	to_timedelta,
)

from erpnext.support.doctype.issue.issue import get_holidays


class WorkstationHolidayError(frappe.ValidationError):
	pass


class NotInWorkingHoursError(frappe.ValidationError):
	pass


class OverlapError(frappe.ValidationError):
	pass


class Workstation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.workstation_working_hour.workstation_working_hour import (
			WorkstationWorkingHour,
		)

		description: DF.Text | None
		holiday_list: DF.Link | None
		hour_rate: DF.Currency
		hour_rate_consumable: DF.Currency
		hour_rate_electricity: DF.Currency
		hour_rate_labour: DF.Currency
		hour_rate_rent: DF.Currency
		off_status_image: DF.AttachImage | None
		on_status_image: DF.AttachImage | None
		plant_floor: DF.Link | None
		production_capacity: DF.Int
		working_hours: DF.Table[WorkstationWorkingHour]
		workstation_name: DF.Data
		workstation_type: DF.Link | None
	# end: auto-generated types

	def before_save(self):
		self.set_data_based_on_workstation_type()
		self.set_hour_rate()
		self.set_total_working_hours()

	def set_total_working_hours(self):
		self.total_working_hours = 0.0
		for row in self.working_hours:
			self.validate_working_hours(row)

			if row.start_time and row.end_time:
				row.hours = flt(time_diff_in_hours(row.end_time, row.start_time), row.precision("hours"))
				self.total_working_hours += row.hours

	def validate_working_hours(self, row):
		if not (row.start_time and row.end_time):
			frappe.throw(_("Row #{0}: Start Time and End Time are required").format(row.idx))

		if get_time(row.start_time) >= get_time(row.end_time):
			frappe.throw(_("Row #{0}: Start Time must be before End Time").format(row.idx))

	def set_hour_rate(self):
		self.hour_rate = (
			flt(self.hour_rate_labour)
			+ flt(self.hour_rate_electricity)
			+ flt(self.hour_rate_consumable)
			+ flt(self.hour_rate_rent)
		)

	@frappe.whitelist()
	def set_data_based_on_workstation_type(self):
		if self.workstation_type:
			fields = [
				"hour_rate_labour",
				"hour_rate_electricity",
				"hour_rate_consumable",
				"hour_rate_rent",
				"hour_rate",
				"description",
			]

			data = frappe.get_cached_value("Workstation Type", self.workstation_type, fields, as_dict=True)

			if not data:
				return

			for field in fields:
				if self.get(field):
					continue

				if value := data.get(field):
					self.set(field, value)

	def on_update(self):
		self.validate_overlap_for_operation_timings()
		self.update_bom_operation()

	def validate_overlap_for_operation_timings(self):
		"""Check if there is no overlap in setting Workstation Operating Hours"""
		for d in self.get("working_hours"):
			existing = frappe.db.sql_list(
				"""select idx from `tabWorkstation Working Hour`
				where parent = %s and name != %s
					and (
						(start_time between %s and %s) or
						(end_time between %s and %s) or
						(%s between start_time and end_time))
				""",
				(self.name, d.name, d.start_time, d.end_time, d.start_time, d.end_time, d.start_time),
			)

			if existing:
				frappe.throw(
					_("Row #{0}: Timings conflicts with row {1}").format(d.idx, comma_and(existing)),
					OverlapError,
				)

	def update_bom_operation(self):
		bom_list = frappe.db.sql(
			"""select DISTINCT parent from `tabBOM Operation`
			where workstation = %s and parenttype = 'routing' """,
			self.name,
		)

		for bom_no in bom_list:
			frappe.db.sql(
				"""update `tabBOM Operation` set hour_rate = %s
				where parent = %s and workstation = %s""",
				(self.hour_rate, bom_no[0], self.name),
			)

	def validate_workstation_holiday(self, schedule_date, skip_holiday_list_check=False):
		if not skip_holiday_list_check and (
			not self.holiday_list
			or cint(frappe.db.get_single_value("Manufacturing Settings", "allow_production_on_holidays"))
		):
			return schedule_date

		if schedule_date in tuple(get_holidays(self.holiday_list)):
			schedule_date = add_days(schedule_date, 1)
			return self.validate_workstation_holiday(schedule_date, skip_holiday_list_check=True)

		return schedule_date

	@frappe.whitelist()
	def start_job(self, job_card, from_time, employee):
		doc = frappe.get_doc("Job Card", job_card)
		doc.append("time_logs", {"from_time": from_time, "employee": employee})
		doc.save(ignore_permissions=True)

		return doc

	@frappe.whitelist()
	def complete_job(self, job_card, qty, to_time):
		doc = frappe.get_doc("Job Card", job_card)
		for row in doc.time_logs:
			if not row.to_time:
				row.to_time = to_time
				row.time_in_mins = time_diff_in_hours(row.to_time, row.from_time) / 60
				row.completed_qty = qty

		doc.save(ignore_permissions=True)
		doc.submit()

		return doc


@frappe.whitelist()
def get_job_cards(workstation):
	if frappe.has_permission("Job Card", "read"):
		jc_data = frappe.get_all(
			"Job Card",
			fields=[
				"name",
				"production_item",
				"work_order",
				"operation",
				"total_completed_qty",
				"for_quantity",
				"transferred_qty",
				"status",
				"expected_start_date",
				"expected_end_date",
				"time_required",
				"wip_warehouse",
			],
			filters={
				"workstation": workstation,
				"docstatus": ("<", 2),
				"status": ["not in", ["Completed", "Stopped"]],
			},
			order_by="expected_start_date, expected_end_date",
		)

		job_cards = [row.name for row in jc_data]
		raw_materials = get_raw_materials(job_cards)
		time_logs = get_time_logs(job_cards)

		allow_excess_transfer = frappe.db.get_single_value(
			"Manufacturing Settings", "job_card_excess_transfer"
		)

		for row in jc_data:
			row.progress_percent = (
				flt(row.total_completed_qty / row.for_quantity * 100, 2) if row.for_quantity else 0
			)
			row.progress_title = _("Total completed quantity: {0}").format(row.total_completed_qty)
			row.status_color = get_status_color(row.status)
			row.job_card_link = get_link_to_form("Job Card", row.name)
			row.work_order_link = get_link_to_form("Work Order", row.work_order)

			row.raw_materials = raw_materials.get(row.name, [])
			row.time_logs = time_logs.get(row.name, [])
			row.make_material_request = False
			if row.for_quantity > row.transferred_qty or allow_excess_transfer:
				row.make_material_request = True

		return jc_data


def get_status_color(status):
	color_map = {
		"Pending": "var(--bg-blue)",
		"In Process": "var(--bg-yellow)",
		"Submitted": "var(--bg-blue)",
		"Open": "var(--bg-gray)",
		"Closed": "var(--bg-green)",
		"Work In Progress": "var(--bg-orange)",
	}

	return color_map.get(status, "var(--bg-blue)")


def get_raw_materials(job_cards):
	raw_materials = {}

	data = frappe.get_all(
		"Job Card Item",
		fields=[
			"parent",
			"item_code",
			"item_group",
			"uom",
			"item_name",
			"source_warehouse",
			"required_qty",
			"transferred_qty",
		],
		filters={"parent": ["in", job_cards]},
	)

	for row in data:
		raw_materials.setdefault(row.parent, []).append(row)

	return raw_materials


def get_time_logs(job_cards):
	time_logs = {}

	data = frappe.get_all(
		"Job Card Time Log",
		fields=[
			"parent",
			"name",
			"employee",
			"from_time",
			"to_time",
			"time_in_mins",
		],
		filters={"parent": ["in", job_cards], "parentfield": "time_logs"},
		order_by="parent, idx",
	)

	for row in data:
		time_logs.setdefault(row.parent, []).append(row)

	return time_logs


@frappe.whitelist()
def get_default_holiday_list():
	return frappe.get_cached_value(
		"Company", frappe.defaults.get_user_default("Company"), "default_holiday_list"
	)


def check_if_within_operating_hours(workstation, operation, from_datetime, to_datetime):
	if from_datetime and to_datetime:
		if not frappe.db.get_single_value("Manufacturing Settings", "allow_production_on_holidays"):
			check_workstation_for_holiday(workstation, from_datetime, to_datetime)

		if not cint(frappe.db.get_value("Manufacturing Settings", None, "allow_overtime")):
			is_within_operating_hours(workstation, operation, from_datetime, to_datetime)


def is_within_operating_hours(workstation, operation, from_datetime, to_datetime):
	operation_length = time_diff_in_seconds(to_datetime, from_datetime)
	workstation = frappe.get_doc("Workstation", workstation)

	if not workstation.working_hours:
		return

	for working_hour in workstation.working_hours:
		if working_hour.start_time and working_hour.end_time:
			slot_length = (
				to_timedelta(working_hour.end_time or "") - to_timedelta(working_hour.start_time or "")
			).total_seconds()
			if slot_length >= operation_length:
				return

	frappe.throw(
		_(
			"Operation {0} longer than any available working hours in workstation {1}, break down the operation into multiple operations"
		).format(operation, workstation.name),
		NotInWorkingHoursError,
	)


def check_workstation_for_holiday(workstation, from_datetime, to_datetime):
	holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")
	if holiday_list and from_datetime and to_datetime:
		applicable_holidays = []
		for d in frappe.db.sql(
			"""select holiday_date from `tabHoliday` where parent = %s
			and holiday_date between %s and %s """,
			(holiday_list, getdate(from_datetime), getdate(to_datetime)),
		):
			applicable_holidays.append(formatdate(d[0]))

		if applicable_holidays:
			frappe.throw(
				_("Workstation is closed on the following dates as per Holiday List: {0}").format(
					holiday_list
				)
				+ "\n"
				+ "\n".join(applicable_holidays),
				WorkstationHolidayError,
			)


@frappe.whitelist()
def get_workstations(**kwargs):
	kwargs = frappe._dict(kwargs)
	_workstation = frappe.qb.DocType("Workstation")

	query = (
		frappe.qb.from_(_workstation)
		.select(
			_workstation.name,
			_workstation.description,
			_workstation.status,
			_workstation.on_status_image,
			_workstation.off_status_image,
		)
		.orderby(_workstation.workstation_type, _workstation.name)
		.where(_workstation.plant_floor == kwargs.plant_floor)
	)

	if kwargs.workstation:
		query = query.where(_workstation.name == kwargs.workstation)

	if kwargs.workstation_type:
		query = query.where(_workstation.workstation_type == kwargs.workstation_type)

	if kwargs.workstation_status:
		query = query.where(_workstation.status == kwargs.workstation_status)

	data = query.run(as_dict=True)

	color_map = {
		"Production": "var(--green-600)",
		"Off": "var(--gray-600)",
		"Idle": "var(--gray-600)",
		"Problem": "var(--red-600)",
		"Maintenance": "var(--yellow-600)",
		"Setup": "var(--blue-600)",
	}

	for d in data:
		d.workstation_name = get_link_to_form("Workstation", d.name)
		d.status_image = d.on_status_image
		d.background_color = color_map.get(d.status, "var(--red-600)")
		d.workstation_link = get_url_to_form("Workstation", d.name)
		if d.status != "Production":
			d.status_image = d.off_status_image

	return data
