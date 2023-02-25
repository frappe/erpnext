# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import add_days, cint, formatdate, time_diff_in_seconds, to_timedelta
from master.master.doctype.workstation.workstation import (
	NotInWorkingHoursError,
	Workstation,
	WorkstationHolidayError,
)

from erpnext.support.doctype.issue.issue import get_holidays


class ERPNextWorkstation(Workstation):
	def on_update(self):
		super(ERPNextWorkstation, self).on_update()
		self.update_bom_operation()

	def update_bom_operation(self):
		bo = frappe.qb.DocType("BOM Operation")
		bom_list = (
			frappe.qb.from_(bo)
			.select(bo.parent)
			.where((bo.workstation == self.name) & (bo.parenttype == "routing"))
			.distinct()
		).run()

		for bom_no in bom_list:
			(
				frappe.qb.update(bo)
				.set(bo.hour_rate, self.hour_rate)
				.where((bo.parent == bom_no[0]) & (bo.workstation == self.name))
			).run()

	def validate_workstation_holiday(self, schedule_date, skip_holiday_list_check=False):
		if not skip_holiday_list_check and (
			not self.holiday_list
			or cint(frappe.db.get_single_value("Manufacturing Settings", "allow_production_on_holidays"))
		):
			return schedule_date

		if schedule_date in tuple(get_holidays(self.holiday_list)):
			schedule_date = add_days(schedule_date, 1)
			self.validate_workstation_holiday(schedule_date, skip_holiday_list_check=True)

		return schedule_date


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

		holiday = frappe.qb.DocType("Holiday")
		for d in (
			frappe.qb.from_(holiday)
			.select(holiday.holiday_date)
			.where(
				(holiday.parent == holiday_list) & (holiday.holiday_date.between(from_datetime, to_datetime))
			)
		).run():
			applicable_holidays.append(formatdate(d[0]))

		if applicable_holidays:
			frappe.throw(
				_("Workstation is closed on the following dates as per Holiday List: {0}").format(holiday_list)
				+ "\n"
				+ "\n".join(applicable_holidays),
				WorkstationHolidayError,
			)
