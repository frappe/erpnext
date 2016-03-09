# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint, get_datetime
from frappe import throw, _
from frappe.model.document import Document

class OverlapError(frappe.ValidationError): pass

class HolidayList(Document):
	def validate(self):
		self.update_default_holiday_list()
		self.validate_time_period()
		self.validate_days()

	def get_weekly_off_dates(self):
		self.validate_values()
		date_list = self.get_weekly_off_date_list(self.from_date, self.to_date)
		last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0,])
		for i, d in enumerate(date_list):
			ch = self.append('holidays', {})
			ch.description = self.weekly_off
			ch.holiday_date = d
			ch.idx = last_idx + i + 1

	def validate_values(self):
		if not self.weekly_off:
			throw(_("Please select weekly off day"))


	def validate_days(self):
		for day in self.get("holidays"):
			if not self.from_date <= day.holiday_date <= self.to_date:
				frappe.throw("Date not between From Date and To Date")
	
	def validate_time_period(self):
		if self.from_date > self.to_date:
			throw(_("To Date cannot be before From Date"))

		existing = frappe.db.sql("""select holiday_list_name, from_date, to_date from `tabHoliday List`
			where
			(
				(%(from_date)s > from_date and %(from_date)s < to_date) or 
				(%(to_date)s > from_date and %(to_date)s < to_date) or 
				(%(from_date)s <= from_date and %(to_date)s >= to_date))
			and name!=%(name)s""",
			{
				"from_date": self.from_date,
				"to_date": self.to_date,
				"name": self.holiday_list_name
			}, as_dict=True)

		if existing:
			frappe.throw(_("This Time Period conflicts with {0} ({1} to {2})").format(existing[0].holiday_list_name,
				 existing[0].from_date, existing[0].to_date, OverlapError))


	def get_weekly_off_date_list(self, start_date, end_date):
		from frappe.utils import getdate
		start_date, end_date = getdate(start_date), getdate(end_date)

		from dateutil import relativedelta
		from datetime import timedelta
		import calendar

		date_list = []
		existing_date_list = []
		weekday = getattr(calendar, (self.weekly_off).upper())
		reference_date = start_date + relativedelta.relativedelta(weekday=weekday)
		
		for holiday in self.get("holidays"):
			existing_date_list.append(get_datetime(holiday.holiday_date).date())

		while reference_date <= end_date:
			if reference_date not in existing_date_list:
				date_list.append(reference_date)
			reference_date += timedelta(days=7)

		return date_list

	def clear_table(self):
		self.set('holidays', [])

	def update_default_holiday_list(self):
		frappe.db.sql("""update `tabHoliday List` set is_default = 0
			where is_default = 1""")

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""

	data = frappe.db.sql("""select hl.name, hld.holiday_date, hld.description
		from `tabHoliday List` hl, tabHoliday hld
		where hld.parent = hl.name
		and ifnull(hld.holiday_date, "0000-00-00") != "0000-00-00"
		""", as_dict=True, update={"allDay": 1})
	return data
