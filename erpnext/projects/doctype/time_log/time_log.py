# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import cstr, comma_and, flt

class OverlapError(frappe.ValidationError): pass
class OverProductionError(frappe.ValidationError): pass
class NotSubmittedError(frappe.ValidationError): pass

from frappe.model.document import Document

class TimeLog(Document):
	def validate(self):
		self.set_status()
		self.validate_overlap()
		self.validate_timings()
		self.calculate_total_hours()
		self.validate_time_log_for()
		self.check_workstation_timings()
		self.validate_production_order()

	def on_submit(self):
		self.update_production_order()

	def on_cancel(self):
		self.update_production_order()

	def before_update_after_submit(self):
		self.set_status()

	def before_cancel(self):
		self.set_status()

	def set_status(self):
		self.status = {
			0: "Draft",
			1: "Submitted",
			2: "Cancelled"
		}[self.docstatus or 0]

		if self.time_log_batch:
			self.status="Batched for Billing"

		if self.sales_invoice:
			self.status="Billed"

	def validate_overlap(self):
		"""Checks if 'Time Log' entries overlap each other. """
		existing = frappe.db.sql_list("""select name from `tabTime Log` where owner=%s and
			(
				(from_time between %s and %s) or
				(to_time between %s and %s) or
				(%s between from_time and to_time))
			and name!=%s
			and ifnull(task, "")=%s
			and docstatus < 2""",
			(self.owner, self.from_time, self.to_time, self.from_time,
				self.to_time, self.from_time, self.name or "No Name",
				cstr(self.task)))

		if existing:
			frappe.throw(_("This Time Log conflicts with {0}").format(comma_and(existing)), OverlapError)

	def validate_timings(self):
		if self.to_time < self.from_time:
			frappe.throw(_("From Time cannot be greater than To Time"))

	def calculate_total_hours(self):
		from frappe.utils import time_diff_in_seconds
		self.hours = flt(time_diff_in_seconds(self.to_time, self.from_time)) / 3600

	def validate_time_log_for(self):
		if self.time_log_for == "Project":
			for fld in ["production_order", "operation", "workstation", "completed_qty"]:
				self.set(fld, None)

	def check_workstation_timings(self):
		"""Checks if **Time Log** is between operating hours of the **Workstation**."""
		if self.workstation:
			from erpnext.manufacturing.doctype.workstation.workstation import check_if_within_operating_hours
			check_if_within_operating_hours(self.workstation, self.from_time, self.to_time)

	def validate_production_order(self):
		"""Throws 'NotSubmittedError' if **production order** is not submitted. """
		if self.production_order:
			if frappe.db.get_value("Production Order", self.production_order, "docstatus") != 1 :
				frappe.throw(_("You can make a time log only against a submitted production order"), NotSubmittedError)

	def update_production_order(self):
		"""Updates `start_date`, `end_date`, `status` for operation in Production Order."""

		if self.time_log_for=="Manufacturing" and self.operation:
			operation = self.operation.split('. ',1)

			dates = self.get_operation_start_end_time()
			tl = self.get_all_time_logs()


			frappe.db.sql("""update `tabProduction Order Operation`
				set actual_start_time = %s, actual_end_time = %s, completed_qty = %s, actual_operation_time = %s
				where parent=%s and idx=%s and operation = %s""",
				(dates.start_date, dates.end_date, tl.completed_qty,
					tl.hours, self.production_order, operation[0], operation[1]))

			pro_order = frappe.get_doc("Production Order", self.production_order)
			pro_order.ignore_validate_update_after_submit = True
			pro_order.update_operation_status()
			pro_order.calculate_operating_cost()
			pro_order.set_actual_dates()
			pro_order.save()

	def get_operation_start_end_time(self):
		"""Returns Min From and Max To Dates of Time Logs against a specific Operation. """
		return frappe.db.sql("""select min(from_time) as start_date, max(to_time) as end_date from `tabTime Log`
				where production_order = %s and operation = %s and docstatus=1""",
				(self.production_order, self.operation), as_dict=1)[0]

	def get_all_time_logs(self):
		"""Returns 'Actual Operating Time'. """
		return frappe.db.sql("""select
			sum(hours*60) as hours, sum(ifnull(completed_qty, 0)) as completed_qty
			from `tabTime Log`
			where production_order = %s and operation = %s and docstatus=1""",
			(self.production_order, self.operation), as_dict=1)[0]

@frappe.whitelist()
def get_workstation(production_order, operation):
	"""Returns workstation name from Production Order against an associated Operation.

	:param production_order string
	:param operation string
	"""
	if operation:
		idx, operation = operation.split('. ',1)

		workstation = frappe.db.sql("""select workstation from `tabProduction Order Operation` where idx=%s and
			parent=%s and operation = %s""", (idx, production_order, operation))
		return workstation[0][0] if workstation else ""

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters like workstation, project etc.
	"""
	from frappe.desk.reportview import build_match_conditions
	if not frappe.has_permission("Time Log"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	conditions = build_match_conditions("Time Log")
	conditions = conditions and (" and " + conditions) or ""
	if filters:
		filters = json.loads(filters)
		for key in filters:
			if filters[key]:
				conditions += " and " + key + ' = "' + filters[key].replace('"', '\"') + '"'

	data = frappe.db.sql("""select name, from_time, to_time,
		activity_type, task, project, production_order, workstation from `tabTime Log`
		where ( from_time between %(start)s and %(end)s or to_time between %(start)s and %(end)s )
		{conditions}""".format(conditions=conditions), {
			"start": start,
			"end": end
			}, as_dict=True, update={"allDay": 0})

	for d in data:
		d.title = d.name + ": " + (d.activity_type or d.production_order or "")
		if d.task:
			d.title += " for Task: " + d.task
		if d.project:
			d.title += " for Project: " + d.project

	return data
