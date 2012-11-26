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
		# TODO: create unsubscribed check in customer
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
		
		webnotes.conn.set(self.doc, "email_sent", 1)
		webnotes.msgprint("""Scheduled to send to %s""" % \
			", ".join(["%d %s(s)" % (self.send_count[s], s) for s in self.send_count]))
			
	def test_send(self, doctype="Lead"):
		args = self.dt_map[doctype]
		sender = webnotes.utils.get_email_id(self.doc.owner)
		recipients = self.doc.test_email_id.split(",")
		from webnotes.utils.email_lib.bulk import send
		send(recipients = recipients, sender = sender, 
			subject = self.doc.subject, message = self.get_message(),
			doctype = doctype, email_field = args["email_field"],
			first_name_field = args["first_name_field"], last_name_field = "")
		webnotes.msgprint("""Scheduled to send to %s""" % self.doc.test_email_id)
		
	def get_recipients(self, key):
		recipients = webnotes.conn.sql(self.query_map[key])
		recipients = [r[0] for r in recipients if r not in self.all_recipients]
		self.all_recipients += recipients
		return recipients
		
	def get_message(self):
		if not hasattr(self, "message"):
			import markdown2
			self.message = markdown2.markdown(self.doc.message)
		return self.message
		
	def send(self, query_key, doctype):
		webnotes.conn.auto_commit_on_many_writes = True
		recipients = self.get_recipients(query_key)
		sender = webnotes.utils.get_email_id(self.doc.owner)
		args = self.dt_map[doctype]
		self.send_count[doctype] = self.send_count.setdefault(doctype, 0) + len(recipients)
		
		from webnotes.utils.email_lib.bulk import send
		send(recipients = recipients, sender = sender, 
			subject = self.doc.subject, message = self.get_message(),
			doctype = doctype, email_field = args["email_field"],
			first_name_field = args["first_name_field"], last_name_field = "")