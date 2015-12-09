# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint
from frappe.model.naming import make_autoname
from frappe import throw, _

from frappe.model.document import Document

class HolidayList(Document):
	def validate(self):
		self.update_default_holiday_list()

	def get_weekly_off_dates(self):
		self.validate_values()
		self.validate_days()
		yr_start_date, yr_end_date = get_fy_start_end_dates(self.fiscal_year)
		date_list = self.get_weekly_off_date_list(yr_start_date, yr_end_date)
		last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0,])
		for i, d in enumerate(date_list):
			ch = self.append('holidays', {})
			ch.description = self.weekly_off
			ch.holiday_date = d
			ch.idx = last_idx + i + 1

	def validate_values(self):
		if not self.fiscal_year:
			throw(_("Please select Fiscal Year"))
		if not self.weekly_off:
			throw(_("Please select weekly off day"))

	def validate_days(self):
		for day in self.get("holidays"):
			if (self.weekly_off or "").upper() == (day.description or "").upper():
				frappe.throw("Records already exist for mentioned weekly off")

	def get_weekly_off_date_list(self, year_start_date, year_end_date):
		from frappe.utils import getdate
		year_start_date, year_end_date = getdate(year_start_date), getdate(year_end_date)

		from dateutil import relativedelta
		from datetime import timedelta
		import calendar

		date_list = []
		weekday = getattr(calendar, (self.weekly_off).upper())
		reference_date = year_start_date + relativedelta.relativedelta(weekday=weekday)

		while reference_date <= year_end_date:
			date_list.append(reference_date)
			reference_date += timedelta(days=7)

		return date_list

	def clear_table(self):
		self.set('holidays', [])

	def update_default_holiday_list(self):
		frappe.db.sql("""update `tabHoliday List` set is_default = 0
			where is_default = 1 and fiscal_year = %s""", (self.fiscal_year,))

@frappe.whitelist()
def get_events(start, end, filters=None):
	import json
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Holiday List", filters)

	fiscal_year = None
	if filters:
		fiscal_year = json.loads(filters).get("fiscal_year")

	if not fiscal_year:
		fiscal_year = frappe.db.get_value("Global Defaults", None, "current_fiscal_year")

	yr_start_date, yr_end_date = get_fy_start_end_dates(fiscal_year)

	data = frappe.db.sql("""select hl.name, hld.holiday_date, hld.description
		from `tabHoliday List` hl, tabHoliday hld
		where hld.parent = hl.name
		and (ifnull(hld.holiday_date, "0000-00-00") != "0000-00-00"
			and hld.holiday_date between %(start)s and %(end)s)
		{conditions}""".format(conditions=conditions), {
			"start": yr_start_date,
			"end": yr_end_date
		}, as_dict=True, update={"allDay": 1})

	return data

def get_fy_start_end_dates(fiscal_year):
	return frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"])
