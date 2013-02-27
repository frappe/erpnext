# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

from webnotes.widgets.reportview import build_match_conditions

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.validate_overlap()
		
	def validate_overlap(self):
		existing = webnotes.conn.sql_list("""select name from `tabTime Log` where owner=%s and
			((from_time between %s and %s) or (to_time between %s and %s)) and name!=%s""", 
			(self.doc.owner, self.doc.from_time, self.doc.to_time, self.doc.from_time, 
				self.doc.to_time, self.doc.name))

		if existing:
			webnotes.msgprint(_("This Time Log conflicts with") + ":" + ', '.join(existing),
				raise_exception=True)
		
@webnotes.whitelist()
def get_events(start, end):
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
		d.title = d.name + ": " + d.activity_type
		if d.task:
			d.title += " for Task: " + d.task
		if d.project:
			d.title += " for Project: " + d.project
			
	return data
