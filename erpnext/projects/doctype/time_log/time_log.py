# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import cstr


class OverlapError(webnotes.ValidationError): pass

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.set_status()
		self.validate_overlap()
		self.calculate_total_hours()
		
	def calculate_total_hours(self):
		from webnotes.utils import time_diff_in_hours
		self.doc.hours = time_diff_in_hours(self.doc.to_time, self.doc.from_time)

	def set_status(self):
		self.doc.status = {
			0: "Draft",
			1: "Submitted",
			2: "Cancelled"
		}[self.doc.docstatus or 0]
		
		if self.doc.time_log_batch:
			self.doc.status="Batched for Billing"
			
		if self.doc.sales_invoice:
			self.doc.status="Billed"
			
	def validate_overlap(self):		
		existing = webnotes.conn.sql_list("""select name from `tabTime Log` where owner=%s and
			(
				(from_time between %s and %s) or 
				(to_time between %s and %s) or 
				(%s between from_time and to_time)) 
			and name!=%s
			and ifnull(task, "")=%s
			and docstatus < 2""", 
			(self.doc.owner, self.doc.from_time, self.doc.to_time, self.doc.from_time, 
				self.doc.to_time, self.doc.from_time, self.doc.name or "No Name",
				cstr(self.doc.task)))

		if existing:
			webnotes.msgprint(_("This Time Log conflicts with") + ":" + ', '.join(existing),
				raise_exception=OverlapError)
	
	def before_cancel(self):
		self.set_status()
	
	def before_update_after_submit(self):
		self.set_status()
				
@webnotes.whitelist()
def get_events(start, end):
	from webnotes.widgets.reportview import build_match_conditions
	if not webnotes.has_permission("Time Log"):
		webnotes.msgprint(_("No Permission"), raise_exception=1)

	match = build_match_conditions("Time Log")
	data = webnotes.conn.sql("""select name, from_time, to_time, 
		activity_type, task, project from `tabTime Log`
		where from_time between '%(start)s' and '%(end)s' or to_time between '%(start)s' and '%(end)s'
		%(match)s""" % {
			"start": start,
			"end": end,
			"match": match and (" and " + match) or ""
		}, as_dict=True, update={"allDay": 0})
		
	for d in data:
		d.title = d.name + ": " + (d.activity_type or "[Activity Type not set]")
		if d.task:
			d.title += " for Task: " + d.task
		if d.project:
			d.title += " for Project: " + d.project
			
	return data
