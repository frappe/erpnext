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

	def validate(self):
		self.validate_dates()
		self.sync_tasks()

	def validate_dates(self):
		if self.expected_start_date and self.expected_end_date:
			if getdate(self.expected_end_date) < getdate(self.expected_start_date):
				frappe.throw(_("Expected End Date can not be less than Expected Start Date"))

	def sync_tasks(self):
		"""sync tasks and remove table"""
		if self.flags.dont_sync_tasks: return
		
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
				
	def update_costing(self):
		total_cost = frappe.db.sql("""select sum(total_costing_amount) as costing_amount,
			sum(total_billing_amount) as billing_amount, sum(total_expense_claim) as expense_claim,
			min(act_start_date) as start_date, max(act_end_date) as end_date, sum(actual_time) as time
			from `tabTask` where project = %s""", self.name, as_dict=1)[0]
			
		self.total_costing_amount = total_cost.costing_amount
		self.total_billing_amount = total_cost.billing_amount
		self.total_expense_claim = total_cost.expense_claim
		self.actual_start_date = total_cost.start_date
		self.actual_end_date = total_cost.end_date
		self.actual_time = total_cost.time
		self.gross_margin = flt(total_cost.billing_amount) - flt(total_cost.costing_amount)
		if self.total_billing_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billing_amount)) *100

@frappe.whitelist()
def get_cost_center_name(project_name):
	return frappe.db.get_value("Project", project_name, "cost_center")
