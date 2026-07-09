# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, bold
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
from frappe.utils.data import DateTimeLikeObject

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

		from erpnext.manufacturing.doctype.workstation_cost.workstation_cost import WorkstationCost
		from erpnext.manufacturing.doctype.workstation_working_hour.workstation_working_hour import (
			WorkstationWorkingHour,
		)

		description: DF.Text | None
		disabled: DF.Check
		holiday_list: DF.Link | None
		hour_rate: DF.Currency
		off_status_image: DF.AttachImage | None
		on_status_image: DF.AttachImage | None
		plant_floor: DF.Link | None
		production_capacity: DF.Int
		status: DF.Literal["Production", "Off", "Idle", "Problem", "Maintenance", "Setup"]
		total_working_hours: DF.Float
		warehouse: DF.Link | None
		working_hours: DF.Table[WorkstationWorkingHour]
		workstation_costs: DF.Table[WorkstationCost]
		workstation_name: DF.Data
		workstation_type: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_operating_component()

	def validate_duplicate_operating_component(self):
		components = []
		for row in self.workstation_costs:
			if row.operating_component not in components:
				components.append(row.operating_component)
			else:
				frappe.throw(
					_("Duplicate Operating Component {0} found in Operating Components").format(
						bold(row.operating_component)
					)
				)

	def before_save(self):
		if self.has_value_changed("workstation_type"):
			self._set_data_based_on_workstation_type()

		self.set_hour_rate()
		self.set_total_working_hours()
		self.disabled_workstation()

	def disabled_workstation(self):
		if self.disabled:
			self.status = "Off"

	def set_total_working_hours(self):
		self.total_working_hours = 0.0
		for row in self.working_hours:
			self.validate_working_hours(row)

			if row.start_time and row.end_time:
				row.hours = flt(time_diff_in_hours(row.end_time, row.start_time), row.precision("hours"))
				self.total_working_hours += row.hours

	def validate_working_hours(self, row):
		if get_time(row.start_time) >= get_time(row.end_time):
			frappe.throw(_("Row #{0}: Start Time must be before End Time").format(row.idx))

	def set_hour_rate(self):
		self.hour_rate = 0.0
		for row in self.workstation_costs:
			if row.operating_cost:
				self.hour_rate += flt(row.operating_cost)

	@frappe.whitelist()
	def set_data_based_on_workstation_type(self):
		self.check_permission("write")
		self._set_data_based_on_workstation_type()

	def _set_data_based_on_workstation_type(self):
		if self.workstation_type:
			data = frappe.get_all(
				"Workstation Cost",
				fields=["operating_component", "operating_cost", "idx"],
				filters={"parent": self.workstation_type, "parenttype": "Workstation Type"},
				order_by="idx",
			)

			if data:
				self.workstation_costs = []

			for row in data:
				self.append(
					"workstation_costs",
					{
						"operating_component": row.operating_component,
						"operating_cost": row.operating_cost,
						"idx": row.idx,
					},
				)

	def on_update(self):
		self.validate_overlap_for_operation_timings()
		self.update_bom_operation()

		if self.plant_floor:
			self.publish_workstation_status()

	def publish_workstation_status(self):
		if not self._doc_before_save:
			return

		if self._doc_before_save.get("status") == self.status:
			return

		data = get_workstations(plant_floor=self.plant_floor, workstation_name=self.name)[0]

		color_map = get_color_map()
		data["old_color"] = color_map.get(self._doc_before_save.get("status"), "red")

		frappe.publish_realtime(
			"update_workstation_status",
			data,
			doctype="Plant Floor",
			docname=self.plant_floor,
		)

	def validate_overlap_for_operation_timings(self):
		"""Check if there is no overlap in setting Workstation Operating Hours"""
		for d in self.get("working_hours"):
			wh = frappe.qb.DocType("Workstation Working Hour")
			existing = (
				frappe.qb.from_(wh)
				.select(wh.idx)
				.where(
					(wh.parent == self.name)
					& (wh.name != d.name)
					& (
						wh.start_time.between(d.start_time, d.end_time)
						| wh.end_time.between(d.start_time, d.end_time)
						| ((wh.start_time <= d.start_time) & (wh.end_time >= d.start_time))
					)
				)
				.run(pluck=True)
			)

			if existing:
				frappe.throw(
					_("Row #{0}: Timings conflict with row {1}").format(d.idx, comma_and(existing)),
					OverlapError,
				)

	def update_bom_operation(self):
		bom_list = frappe.get_all(
			"BOM Operation",
			# DocType is "Routing"; the original raw SQL used 'routing', which matched only via
			# MariaDB's case-insensitive collation and silently matched nothing on Postgres.
			filters={"workstation": self.name, "parenttype": "Routing"},
			pluck="parent",
			distinct=True,
		)

		if bom_list:
			bom_op = frappe.qb.DocType("BOM Operation")
			(
				frappe.qb.update(bom_op)
				.set(bom_op.hour_rate, self.hour_rate)
				.where(bom_op.parent.isin(bom_list) & (bom_op.workstation == self.name))
				.run()
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

	@frappe.whitelist(methods=["POST"])
	def start_job(self, job_card: str, from_time: DateTimeLikeObject, employee: str):
		doc = frappe.get_doc("Job Card", job_card)
		doc.check_permission("write")

		doc.append("time_logs", {"from_time": from_time, "employee": employee})
		doc.save()

		return doc

	@frappe.whitelist(methods=["POST"])
	def complete_job(self, job_card: str, qty: float, to_time: DateTimeLikeObject):
		doc = frappe.get_doc("Job Card", job_card)
		doc.check_permission("submit")

		for row in doc.time_logs:
			if not row.to_time:
				row.to_time = to_time
				row.time_in_mins = time_diff_in_hours(row.to_time, row.from_time) / 60
				row.completed_qty = qty

		doc.save()
		doc.submit()

		return doc


def get_status_color(status):
	color_map = {
		"Pending": "blue",
		"In Process": "yellow",
		"Submitted": "blue",
		"Open": "gray",
		"Closed": "green",
		"Completed": "green",
		"Work In Progress": "orange",
		"To Manufacture": "purple",
	}

	return color_map.get(status, "blue")


@frappe.whitelist()
def get_raw_materials(job_card: str):
	frappe.has_permission("Job Card", "read", doc=job_card, throw=True)

	raw_materials = frappe.get_all(
		"Job Card",
		fields=[
			"`tabJob Card`.`skip_material_transfer`",
			"`tabJob Card`.`backflush_from_wip_warehouse`",
			"`tabJob Card`.`wip_warehouse`",
			"`tabJob Card Item`.`parent`",
			"`tabJob Card Item`.`item_code`",
			"`tabJob Card Item`.`item_group`",
			"`tabJob Card Item`.`uom`",
			"`tabJob Card Item`.`item_name`",
			"`tabJob Card Item`.`source_warehouse`",
			"`tabJob Card Item`.`required_qty`",
			"`tabJob Card Item`.`transferred_qty`",
		],
		filters={"name": job_card},
	)

	if not raw_materials:
		return []

	for row in raw_materials:
		warehouse = row.source_warehouse
		if row.skip_material_transfer and row.backflush_from_wip_warehouse:
			warehouse = row.wip_warehouse

		row.stock_qty = (
			frappe.db.get_value(
				"Bin",
				{
					"item_code": row.item_code,
					"warehouse": warehouse,
				},
				"actual_qty",
			)
			or 0.0
		)

		row.warehouse = warehouse

		row.material_availability_status = 0
		if row.skip_material_transfer and row.stock_qty >= row.required_qty:
			row.material_availability_status = 1
		elif row.transferred_qty >= row.required_qty:
			row.material_availability_status = 1

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
def get_default_holiday_list(company: str | None = None):
	if company:
		if not frappe.has_permission("Company", "read"):
			return []

		if not frappe.db.exists("Company", company):
			return []

	if not company:
		company = frappe.defaults.get_user_default("Company")

	return frappe.get_cached_value("Company", company, "default_holiday_list")


def check_if_within_operating_hours(workstation, operation, from_datetime, to_datetime):
	if from_datetime and to_datetime:
		if not frappe.db.get_single_value("Manufacturing Settings", "allow_production_on_holidays"):
			check_workstation_for_holiday(workstation, from_datetime, to_datetime)

		if not cint(frappe.db.get_single_value("Manufacturing Settings", "allow_overtime")):
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
			"Operation {0} is longer than any available working hours in workstation {1}, break down the operation into multiple operations"
		).format(operation, workstation.name),
		NotInWorkingHoursError,
	)


