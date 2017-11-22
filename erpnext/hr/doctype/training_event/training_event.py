# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.hr.doctype.employee.employee import get_employee_emails

class TrainingEvent(Document):
	def validate(self):
		self.employee_emails = ', '.join(get_employee_emails([d.employee
			for d in self.employees]))

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Training Event", filters)

	data = frappe.db.sql("""
		select
			name, event_name, event_status, start_time, end_time
		from
			`tabTraining Event`
		where (ifnull(start_time, '0000-00-00')!= '0000-00-00') \
			and (start_time between %(start)s and %(end)s)
			and docstatus < 2
			{conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})
	return data
