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
from webnotes.model.doc import Document
from webnotes import msgprint

class DocType:
	def __init__(self, doc, doclist=[]):
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
		"""add events for milestones"""
		webnotes.conn.sql("""delete from tabEvent where ref_type='Project' and ref_name=%s""",
			self.doc.name)
		for d in self.doclist:
			if d.doctype=='Project Milestone' and d.docstatus!=2:
				self.add_calendar_event(d.milestone, d.milestone_date)

	def add_calendar_event(self, milestone, date):
		""" Add calendar event for task in calendar of Allocated person"""
		event = Document('Event')
		event.description = milestone + ' for ' + self.doc.name
		event.event_date = date
		event.event_hour =  '10:00'
		event.event_type = 'Public'
		event.ref_type = 'Project'
		event.ref_name = self.doc.name
		event.save(1)
		
	def update_percent_complete(self):
		total = webnotes.conn.sql("""select count(*) from tabTask where project=%s""", 
			self.doc.name)[0][0]
		if total:
			completed = webnotes.conn.sql("""select count(*) from tabTask where
				project=%s and status='Closed'""", self.doc.name)[0][0]
			webnotes.conn.set_value("Project", self.doc.name, "percent_complete",
			 	int(float(completed) / total * 100))

