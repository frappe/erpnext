# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils import getdate, nowdate, today

from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date


class AssetMaintenanceLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actions_performed: DF.TextEditor | None
		amended_from: DF.Link | None
		asset_maintenance: DF.Link | None
		asset_name: DF.ReadOnly | None
		assign_to_name: DF.ReadOnly | None
		certificate_attachement: DF.Attach | None
		completion_date: DF.Date | None
		description: DF.ReadOnly | None
		due_date: DF.Date | None
		has_certificate: DF.Check
		item_code: DF.ReadOnly | None
		item_name: DF.ReadOnly | None
		maintenance_status: DF.Literal["Planned", "Completed", "Cancelled", "Overdue"]
		maintenance_type: DF.ReadOnly | None
		naming_series: DF.Literal["ACC-AML-.YYYY.-"]
		periodicity: DF.Data | None
		task: DF.Link | None
		task_assignee_email: DF.Data | None
		task_name: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_task()
		if getdate(self.due_date) < getdate(nowdate()) and self.maintenance_status not in [
			"Completed",
			"Cancelled",
		]:
			self.maintenance_status = "Overdue"

		if self.maintenance_status == "Completed" and not self.completion_date:
			frappe.throw(_("Please select Completion Date for Completed Asset Maintenance Log"))

		if self.maintenance_status != "Completed" and self.completion_date:
			frappe.throw(_("Please select Maintenance Status as Completed or remove Completion Date"))

	def validate_task(self):
		if (
			self.task
			and frappe.db.get_value("Asset Maintenance Task", self.task, "parent") != self.asset_maintenance
		):
			frappe.throw(
				_("Task {0} does not belong to Asset Maintenance {1}").format(
					self.task, self.asset_maintenance
				)
			)

	def on_submit(self):
		if self.maintenance_status not in ["Completed", "Cancelled"]:
			frappe.throw(_("Maintenance Status has to be Cancelled or Completed to Submit"))
		self.update_maintenance_task()

	def on_cancel(self):
		if self.maintenance_status == "Completed":
			self.revert_maintenance_task()

	def revert_maintenance_task(self):
		task = frappe.get_doc("Asset Maintenance Task", self.task)
		if not task.last_completion_date or getdate(task.last_completion_date) != getdate(
			self.completion_date
		):
			return

		task.last_completion_date = frappe.db.get_value(
			"Asset Maintenance Log",
			{"task": self.task, "docstatus": 1, "maintenance_status": "Completed", "name": ("!=", self.name)},
			"completion_date",
			order_by="completion_date desc",
		)
		task.next_due_date = self.due_date
		task.save()
		frappe.get_doc("Asset Maintenance", self.asset_maintenance).save()

	def update_maintenance_task(self):
		asset_maintenance_doc = frappe.get_doc("Asset Maintenance Task", self.task)
		if self.maintenance_status == "Completed":
			if asset_maintenance_doc.last_completion_date != self.completion_date:
				next_due_date = calculate_next_due_date(
					periodicity=self.periodicity, last_completion_date=self.completion_date
				)
				asset_maintenance_doc.last_completion_date = self.completion_date
				asset_maintenance_doc.next_due_date = next_due_date
				asset_maintenance_doc.maintenance_status = "Planned"
				asset_maintenance_doc.save()
		if self.maintenance_status == "Cancelled":
			asset_maintenance_doc.maintenance_status = "Cancelled"
			asset_maintenance_doc.save()
		asset_maintenance_doc = frappe.get_doc("Asset Maintenance", self.asset_maintenance)
		asset_maintenance_doc.save()


def update_asset_maintenance_log_status():
	AssetMaintenanceLog = DocType("Asset Maintenance Log")
	(
		frappe.qb.update(AssetMaintenanceLog)
		.set(AssetMaintenanceLog.maintenance_status, "Overdue")
		.where(
			(AssetMaintenanceLog.maintenance_status == "Planned") & (AssetMaintenanceLog.due_date < today())
		)
	).run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_maintenance_tasks(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	asset_maintenance = filters.get("asset_maintenance")
	frappe.has_permission("Asset Maintenance", "read", asset_maintenance, throw=True)
	return frappe.get_all(
		"Asset Maintenance Task",
		filters={"parent": asset_maintenance, "parenttype": "Asset Maintenance"},
		or_filters={"name": ("like", f"%{txt}%"), "maintenance_task": ("like", f"%{txt}%")},
		fields=["name", "maintenance_task"],
		as_list=True,
	)
