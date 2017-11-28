# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.form import assign_to
from frappe import throw, _
from frappe.utils import add_days, add_months, add_years, getdate, nowdate

class AssetMaintenance(Document):
	def validate(self):
		for task in self.get('asset_maintenance_tasks'):
			if task.end_date and (getdate(task.start_date) >= getdate(task.end_date)):
				throw(_("Start date should be less than end date for task {0}").format(task.maintenance_task))
			if getdate(task.next_due_date) < getdate(nowdate()):
				task.maintenance_status = "Overdue"
			if not self.get("__islocal"):
				if not task.assign_to:
					task.assign_to = self.maintenance_manager
				if task.assign_to:
					self.assign_tasks(task)

	def assign_tasks(self, task):
		team_member = frappe.get_doc('User', task.assign_to).email
		args = {
			'doctype' : self.doctype,
			'assign_to' : team_member,
			'name' : self.name,
			'description' : task.maintenance_task,
			'date' : task.next_due_date
		}
		if not frappe.db.sql("""select owner from `tabToDo`
			where reference_type=%(doctype)s and reference_name=%(name)s and status="Open"
			and owner=%(assign_to)s""", args):
			assign_to.add(args)


@frappe.whitelist()
def calculate_next_due_date(periodicity, start_date = None, end_date = None, last_completion_date = None, next_due_date = None):
	if not start_date and not last_completion_date:
		start_date = frappe.utils.now()

	if last_completion_date and (last_completion_date > start_date or not start_date):
		start_date = last_completion_date

	if periodicity == 'Daily':
		next_due_date = add_days(start_date, 1)
	if periodicity == 'Weekly':
		next_due_date = add_days(start_date, 7)
	if periodicity == 'Monthly':
		next_due_date = add_months(start_date, 1)
	if periodicity == 'Yearly':
		next_due_date = add_years(start_date, 1)
	if periodicity == '2 Yearly':
		next_due_date = add_years(start_date, 2)
	if periodicity == 'Quarterly':
		next_due_date = add_months(start_date, 3)
	if end_date and (start_date >= end_date or last_completion_date >= end_date or next_due_date):
		next_due_date = ""
	return next_due_date

@frappe.whitelist()
def get_maintenance_log(asset_name):
    return frappe.db.sql("""
        select maintenance_status, count(asset_name) as count, asset_name
        from `tabAsset Maintenance Log`
        where asset_name=%s group by maintenance_status""",
        (asset_name), as_dict=1)
		