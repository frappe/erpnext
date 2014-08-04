# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate
from frappe import _
from erpnext.utilities.transaction_base import delete_events

from frappe.model.document import Document

class Project(Document):

	def get_gross_profit(self):
		pft, per_pft =0, 0
		pft = flt(self.project_value) - flt(self.est_material_cost)
		#if pft > 0:
		per_pft = (flt(pft) / flt(self.project_value)) * 100
		ret = {'gross_margin_value': pft, 'per_gross_margin': per_pft}
		return ret

	def validate(self):
		"""validate start date before end date"""
		if self.project_start_date and self.completion_date:
			if getdate(self.completion_date) < getdate(self.project_start_date):
				frappe.throw(_("Expected Completion Date can not be less than Project Start Date"))

		self.update_milestones_completed()

	def update_milestones_completed(self):
		if self.project_milestones:
			completed = filter(lambda x: x.status=="Completed", self.project_milestones)
			self.percent_milestones_completed =  len(completed) * 100 / len(self.project_milestones)

	def on_update(self):
		self.add_calendar_event()

	def update_percent_complete(self):
		total = frappe.db.sql("""select count(*) from tabTask where project=%s""",
			self.name)[0][0]
		if total:
			completed = frappe.db.sql("""select count(*) from tabTask where
				project=%s and status in ('Closed', 'Cancelled')""", self.name)[0][0]
			frappe.db.set_value("Project", self.name, "percent_complete",
			 	int(float(completed) / total * 100))


	def add_calendar_event(self):
		# delete any earlier event for this project
		delete_events(self.doctype, self.name)

		# add events
		for milestone in self.get("project_milestones"):
			if milestone.milestone_date:
				description = (milestone.milestone or "Milestone") + " for " + self.name
				frappe.get_doc({
					"doctype": "Event",
					"owner": self.owner,
					"subject": description,
					"description": description,
					"starts_on": milestone.milestone_date + " 10:00:00",
					"event_type": "Private",
					"ref_type": self.doctype,
					"ref_name": self.name
				}).insert(ignore_permissions=True)

	def on_trash(self):
		delete_events(self.doctype, self.name)
