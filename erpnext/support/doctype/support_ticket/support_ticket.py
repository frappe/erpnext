# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from erpnext.utilities.transaction_base import TransactionBase
from frappe.utils import now, extract_email_id

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def get_sender(self, comm):
		return frappe.db.get_value('Email Settings',None,'support_email')

	def get_subject(self, comm):
		return '[' + self.doc.name + '] ' + (comm.subject or 'No Subject Specified')
	
	def get_content(self, comm):
		signature = frappe.db.get_value('Email Settings',None,'support_signature')
		content = comm.content
		if signature:
			content += '<p>' + signature + '</p>'
		return content
		
	def get_portal_page(self):
		return "ticket"
	
	def validate(self):
		self.update_status()
		self.set_lead_contact(self.doc.raised_by)
		
		if self.doc.status == "Closed":
			from frappe.widgets.form.assign_to import clear
			clear(self.doc.doctype, self.doc.name)
				
	def set_lead_contact(self, email_id):
		import email.utils
		email_id = email.utils.parseaddr(email_id)
		if email_id:
			if not self.doc.lead:
				self.doc.lead = frappe.db.get_value("Lead", {"email_id": email_id})
			if not self.doc.contact:
				self.doc.contact = frappe.db.get_value("Contact", {"email_id": email_id})
				
			if not self.doc.company:		
				self.doc.company = frappe.db.get_value("Lead", self.doc.lead, "company") or \
					frappe.db.get_default("company")

	def update_status(self):
		status = frappe.db.get_value("Support Ticket", self.doc.name, "status")
		if self.doc.status!="Open" and status =="Open" and not self.doc.first_responded_on:
			self.doc.first_responded_on = now()
		if self.doc.status=="Closed" and status !="Closed":
			self.doc.resolution_date = now()
		if self.doc.status=="Open" and status !="Open":
			self.doc.resolution_date = ""

@frappe.whitelist()
def set_status(name, status):
	st = frappe.bean("Support Ticket", name)
	st.doc.status = status
	st.save()
		
def auto_close_tickets():
	frappe.db.sql("""update `tabSupport Ticket` set status = 'Closed' 
		where status = 'Replied' 
		and date_sub(curdate(),interval 15 Day) > modified""")
