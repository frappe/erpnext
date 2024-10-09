# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from datetime import date

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import formatdate, getdate, today


class OverlapError(frappe.ValidationError):
	pass


class HolidayList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.holiday.holiday import Holiday

		color: DF.Color | None
		country: DF.Autocomplete | None
		from_date: DF.Date
		holiday_list_name: DF.Data
		holidays: DF.Table[Holiday]
		subdivision: DF.Autocomplete | None
		to_date: DF.Date
		total_holidays: DF.Int
		weekly_off: DF.Literal[
			"", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
		]
	# end: auto-generated types

	def validate(self):
		self.validate_days()
		self.total_holidays = len(self.holidays)
		self.validate_duplicate_date()
		self.sort_holidays()

	@frappe.whitelist()
	def get_weekly_off_dates(self):
		if not self.weekly_off:
			throw(_("Please select weekly off day"))

		existing_holidays = self.get_holidays()

		for d in self.get_weekly_off_date_list(self.from_date, self.to_date):
			if d in existing_holidays:
				continue

			self.append("holidays", {"description": _(self.weekly_off), "holiday_date": d, "weekly_off": 1})

	@frappe.whitelist()
	def get_supported_countries(self):
		from holidays.utils import list_supported_countries

		subdivisions_by_country = list_supported_countries()
		countries = [
			{"value": country, "label": local_country_name(country)}
			for country in subdivisions_by_country.keys()
		]
		return {
			"countries": countries,
			"subdivisions_by_country": subdivisions_by_country,
		}

	@frappe.whitelist()
	def get_local_holidays(self):
		from holidays import country_holidays

		if not self.country:
			throw(_("Please select a country"))

		existing_holidays = self.get_holidays()
		from_date = getdate(self.from_date)
		to_date = getdate(self.to_date)

		for holiday_date, holiday_name in country_holidays(
			self.country,
			subdiv=self.subdivision,
			years=list(range(from_date.year, to_date.year + 1)),
			language=frappe.local.lang,
		).items():
			if holiday_date in existing_holidays:
				continue

			if holiday_date < from_date or holiday_date > to_date:
				continue

			self.append(
				"holidays", {"description": holiday_name, "holiday_date": holiday_date, "weekly_off": 0}
			)

	def sort_holidays(self):
		self.holidays.sort(key=lambda x: getdate(x.holiday_date))
		for i in range(len(self.holidays)):
			self.holidays[i].idx = i + 1

	def get_holidays(self) -> list[date]:
		return [getdate(holiday.holiday_date) for holiday in self.holidays]

	def validate_days(self):
		if getdate(self.from_date) > getdate(self.to_date):
			throw(_("To Date cannot be before From Date"))

		for day in self.get("holidays"):
			if not (getdate(self.from_date) <= getdate(day.holiday_date) <= getdate(self.to_date)):
				frappe.throw(
					_("The holiday on {0} is not between From Date and To Date").format(
						formatdate(day.holiday_date)
					)
				)

	def get_weekly_off_date_list(self, start_date, end_date):
		start_date, end_date = getdate(start_date), getdate(end_date)

		import calendar
		from datetime import timedelta

		from dateutil import relativedelta

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

	@frappe.whitelist()
	def clear_table(self):
		self.set("holidays", [])

	def validate_duplicate_date(self):
		unique_dates = []
		for row in self.holidays:
			if row.holiday_date in unique_dates:
				frappe.throw(
					_("Holiday Date {0} added multiple times").format(
						frappe.bold(formatdate(row.holiday_date))
					)
				)

			unique_dates.append(row.holiday_date)


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	if filters:
		filters = json.loads(filters)
	else:
		filters = []

	if start:
		filters.append(["Holiday", "holiday_date", ">", getdate(start)])
	if end:
		filters.append(["Holiday", "holiday_date", "<", getdate(end)])

	return frappe.get_list(
		"Holiday List",
		fields=[
			"name",
			"`tabHoliday`.holiday_date",
			"`tabHoliday`.description",
			"`tabHoliday List`.color",
		],
		filters=filters,
		update={"allDay": 1},
	)


def is_holiday(holiday_list, date=None):
	"""Returns true if the given date is a holiday in the given holiday list"""
	if date is None:
		date = today()
	if holiday_list:
		return bool(frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date}, cache=True))
	else:
		return False


def local_country_name(country_code: str) -> str:
	"""Return the localized country name for the given country code."""
	from babel import Locale

	return Locale.parse(frappe.local.lang, sep="-").territories.get(country_code, country_code)
