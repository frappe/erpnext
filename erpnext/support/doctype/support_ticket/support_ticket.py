# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.model.document import Document
from frappe.utils import now

class SupportTicket(Document):
	def get_feed(self):
		return "{0}: {1}".format(_(self.status), self.subject)

	def get_portal_page(self):
		return "ticket"

	def validate(self):
		self.update_status()
		self.set_lead_contact(self.raised_by)

		if self.status == "Closed":
			from frappe.desk.form.assign_to import clear
			clear(self.doctype, self.name)

	def set_lead_contact(self, email_id):
		import email.utils
		email_id = email.utils.parseaddr(email_id)
		if email_id:
			if not self.lead:
				self.lead = frappe.db.get_value("Lead", {"email_id": email_id})
			if not self.contact:
				self.contact = frappe.db.get_value("Contact", {"email_id": email_id})

			if not self.company:
				self.company = frappe.db.get_value("Lead", self.lead, "company") or \
					frappe.db.get_default("company")

	def update_status(self):
		status = frappe.db.get_value("Support Ticket", self.name, "status")
		if self.status!="Open" and status =="Open" and not self.first_responded_on:
			self.first_responded_on = now()
		if self.status=="Closed" and status !="Closed":
			self.resolution_date = now()
		if self.status=="Open" and status !="Open":
			# if no date, it should be set as None and not a blank string "", as per mysql strict config
			self.resolution_date = None

@frappe.whitelist()
def set_status(name, status):
	st = frappe.get_doc("Support Ticket", name)
	st.status = status
	st.save()

def auto_close_tickets():
	frappe.db.sql("""update `tabSupport Ticket` set status = 'Closed'
		where status = 'Replied'
		and date_sub(curdate(),interval 15 Day) > modified""")
