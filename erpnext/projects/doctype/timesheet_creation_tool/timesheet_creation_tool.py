# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class TimesheetCreationTool(Document):
	def onload(self):
		self.get("__onload").maintain_bill_work_hours_same = frappe.db.get_single_value('HR Settings', 'maintain_bill_work_hours_same')
		self.total_hours = 0.0
		self.total_billable_hours = 0.0
		self.total_billed_hours = 0.0
		self.total_billable_amount = 0.0
		self.total_costing_amount = 0.0
		self.total_billed_amount = 0.0

	def create_timesheet(self):
		docs = []
		if not self.company:
			frappe.throw(_("Please select the Company."))
		elif not self.employees:
			frappe.throw(_("Please add atleast one employee."))
		elif not self.time_logs:
			frappe.throw(_("Mandatory field: Time Logs"))
		for emp in self.employees:
			if not emp:
				return None

			time_log = get_timelogs_dict(self.time_logs)
			timesheet = frappe.get_doc({
							"doctype": "Timesheet",
							"company": self.company,
							"employee": emp.employee,
							"time_logs": time_log
						})
			doc = timesheet.insert();
			docs.append(doc)
		return docs

	def submit_timesheet(self):
		docs = self.create_timesheet()
		for doc in docs:
			doc.submit()

def get_timelogs_dict(time_logs):
	logs = []
	for row in time_logs:
		items = frappe._dict({
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
		logs.append(items)

	return logs
