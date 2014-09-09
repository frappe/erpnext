# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import frappe.utils
from frappe.utils import cstr
from frappe import throw, _
from frappe.model.document import Document
import erpnext.tasks

class Newsletter(Document):
	def onload(self):
		if self.email_sent:
			self.get("__onload").status_count = dict(frappe.db.sql("""select status, count(name)
				from `tabBulk Email` where ref_doctype=%s and ref_docname=%s
				group by status""", (self.doctype, self.name))) or None

	def test_send(self, doctype="Lead"):
		self.recipients = self.test_email_id.split(",")
		self.send_to_doctype = "Lead"
		self.send_bulk()
		frappe.msgprint(_("Scheduled to send to {0}").format(self.test_email_id))

	def send_emails(self):
		"""send emails to leads and customers"""
		if self.email_sent:
			throw(_("Newsletter has already been sent"))

		self.recipients = self.get_recipients()

		if getattr(frappe.local, "is_ajax", False):
			# to avoid request timed out!
			self.validate_send()

			# hack! event="bulk_long" to queue in longjob queue
			erpnext.tasks.send_newsletter.delay(frappe.local.site, self.name, event="bulk_long")
		else:
			self.send_bulk()

		frappe.msgprint(_("Scheduled to send to {0} recipients").format(len(self.recipients)))

		frappe.db.set(self, "email_sent", 1)

	def get_recipients(self):
		self.email_field = None
		if self.send_to_type=="Contact":
			self.send_to_doctype = "Contact"
			if self.contact_type == "Customer":
				return frappe.db.sql_list("""select email_id from tabContact
					where ifnull(email_id, '') != '' and ifnull(customer, '') != ''""")

			elif self.contact_type == "Supplier":
				return frappe.db.sql_list("""select email_id from tabContact
					where ifnull(email_id, '') != '' and ifnull(supplier, '') != ''""")

		elif self.send_to_type=="Lead":
			self.send_to_doctype = "Lead"
			conditions = []
			if self.lead_source and self.lead_source != "All":
				conditions.append(" and source='%s'" % self.lead_source.replace("'", "\'"))
			if self.lead_status and self.lead_status != "All":
				conditions.append(" and status='%s'" % self.lead_status.replace("'", "\'"))

			if conditions:
				conditions = "".join(conditions)

			return frappe.db.sql_list("""select email_id from tabLead
				where ifnull(email_id, '') != '' %s""" % (conditions or ""))

		elif self.send_to_type=="Employee":
			self.send_to_doctype = "Employee"
			self.email_field = "company_email"

			return frappe.db.sql_list("""select
				if(ifnull(company_email, '')!='', company_email, personal_email) as email_id
				from `tabEmployee` where status='Active'""")

		elif self.email_list:
			email_list = [cstr(email).strip() for email in self.email_list.split(",")]
			for email in email_list:
				create_lead(email)

			self.send_to_doctype = "Lead"
			return email_list

	def send_bulk(self):
		if not self.get("recipients"):
			# in case it is called via worker
			self.recipients = self.get_recipients()

		self.validate_send()

		sender = self.send_from or frappe.utils.get_formatted_email(self.owner)

		from frappe.utils.email_lib.bulk import send

		if not frappe.flags.in_test:
			frappe.db.auto_commit_on_many_writes = True

		send(recipients = self.recipients, sender = sender,
			subject = self.subject, message = self.message,
			doctype = self.send_to_doctype, email_field = self.get("email_field") or "email_id",
			ref_doctype = self.doctype, ref_docname = self.name)

		if not frappe.flags.in_test:
			frappe.db.auto_commit_on_many_writes = False

	def validate_send(self):
		if self.get("__islocal"):
			throw(_("Please save the Newsletter before sending"))

@frappe.whitelist()
def get_lead_options():
	return {
		"sources": ["All"] + filter(None,
			frappe.db.sql_list("""select distinct source from tabLead""")),
		"statuses": ["All"] + filter(None,
			frappe.db.sql_list("""select distinct status from tabLead"""))
	}


def create_lead(email_id):
	"""create a lead if it does not exist"""
	from email.utils import parseaddr
	from frappe.model.naming import get_default_naming_series
	real_name, email_id = parseaddr(email_id)

	if frappe.db.get_value("Lead", {"email_id": email_id}):
		return

	lead = frappe.get_doc({
		"doctype": "Lead",
		"email_id": email_id,
		"lead_name": real_name or email_id,
		"status": "Lead",
		"naming_series": get_default_naming_series("Lead"),
		"company": frappe.db.get_default("company"),
		"source": "Email"
	})
	lead.insert()
