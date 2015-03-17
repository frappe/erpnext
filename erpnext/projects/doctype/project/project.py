# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate
from frappe import _

from frappe.model.document import Document

class Project(Document):
	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.project_name)

	def onload(self):
		"""Load project tasks for quick view"""
		for task in frappe.get_all("Task", "*", {"project": self.name}, order_by="exp_start_date asc"):
			self.append("tasks", {
				"title": task.subject,
				"status": task.status,
				"start_date": task.exp_start_date,
				"end_date": task.exp_end_date,
				"desciption": task.description,
				"task_id": task.name
			})

	def get_gross_profit(self):
		pft, per_pft =0, 0
		pft = flt(self.project_value) - flt(self.est_material_cost)
		#if pft > 0:
		per_pft = (flt(pft) / flt(self.project_value)) * 100
		ret = {'gross_margin_value': pft, 'per_gross_margin': per_pft}
		return ret

	def validate(self):
		if self.project_start_date and self.completion_date:
			if getdate(self.completion_date) < getdate(self.project_start_date):
				frappe.throw(_("Expected Completion Date can not be less than Project Start Date"))

		self.sync_tasks()

	def sync_tasks(self):
		"""sync tasks and remove table"""
		task_names = []
		for t in self.tasks:
			if t.task_id:
				task = frappe.get_doc("Task", t.task_id)
			else:
				task = frappe.new_doc("Task")
				task.project = self.name

			task.update({
				"subject": t.title,
				"status": t.status,
				"exp_start_date": t.start_date,
				"exp_end_date": t.end_date,
				"desciption": t.description,
			})

			task.flags.ignore_links = True
			task.flags.from_project = True
			task.save(ignore_permissions = True)
			task_names.append(task.name)

		# delete
		for t in frappe.get_all("Task", ["name"], {"project": self.name, "name": ("not in", task_names)}):
			frappe.delete_doc("Task", t.name)

		self.tasks = []

	def update_percent_complete(self):
		total = frappe.db.sql("""select count(*) from tabTask where project=%s""",
			self.name)[0][0]
		if total:
			completed = frappe.db.sql("""select count(*) from tabTask where
				project=%s and status in ('Closed', 'Cancelled')""", self.name)[0][0]
			frappe.db.set_value("Project", self.name, "percent_complete",
			 	int(float(completed) / total * 100))


@frappe.whitelist()
def get_cost_center_name(project_name):
	return frappe.db.get_value("Project", project_name, "cost_center")
