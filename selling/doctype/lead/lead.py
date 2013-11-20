# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import cstr, validate_email_add, cint, extract_email_id
from webnotes import session, msgprint

	
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
		customer = webnotes.conn.get_value("Customer", {"lead_name": self.doc.name})
		if customer:
			self.doc.fields["__is_customer"] = customer
	
	def validate(self):
		self.set_status()
		
		if self.doc.source == 'Campaign' and not self.doc.campaign_name and session['user'] != 'Guest':
			webnotes.throw("Please specify campaign name")
		
		if self.doc.email_id:
			if not validate_email_add(self.doc.email_id):
				webnotes.throw('Please enter valid email id.')
				
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

	def on_trash(self):
		webnotes.conn.sql("""update `tabSupport Ticket` set lead='' where lead=%s""",
			self.doc.name)
		
		self.delete_events()
		
	def has_customer(self):
		return webnotes.conn.get_value("Customer", {"lead_name": self.doc.name})
		
	def has_opportunity(self):
		return webnotes.conn.get_value("Opportunity", {"lead": self.doc.name, "docstatus": 1,
			"status": ["!=", "Lost"]})

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
				"lead_name": "contact_display",
				"company_name": "customer_name",
				"email_id": "contact_email",
				"mobile_no": "contact_mobile"
			}
		}}, target_doclist)
		
	return [d if isinstance(d, dict) else d.fields for d in doclist]