# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, validate_email_add
from webnotes.model.doc import Document, addchild
from webnotes import session, msgprint

sql = webnotes.conn.sql
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def onload(self):
		self.add_communication_list();

	def on_update(self):
		if self.doc.contact_date:
			self.add_calendar_event()
		
	def add_calendar_event(self):
		# delete any earlier event by this lead
		event=sql("select name from tabEvent where ref_type='Job Applicant' and ref_name=%s",self.doc.name)
		if event:
			sql("delete from `tabEvent User` where parent=%s", event[0])
		sql("delete from tabEvent where ref_type='Job Applicant' and ref_name=%s", self.doc.name)
		# create new event
		ev = Document('Event')
		ev.owner = self.doc.contact_owner
		ev.description = ('Contact ' + cstr(self.doc.applicant_name)) + \
			(self.doc.interviewed_by and ('. By : ' + cstr(self.doc.interviewed_by)) or '') + \
			(self.doc.remarks and ('.To Discuss : ' + cstr(self.doc.remarks)) or '')
		ev.event_date = self.doc.contact_date
		ev.event_hour = '10:00'
		ev.event_type = 'Private'
		ev.ref_type = 'Job Applicant'
		ev.ref_name = self.doc.name
		ev.save(1)
		
		
		event_user = addchild(ev, 'event_individuals', 'Event User')
		event_user.person = self.doc.contact_owner
		event_user.save()

	def on_trash(self):
		webnotes.conn.sql("""update tabCommunication set job_applicant='' where job_applicant=%s""",
			self.doc.name)
		webnotes.conn.sql("""update `tabSupport Ticket` set job_applicant='' where job_applicant=%s""",
			self.doc.name)