def check_workstation_for_holiday(workstation, from_datetime, to_datetime):
	holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")
	if holiday_list and from_datetime and to_datetime:
		applicable_holidays = []
		for holiday_date in frappe.get_all(
			"Holiday",
			filters={
				"parent": holiday_list,
				"holiday_date": ["between", [getdate(from_datetime), getdate(to_datetime)]],
			},
			pluck="holiday_date",
		):
			applicable_holidays.append(formatdate(holiday_date))

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
	frappe.has_permission("Workstation", "read", throw=True)

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
		.orderby(_workstation.creation, _workstation.workstation_type, _workstation.name)
		.where((_workstation.plant_floor == kwargs.plant_floor) & (_workstation.disabled == 0))
	)

	if kwargs.workstation:
		query = query.where(_workstation.name == kwargs.workstation)

	if kwargs.workstation_type:
		query = query.where(_workstation.workstation_type == kwargs.workstation_type)

	if kwargs.workstation_status:
		query = query.where(_workstation.status == kwargs.workstation_status)

	if kwargs.workstation_name:
		query = query.where(_workstation.name == kwargs.workstation_name)

	data = query.run(as_dict=True)

	color_map = get_color_map()

	for d in data:
		d.workstation_name = get_link_to_form("Workstation", d.name)
		d.status_image = d.on_status_image
		d.workstation_off = ""
		d.color = color_map.get(d.status, "red")
		d.workstation_link = get_url_to_form("Workstation", d.name)
		if d.status != "Production":
			d.status_image = d.off_status_image
			d.workstation_off = "workstation-off"

	return data


