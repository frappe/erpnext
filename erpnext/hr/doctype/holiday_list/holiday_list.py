# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.utils import cint, getdate, formatdate
from frappe import throw, _
from frappe.model.document import Document

class OverlapError(frappe.ValidationError): pass

class HolidayList(Document):
	def validate(self):
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
		if self.from_date > self.to_date:
			throw(_("To Date cannot be before From Date"))

		for day in self.get("holidays"):
			if not (getdate(self.from_date) <= getdate(day.holiday_date) <= getdate(self.to_date)):
				frappe.throw(_("The holiday on {0} is not between From Date and To Date").format(formatdate(day.holiday_date)))

	def get_weekly_off_date_list(self, start_date, end_date):
		start_date, end_date = getdate(start_date), getdate(end_date)

		from dateutil import relativedelta
		from datetime import timedelta
		import calendar

		date_list = []
		existing_date_list = []
		weekday = getattr(calendar, (self.weekly_off).upper())
		reference_date = start_date + relativedelta.relativedelta(weekday=weekday)

		existing_date_list = [getdate(holiday.holiday_date) for holiday in self.get("holidays")]

		while reference_date <= end_date:
			if reference_date not in existing_date_list:
				date_list.append(reference_date)
			reference_date += timedelta(days=7)

		return date_list

	def clear_table(self):
		self.set('holidays', [])

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	condition = ''
	values = {
		"start_date": getdate(start),
		"end_date": getdate(end)
	}

	if filters:
		if isinstance(filters, basestring):
			filters = json.loads(filters)

		if filters.get('holiday_list'):
			condition = 'and hlist.name=%(holiday_list)s'
			values['holiday_list'] = filters['holiday_list']

	data = frappe.db.sql("""select hlist.name, h.holiday_date, h.description
		from `tabHoliday List` hlist, tabHoliday h
		where h.parent = hlist.name
		and h.holiday_date is not null
		and h.holiday_date >= %(start_date)s
		and h.holiday_date <= %(end_date)s
		{condition}""".format(condition=condition),
		values, as_dict=True, update={"allDay": 1})

	return data
