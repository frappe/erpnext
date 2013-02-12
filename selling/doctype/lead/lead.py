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
from webnotes import _
from webnotes.utils import cstr, validate_email_add
from webnotes.model.doc import Document, addchild
from webnotes import session, msgprint

sql = webnotes.conn.sql
	
from controllers.selling_controller import SellingController

class DocType(SellingController):
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist

	def onload(self):
		self.add_communication_list()

	def on_communication_sent(self, comm):
		webnotes.conn.set(self.doc, 'status', 'Replied')

	def check_status(self):
		chk = sql("select status from `tabLead` where name=%s", self.doc.name)
		chk = chk and chk[0][0] or ''
		return cstr(chk)
	
	def validate(self):
		if self.doc.status == 'Lead Lost' and not self.doc.order_lost_reason:
			msgprint("Please Enter Lost Reason under More Info section")
			raise Exception	
		
		if self.doc.source == 'Campaign' and not self.doc.campaign_name and session['user'] != 'Guest':
			msgprint("Please specify campaign name")
			raise Exception
		
		if self.doc.email_id:
			if not validate_email_add(self.doc.email_id):
				msgprint('Please enter valid email id.')
				raise Exception
				
	
	def on_update(self):
		if self.doc.contact_date:
			self.add_calendar_event()
			
		self.check_email_id_is_unique()

	def check_email_id_is_unique(self):
		if self.doc.email_id:
			# validate email is unique
			email_list = webnotes.conn.sql("""select name from tabLead where email_id=%s""", 
				self.doc.email_id)
			if len(email_list) > 1:
				items = [e[0] for e in email_list if e[0]!=self.doc.name]
				webnotes.msgprint(_("""Email Id must be unique, already exists for: """) + \
					", ".join(items), raise_exception=True)
		
	def add_calendar_event(self):
		# delete any earlier event by this lead
		sql("delete from tabEvent where ref_type='Lead' and ref_name=%s", self.doc.name)
	
		# create new event
		ev = Document('Event')
		ev.owner = self.doc.lead_owner
		ev.description = ('Contact ' + cstr(self.doc.lead_name)) + \
			(self.doc.contact_by and ('. By : ' + cstr(self.doc.contact_by)) or '') + \
			(self.doc.remark and ('.To Discuss : ' + cstr(self.doc.remark)) or '')
		ev.event_date = self.doc.contact_date
		ev.event_hour = '10:00'
		ev.event_type = 'Private'
		ev.ref_type = 'Lead'
		ev.ref_name = self.doc.name
		ev.save(1)
		
		event_user = addchild(ev, 'event_individuals', 'Event User')
		event_user.person = self.doc.contact_by
		event_user.save()

	def get_sender(self, comm):
		return webnotes.conn.get_value('Sales Email Settings',None,'email_id')

	def on_trash(self):
		webnotes.conn.sql("""delete from tabCommunication where lead=%s""",
			self.doc.name)
		webnotes.conn.sql("""update `tabSupport Ticket` set lead='' where lead=%s""",
			self.doc.name)
