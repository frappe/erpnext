# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate
from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date

class AssetMaintenanceLog(Document):
	def validate(self):
		if getdate(self.due_date) < getdate(nowdate()):
			self.maintenance_status = "Overdue"

		if self.maintenance_status == "Completed" and not self.completion_date:
			frappe.throw(_("Please select Completion Date for Completed Asset Maintenance Log"))

		if self.maintenance_status != "Completed" and self.completion_date:
			frappe.throw(_("Please select Maintenance Status as Completed or remove Completion Date"))

	def on_submit(self):
		if self.maintenance_status not in ['Completed', 'Cancelled']:
			frappe.throw(_("Maintenance Status has to be Cancelled or Completed to Submit"))
		self.update_maintenance_task()

	def update_maintenance_task(self):
		asset_maintenance_doc = frappe.get_doc('Asset Maintenance Task', self.task)
		if self.maintenance_status == "Completed":
			if asset_maintenance_doc.last_completion_date != self.completion_date:
				next_due_date = calculate_next_due_date(periodicity = self.periodicity, last_completion_date = self.completion_date)
				asset_maintenance_doc.last_completion_date = self.completion_date
				asset_maintenance_doc.next_due_date = next_due_date
				asset_maintenance_doc.maintenance_status = "Planned"
				asset_maintenance_doc.save()
		if self.maintenance_status == "Cancelled":
			asset_maintenance_doc.maintenance_status = "Cancelled"
			asset_maintenance_doc.save()
		asset_maintenance_doc = frappe.get_doc('Asset Maintenance', self.asset_maintenance)
		asset_maintenance_doc.save()

@frappe.whitelist()
def get_maintenance_tasks(doctype, txt, searchfield, start, page_len, filters):
	asset_maintenance_tasks = frappe.db.get_values('Asset Maintenance Task', {'parent':filters.get("asset_maintenance")}, 'maintenance_task')
	return asset_maintenance_tasks

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Asset Maintenance Log", filters)
	data = frappe.db.sql("""select name, due_date, due_date,
		task, maintenance_status, asset_name from `tabAsset Maintenance Log`
		where ((ifnull(due_date, '0000-00-00')!= '0000-00-00') \
				and (due_date <= %(end)s) \
			or ((ifnull(due_date, '0000-00-00')!= '0000-00-00') \
				and due_date >= %(start)s))
		{conditions}""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})

	return data