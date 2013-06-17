# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

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
