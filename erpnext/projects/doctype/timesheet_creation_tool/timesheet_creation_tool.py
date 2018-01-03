# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TimesheetCreationTool(Document):
	def create_timesheet(self):
		for emp in self.employees:
			def get_timelogs_dict(self, row=None):
				for row in self.time_logs:
					return frappe._dict({
						"activity_type": row.activity_type,
						"from_time": row.from_time,
						"hours": row.hours,
						"project": row.project,
						"to_time": row.to_time,
						"task": row.task,
						"billable": row.billable,
						"billing_hours": row.billing_hours,
						"billing_rate": row.billing_rate,
						"costing_rate": row.costing_rate
					})

				if not emp:
					return None

				time_log = get_timelogs_dict()
				timesheet = frappe.get_doc({
								"doctype": "Timesheet",
								"company": self.company,
								"employee": emp.employee,
								"time_logs": [time_log]
							})
				doc = timesheet.insert()
				return doc
					
