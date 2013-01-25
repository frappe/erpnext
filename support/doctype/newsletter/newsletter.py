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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import webnotes
import webnotes.utils
from webnotes.utils import cstr
from webnotes.model.doc import Document
from webnotes import _

class DocType():
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		self.dt_map = {
			"Contact": {
				"email_field": "email_id",
				"first_name_field": "first_name",
			},
			"Lead": {
				"email_field": "email_id",
				"first_name_field": "lead_name"
			}
		}
		self.query_map = {
			"contacts": """select distinct email_id from `tabContact`
				where ifnull(email_id, '') != '' """,
			"customer_contacts": """select distinct email_id from `tabContact`
				where ifnull(customer, '') != '' and ifnull(email_id, '') != '' """,
			"leads": """select distinct email_id from `tabLead`
				where ifnull(email_id, '') != '' """,
			"active_leads": """select distinct email_id from `tabLead`
				where status = "Open" and ifnull(email_id, '') != '' """,
			"blog_subscribers": """select distinct email_id from `tabLead`
				where ifnull(blog_subscriber,0) = 1 and ifnull(email_id, '') != '' """
		}
		
	def send_emails(self):
		"""send emails to leads and customers"""
		if self.doc.email_sent:
			webnotes.msgprint("""Newsletter has already been sent""", raise_exception=1)

		self.all_recipients = []
		self.send_count = {}
		
		if self.doc.contacts:
			self.send("contacts", "Contact")
		elif self.doc.customer_contacts:
			self.send("customer_contacts", "Contact")
		
		if self.doc.leads:
			self.send("leads", "Lead")
		else:
			if self.doc.active_leads:
				self.send("active_leads", "Lead")
				
			if self.doc.blog_subscribers:
				self.send("blog_subscribers", "Lead")
				
		if self.doc.email_list:
			email_list = [cstr(email).strip() for email in self.doc.email_list.split(",")]
			for email in email_list:
				if not webnotes.conn.exists({"doctype": "Lead", "email_id": email}):
					create_lead(email)
			
			self.send(email_list, "Lead")
		
		webnotes.msgprint("""Scheduled to send to %s""" % \
			", ".join(["%d %s(s)" % (self.send_count[s], s) for s in self.send_count]))
			
	def test_send(self, doctype="Lead"):
		self.validate_send()

		args = self.dt_map[doctype]

		sender = self.doc.send_from or webnotes.utils.get_formatted_email(self.doc.owner)
		recipients = self.doc.test_email_id.split(",")
		from webnotes.utils.email_lib.bulk import send
		send(recipients = recipients, sender = sender, 
			subject = self.doc.subject, message = self.doc.message,
			doctype = doctype, email_field = args["email_field"])
		webnotes.msgprint("""Scheduled to send to %s""" % self.doc.test_email_id)
		
	def get_recipients(self, key):
		recipients = webnotes.conn.sql(self.query_map[key])
		recipients = [r[0] for r in recipients if r not in self.all_recipients]
		self.all_recipients += recipients
		return recipients
		
	def send(self, query_key, doctype):
		self.validate_send()

		webnotes.conn.auto_commit_on_many_writes = True
		if isinstance(query_key, basestring) and self.query_map.has_key(query_key):
			recipients = self.get_recipients(query_key)
		else:
			recipients = query_key
		sender = self.doc.send_from or webnotes.utils.get_formatted_email(self.doc.owner)
		args = self.dt_map[doctype]
		self.send_count[doctype] = self.send_count.setdefault(doctype, 0) + \
			len(recipients)
		
		from webnotes.utils.email_lib.bulk import send
		send(recipients = recipients, sender = sender, 
			subject = self.doc.subject, message = self.doc.message,
			doctype = doctype, email_field = args["email_field"])

		webnotes.conn.set(self.doc, "email_sent", 1)

	def validate_send(self):
		if self.doc.fields.get("__islocal"):
			webnotes.msgprint(_("""Please save the Newsletter before sending."""),
				raise_exception=1)

		import conf
		if getattr(conf, "status", None) == "Trial":
			webnotes.msgprint(_("""Sending newsletters is not allowed for Trial users, \
				to prevent abuse of this feature."""), raise_exception=1)

lead_naming_series = None
def create_lead(email_id):
	"""create a lead if it does not exist"""
	from email.utils import parseaddr
	real_name, email_id = parseaddr(email_id)
	lead = Document("Lead")
	lead.fields["__islocal"] = 1
	lead.lead_name = real_name or email_id
	lead.email_id = email_id
	lead.status = "Contacted"
	lead.naming_series = lead_naming_series or get_lead_naming_series()
	lead.company = webnotes.conn.get_default("company")
	lead.source = "Email"
	lead.save()
	
def get_lead_naming_series():
	"""gets lead's default naming series"""
	global lead_naming_series
	naming_series_field = webnotes.get_doctype("Lead").get_field("naming_series")
	if naming_series_field.default:
		lead_naming_series = naming_series_field.default
	else:
		latest_naming_series = webnotes.conn.sql("""select naming_series
			from `tabLead` order by creation desc limit 1""")
		if latest_naming_series:
			lead_naming_series = latest_naming_series[0][0]
		else:
			lead_naming_series = filter(None, naming_series_field.options.split("\n"))[0]
	
	return lead_naming_series
