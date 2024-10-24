# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, flt, get_datetime, time_diff_in_hours


class TimesheetDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		activity_type: DF.Link | None
		base_billing_amount: DF.Currency
		base_billing_rate: DF.Currency
		base_costing_amount: DF.Currency
		base_costing_rate: DF.Currency
		billing_amount: DF.Currency
		billing_hours: DF.Float
		billing_rate: DF.Currency
		completed: DF.Check
		costing_amount: DF.Currency
		costing_rate: DF.Currency
		description: DF.SmallText | None
		expected_hours: DF.Float
		from_time: DF.Datetime | None
		hours: DF.Float
		is_billable: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		project: DF.Link | None
		project_name: DF.Data | None
		sales_invoice: DF.Link | None
		task: DF.Link | None
		to_time: DF.Datetime | None
	# end: auto-generated types

	def set_to_time(self):
		"""Set to_time based on from_time and hours."""
		if not (self.from_time and self.hours):
			return

		self.to_time = get_datetime(add_to_date(self.from_time, hours=self.hours, as_datetime=True))

	def set_project(self):
		"""Set project based on task."""
		if self.task and not self.project:
			self.project = frappe.db.get_value("Task", self.task, "project")

	def calculate_hours(self):
		"""Calculate hours based on from_time and to_time."""
		if self.to_time and self.from_time:
			self.hours = time_diff_in_hours(self.to_time, self.from_time)

	def update_billing_hours(self):
		"""Update billing hours based on hours."""
		if not self.is_billable:
			self.billing_hours = 0
			return

		if flt(self.billing_hours) == 0.0:
			self.billing_hours = self.hours

	def update_cost(self, employee: str):
		"""Update costing and billing rates based on activity type."""
		from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost

		if not self.is_billable and not self.activity_type:
			return

		rate = get_activity_cost(employee, self.activity_type)
		if not rate:
			return

		self.billing_rate = (
			flt(rate.get("billing_rate")) if flt(self.billing_rate) == 0 else self.billing_rate
		)
		self.costing_rate = (
			flt(rate.get("costing_rate")) if flt(self.costing_rate) == 0 else self.costing_rate
		)

		self.billing_amount = self.billing_rate * (self.billing_hours or 0)
		self.costing_amount = self.costing_rate * (self.billing_hours or self.hours or 0)

	def validate_dates(self):
		"""Validate that to_time is not before from_time."""
		if self.from_time and self.to_time and time_diff_in_hours(self.to_time, self.from_time) < 0:
			frappe.throw(_("To Time cannot be before from date"))

	def validate_parent_project(self, parent_project: str):
		"""Validate that project is same as Timesheet's parent project."""
		if parent_project and parent_project != self.project:
			frappe.throw(
				_("Row {0}: Project must be same as the one set in the Timesheet: {1}.").format(
					self.idx, parent_project
				)
			)

	def validate_task_project(self):
		"""Validate that the the task belongs to the project specified in the timesheet detail."""
		if self.task and self.project:
			task_project = frappe.db.get_value("Task", self.task, "project")
			if task_project and task_project != self.project:
				frappe.throw(
					_("Row {0}: Task {1} does not belong to Project {2}").format(
						self.idx, frappe.bold(self.task), frappe.bold(self.project)
					)
				)

	def validate_billing_hours(self):
		"""Warn if billing hours are more than actual hours."""
		if flt(self.billing_hours) > flt(self.hours):
			frappe.msgprint(
				_("Warning - Row {0}: Billing Hours are more than Actual Hours").format(self.idx),
				indicator="orange",
				alert=True,
			)
