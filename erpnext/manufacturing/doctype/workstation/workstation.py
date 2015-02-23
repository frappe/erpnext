# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.utils import flt, cint, getdate, formatdate, comma_and

from frappe.model.document import Document

class WorkstationHolidayError(frappe.ValidationError): pass
class NotInWorkingHoursError(frappe.ValidationError): pass
class OverlapError(frappe.ValidationError): pass

class Workstation(Document):
	def update_bom_operation(self):
		bom_list = frappe.db.sql("""select DISTINCT parent from `tabBOM Operation`
			where workstation = %s""", self.name)
		for bom_no in bom_list:
			frappe.db.sql("""update `tabBOM Operation` set hour_rate = %s
				where parent = %s and workstation = %s""",
				(self.hour_rate, bom_no[0], self.name))

	def on_update(self):
		self.validate_overlap_for_operation_timings()

		frappe.db.set(self, 'hour_rate', flt(self.hour_rate_labour) + flt(self.hour_rate_electricity) +
			flt(self.hour_rate_consumable) + flt(self.hour_rate_rent))

		self.update_bom_operation()

	def validate_overlap_for_operation_timings(self):
		"""Check if there is no overlap in setting Workstation Operating Hours"""
		for d in self.get("working_hours"):
			existing = frappe.db.sql_list("""select idx from `tabWorkstation Working Hour`
				where parent = %s and name != %s
					and (
						(start_time between %s and %s) or
						(end_time between %s and %s) or
						(%s between start_time and end_time))
				""", (self.name, d.name, d.start_time, d.end_time, d.start_time, d.end_time, d.start_time))

			if existing:
				frappe.throw(_("Row #{0}: Timings conflicts with row {1}").format(d.idx, comma_and(existing)), OverlapError)

@frappe.whitelist()
def get_default_holiday_list():
	return frappe.db.get_value("Company", frappe.defaults.get_user_default("company"), "default_holiday_list")

def check_if_within_operating_hours(workstation, from_datetime, to_datetime):
	if not is_within_operating_hours(workstation, from_datetime, to_datetime):
		frappe.throw(_("Time Log timings outside workstation operating hours"), NotInWorkingHoursError)

	if not cint(frappe.db.get_value("Manufacturing Settings", "None", "allow_production_on_holidays")):
		check_workstation_for_holiday(workstation, from_datetime, to_datetime)

def is_within_operating_hours(workstation, from_datetime, to_datetime):
	if not cint(frappe.db.get_value("Manufacturing Settings", None, "dont_allow_overtime")):
		return True

	start_time = datetime.datetime.strptime(from_datetime,'%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')
	end_time = datetime.datetime.strptime(to_datetime,'%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')

	for d in frappe.db.sql("""select start_time, end_time from `tabWorkstation Operation Hours`
		where parent = %s and ifnull(enabled, 0) = 1""", workstation, as_dict=1):
			if d.end_time >= start_time >= d.start_time and d.end_time >= end_time >= d.start_time:
				return True

def check_workstation_for_holiday(workstation, from_datetime, to_datetime):
	holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")
	if holiday_list:
		applicable_holidays = []
		for d in frappe.db.sql("""select holiday_date from `tabHoliday` where parent = %s
			and holiday_date between %s and %s """, (holiday_list, getdate(from_datetime), getdate(to_datetime))):
				applicable_holidays.append(formatdate(d[0]))

		if applicable_holidays:
			frappe.throw(_("Workstation is closed on the following dates as per Holiday List: {0}")
				.format(holiday_list) + "\n" + "\n".join(applicable_holidays), WorkstationHolidayError)
