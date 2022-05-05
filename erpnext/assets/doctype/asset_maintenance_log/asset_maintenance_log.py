# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date


class AssetMaintenanceLog(Document):
	def validate(self):
		self.check_if_maintenance_is_overdue()
		self.validate_completion_date()

	def on_submit(self):
		self.validate_maintenance_status()
		self.update_maintenance_task()

	def check_if_maintenance_is_overdue(self):
		if getdate(self.due_date) < getdate() and self.maintenance_status not in [
			"Completed",
			"Cancelled",
		]:
			self.maintenance_status = "Overdue"

	def validate_completion_date(self):
		if self.maintenance_status == "Completed" and not self.completion_date:
			frappe.throw(_("Please select Completion Date for Completed Asset Maintenance Log"))

		if self.maintenance_status != "Completed" and self.completion_date:
			frappe.throw(_("Please select Maintenance Status as Completed or remove Completion Date"))

	def validate_maintenance_status(self):
		if self.maintenance_status not in ["Completed", "Cancelled"]:
			frappe.throw(_("Maintenance Status has to be Cancelled or Completed to Submit this doc"))

	def update_maintenance_task(self):
		maintenance_task = frappe.get_doc("Asset Maintenance Task", self.task)

		if self.maintenance_status == "Completed":
			if maintenance_task.last_completion_date != self.completion_date:
				self.set_next_due_date(maintenance_task)

		elif self.maintenance_status == "Cancelled":
			maintenance_task.maintenance_status = "Cancelled"
			maintenance_task.save()

	def set_next_due_date(self, maintenance_task):
		next_due_date = calculate_next_due_date(
			periodicity=self.periodicity, last_completion_date=self.completion_date
		)

		maintenance_task.last_completion_date = self.completion_date
		maintenance_task.next_due_date = next_due_date
		maintenance_task.maintenance_status = "Planned"
		maintenance_task.save()