def get_color_map():
	return {
		"Production": "green",
		"Off": "gray",
		"Idle": "gray",
		"Problem": "red",
		"Maintenance": "yellow",
		"Setup": "blue",
	}


ALLOWED_JOB_CARD_METHODS = frozenset(
	{
		"start_timer",
		"pause_job",
		"resume_job",
		"complete_job_card",
	}
)


@frappe.whitelist()
def update_job_card(job_card: str, method: str, **kwargs):
	if method not in ALLOWED_JOB_CARD_METHODS:
		frappe.throw(
			_("Method {0} is not allowed to be run on a Job Card.").format(bold(method)),
			frappe.PermissionError,
			title=_("Not Allowed"),
		)

	doc = frappe.get_doc("Job Card", job_card)
	doc.check_permission("write")

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	if kwargs.get("employees"):
		kwargs.employees = frappe.parse_json(kwargs.employees)

	if kwargs.qty and isinstance(kwargs.qty, str):
		kwargs.qty = flt(kwargs.qty)

	doc.run_method(method, **kwargs)


@frappe.whitelist()
def validate_job_card(job_card: str, status: str):
	frappe.has_permission("Job Card", "read", doc=job_card, throw=True)

	job_card_details = frappe.db.get_value("Job Card", job_card, ["status", "for_quantity"], as_dict=1)

	current_status = job_card_details.status
	if current_status != status:
		if status == "Open":
			frappe.throw(
				_("The job card {0} is in {1} state and you cannot start it again.").format(
					job_card, current_status
				)
			)
		else:
			frappe.throw(
				_("The job card {0} is in {1} state and you cannot complete it.").format(
					job_card, current_status
				)
			)

	return job_card_details.for_quantity
