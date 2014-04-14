# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, comma_and


class OverlapError(frappe.ValidationError): pass

from frappe.model.document import Document

class TimeLog(Document):

	def validate(self):
		self.set_status()
		self.validate_overlap()
		self.calculate_total_hours()

	def calculate_total_hours(self):
		from frappe.utils import time_diff_in_hours
		self.hours = time_diff_in_hours(self.to_time, self.from_time)

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

	def before_cancel(self):
		self.set_status()

	def before_update_after_submit(self):
		self.set_status()

@frappe.whitelist()
def get_events(start, end):
	from frappe.widgets.reportview import build_match_conditions
	if not frappe.has_permission("Time Log"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	match = build_match_conditions("Time Log")
	data = frappe.db.sql("""select name, from_time, to_time,
		activity_type, task, project from `tabTime Log`
		where from_time between '%(start)s' and '%(end)s' or to_time between '%(start)s' and '%(end)s'
		%(match)s""" % {
			"start": start,
			"end": end,
			"match": match and (" and " + match) or ""
		}, as_dict=True, update={"allDay": 0})

	for d in data:
		d.title = d.name + ": " + (d.activity_type or "[Activity Type not set]")
		if d.task:
			d.title += " for Task: " + d.task
		if d.project:
			d.title += " for Project: " + d.project

	return data
