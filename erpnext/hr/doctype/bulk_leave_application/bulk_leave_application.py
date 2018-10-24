# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, add_days, formatdate
from frappe.model.document import Document

class BulkLeaveApplication(Document):
	def validate(self):
		self.reset_helper_fields()
		self.validate_dates()
		self.calculate_total_days()

	def reset_helper_fields(self):
		for field in ("leave_type", "leave_date", "half_day_date"):
			self.set(field, None)

	def validate_dates(self):
		date_ranges = []
		for d in self.date_ranges:
			row_dates = []
			for r in range(date_diff(d.to_date, d.from_date) + 1):
				row_dates.append(add_days(d.from_date, r))
			date_ranges.append(row_dates)

		for i, dates in enumerate(date_ranges):
			for dt in dates:
				for j, other_row_dates in enumerate(date_ranges):
					if i != j and dt in other_row_dates:
						frappe.throw(_("Duplicate entry for date {0} in rows {1} and {2}")
							.format(formatdate(dt), i+1, j+1))

	def calculate_total_days(self):
		self.total_leaves = 0.0
		for d in self.date_ranges:
			days = date_diff(d.to_date, d.from_date) + 1
			if d.half_day:
				days -= 0.5
			d.days = days
			self.total_leaves += d.days

	def on_submit(self):
		self.create_leave_applications()

	def create_leave_applications(self):
		for d in self.date_ranges:
			if d.leave_type and d.from_date and d.to_date:
				leave = frappe.new_doc("Leave Application")
				leave.employee = self.employee
				leave.leave_type = d.leave_type
				leave.from_date = d.from_date
				leave.to_date = d.to_date
				leave.half_day = d.half_day
				leave.half_day_date = d.half_day_date
				leave.status = "Approved"
				leave.bulk_leave_application = self.name
				leave.save()
				leave.submit()

	def on_cancel(self):
		self.cancel_leave_applications()

	def cancel_leave_applications(self):
		leave_apps = frappe.get_all("Leave Application",
			filters={"bulk_leave_application": self.name, "docstatus": 1})
		for app in leave_apps:
			app = frappe.get_doc("Leave Application", app.name)
			app.cancel()