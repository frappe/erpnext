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
from webnotes.utils import cstr, validate_email_add, cint
from webnotes import session, msgprint

sql = webnotes.conn.sql
	
from controllers.selling_controller import SellingController

class DocType(SellingController):
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist

		self._prev = webnotes._dict({
			"contact_date": webnotes.conn.get_value("Lead", self.doc.name, "contact_date") if \
				(not cint(self.doc.fields.get("__islocal"))) else None,
			"contact_by": webnotes.conn.get_value("Lead", self.doc.name, "contact_by") if \
				(not cint(self.doc.fields.get("__islocal"))) else None,
		})

	def onload(self):
		self.add_communication_list()
		customer = webnotes.conn.get_value("Customer", {"lead_name": self.doc.name})
		if customer:
			self.doc.fields["__is_customer"] = customer

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
		self.check_email_id_is_unique()
		self.add_calendar_event()
		
	def add_calendar_event(self, opts=None, force=False):
		super(DocType, self).add_calendar_event({
			"owner": self.doc.lead_owner,
			"subject": ('Contact ' + cstr(self.doc.lead_name)),
			"description": ('Contact ' + cstr(self.doc.lead_name)) + \
				(self.doc.contact_by and ('. By : ' + cstr(self.doc.contact_by)) or '') + \
				(self.doc.remark and ('.To Discuss : ' + cstr(self.doc.remark)) or '')
		}, force)

	def check_email_id_is_unique(self):
		if self.doc.email_id:
			# validate email is unique
			email_list = webnotes.conn.sql("""select name from tabLead where email_id=%s""", 
				self.doc.email_id)
			if len(email_list) > 1:
				items = [e[0] for e in email_list if e[0]!=self.doc.name]
				webnotes.msgprint(_("""Email Id must be unique, already exists for: """) + \
					", ".join(items), raise_exception=True)

	def get_sender(self, comm):
		return webnotes.conn.get_value('Sales Email Settings',None,'email_id')

	def on_trash(self):
		webnotes.conn.sql("""update tabCommunication set lead=null where lead=%s""", self.doc.name)
		webnotes.conn.sql("""update `tabSupport Ticket` set lead='' where lead=%s""",
			self.doc.name)
		
		self.delete_events()

@webnotes.whitelist()
def make_customer(source_name, target_doclist=None):
	return _make_customer(source_name, target_doclist)

def _make_customer(source_name, target_doclist=None, ignore_permissions=False):
	from webnotes.model.mapper import get_mapped_doclist
	
	def set_missing_values(source, target):
		if source.doc.company_name:
			target[0].customer_type = "Company"
			target[0].customer_name = source.doc.company_name
		else:
			target[0].customer_type = "Individual"
			target[0].customer_name = source.doc.lead_name
			
		target[0].customer_group = webnotes.conn.get_default("customer_group")
			
	doclist = get_mapped_doclist("Lead", source_name, 
		{"Lead": {
			"doctype": "Customer",
			"field_map": {
				"name": "lead_name",
				"company_name": "customer_name",
				"contact_no": "phone_1",
				"fax": "fax_1"
			}
		}}, target_doclist, set_missing_values, ignore_permissions=ignore_permissions)
		
	return [d.fields for d in doclist]
	
@webnotes.whitelist()
def make_opportunity(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
		
	doclist = get_mapped_doclist("Lead", source_name, 
		{"Lead": {
			"doctype": "Opportunity",
			"field_map": {
				"campaign_name": "campaign",
				"doctype": "enquiry_from",
				"name": "lead",
			}
		}}, target_doclist)
		
	return [d.fields for d in doclist]