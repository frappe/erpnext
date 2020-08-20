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
		if getdate(self.due_date) < getdate(nowdate()) and self.maintenance_status not in ["Completed", "Cancelled"]:
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
@frappe.validate_and_sanitize_search_inputs
def get_maintenance_tasks(doctype, txt, searchfield, start, page_len, filters):
	asset_maintenance_tasks = frappe.db.get_values('Asset Maintenance Task', {'parent':filters.get("asset_maintenance")}, 'maintenance_task')
	return asset_maintenance_tasks
