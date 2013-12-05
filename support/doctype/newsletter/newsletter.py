# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes
import webnotes.utils
from webnotes.utils import cstr
from webnotes import _

class DocType():
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def onload(self):
		if self.doc.email_sent:
			self.doc.fields["__status_count"] = dict(webnotes.conn.sql("""select status, count(*)
				from `tabBulk Email` where ref_doctype=%s and ref_docname=%s
				group by status""", (self.doc.doctype, self.doc.name))) or None

	def test_send(self, doctype="Lead"):
		self.recipients = self.doc.test_email_id.split(",")
		self.send_to_doctype = "Lead"
		self.send_bulk()
		webnotes.msgprint("""Scheduled to send to %s""" % self.doc.test_email_id)

	def send_emails(self):
		"""send emails to leads and customers"""
		if self.doc.email_sent:
			webnotes.msgprint("""Newsletter has already been sent""", raise_exception=1)

		self.recipients = self.get_recipients()
		self.send_bulk()
		
		webnotes.msgprint("""Scheduled to send to %d %s(s)""" % (len(self.recipients), 
			self.send_to_doctype))

		webnotes.conn.set(self.doc, "email_sent", 1)
	
	def get_recipients(self):
		if self.doc.send_to_type=="Contact":
			self.send_to_doctype = "Contact"
			if self.doc.contact_type == "Customer":		
				return webnotes.conn.sql_list("""select email_id from tabContact 
					where ifnull(email_id, '') != '' and ifnull(customer, '') != ''""")

			elif self.doc.contact_type == "Supplier":		
				return webnotes.conn.sql_list("""select email_id from tabContact 
					where ifnull(email_id, '') != '' and ifnull(supplier, '') != ''""")
	
		elif self.doc.send_to_type=="Lead":
			self.send_to_doctype = "Lead"
			conditions = []
			if self.doc.lead_source and self.doc.lead_source != "All":
				conditions.append(" and source='%s'" % self.doc.lead_source)
			if self.doc.lead_status and self.doc.lead_status != "All":
				conditions.append(" and status='%s'" % self.doc.lead_status)

			if conditions:
				conditions = "".join(conditions)
				
			return webnotes.conn.sql_list("""select email_id from tabLead 
				where ifnull(email_id, '') != '' %s""" % (conditions or ""))

		elif self.doc.email_list:
			email_list = [cstr(email).strip() for email in self.doc.email_list.split(",")]
			for email in email_list:
				create_lead(email)
					
			self.send_to_doctype = "Lead"
			return email_list
	
	def send_bulk(self):
		self.validate_send()

		sender = self.doc.send_from or webnotes.utils.get_formatted_email(self.doc.owner)
		
		from webnotes.utils.email_lib.bulk import send
		
		if not webnotes.flags.in_test:
			webnotes.conn.auto_commit_on_many_writes = True
		
		send(recipients = self.recipients, sender = sender, 
			subject = self.doc.subject, message = self.doc.message,
			doctype = self.send_to_doctype, email_field = "email_id",
			ref_doctype = self.doc.doctype, ref_docname = self.doc.name)

		if not webnotes.flags.in_test:
			webnotes.conn.auto_commit_on_many_writes = False

	def validate_send(self):
		if self.doc.fields.get("__islocal"):
			webnotes.msgprint(_("""Please save the Newsletter before sending."""),
				raise_exception=1)

		from webnotes import conf
		if (conf.get("status") or None) == "Trial":
			webnotes.msgprint(_("""Sending newsletters is not allowed for Trial users, \
				to prevent abuse of this feature."""), raise_exception=1)

@webnotes.whitelist()
def get_lead_options():
	return {
		"sources": ["All"] + filter(None, 
			webnotes.conn.sql_list("""select distinct source from tabLead""")),
		"statuses": ["All"] + filter(None, 
			webnotes.conn.sql_list("""select distinct status from tabLead"""))
	}


def create_lead(email_id):
	"""create a lead if it does not exist"""
	from email.utils import parseaddr
	from webnotes.model.doc import get_default_naming_series
	real_name, email_id = parseaddr(email_id)
	
	if webnotes.conn.get_value("Lead", {"email_id": email_id}):
		return
	
	lead = webnotes.bean({
		"doctype": "Lead",
		"email_id": email_id,
		"lead_name": real_name or email_id,
		"status": "Contacted",
		"naming_series": get_default_naming_series("Lead"),
		"company": webnotes.conn.get_default("company"),
		"source": "Email"
	})
	lead.insert()