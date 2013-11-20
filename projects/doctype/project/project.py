# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import flt, getdate
from webnotes import msgprint
from utilities.transaction_base import delete_events

class DocType:
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist
	
	def get_gross_profit(self):
		pft, per_pft =0, 0
		pft = flt(self.doc.project_value) - flt(self.doc.est_material_cost)
		#if pft > 0:
		per_pft = (flt(pft) / flt(self.doc.project_value)) * 100
		ret = {'gross_margin_value': pft, 'per_gross_margin': per_pft}
		return ret
		
	def validate(self):
		"""validate start date before end date"""
		if self.doc.project_start_date and self.doc.completion_date:
			if getdate(self.doc.completion_date) < getdate(self.doc.project_start_date):
				msgprint("Expected Completion Date can not be less than Project Start Date")
				raise Exception
				
	def on_update(self):
		self.add_calendar_event()
		
	def update_percent_complete(self):
		total = webnotes.conn.sql("""select count(*) from tabTask where project=%s""", 
			self.doc.name)[0][0]
		if total:
			completed = webnotes.conn.sql("""select count(*) from tabTask where
				project=%s and status in ('Closed', 'Cancelled')""", self.doc.name)[0][0]
			webnotes.conn.set_value("Project", self.doc.name, "percent_complete",
			 	int(float(completed) / total * 100))

	def add_calendar_event(self):
		# delete any earlier event for this project
		delete_events(self.doc.doctype, self.doc.name)
		
		# add events
		for milestone in self.doclist.get({"parentfield": "project_milestones"}):
			if milestone.milestone_date:
				description = (milestone.milestone or "Milestone") + " for " + self.doc.name
				webnotes.bean({
					"doctype": "Event",
					"owner": self.doc.owner,
					"subject": description,
					"description": description,
					"starts_on": milestone.milestone_date + " 10:00:00",
					"event_type": "Private",
					"ref_type": self.doc.doctype,
					"ref_name": self.doc.name
				}).insert()
	
	def on_trash(self):
		delete_events(self.doc.doctype, self.doc.name)
