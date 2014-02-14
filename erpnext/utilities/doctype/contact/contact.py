# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, extract_email_id

from erpnext.controllers.status_updater import StatusUpdater

class DocType(StatusUpdater):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		# concat first and last name
		self.doc.name = " ".join(filter(None, 
			[cstr(self.doc.fields.get(f)).strip() for f in ["first_name", "last_name"]]))
		
		# concat party name if reqd
		for fieldname in ("customer", "supplier", "sales_partner"):
			if self.doc.fields.get(fieldname):
				self.doc.name = self.doc.name + "-" + cstr(self.doc.fields.get(fieldname)).strip()
				break
		
	def validate(self):
		self.set_status()
		self.validate_primary_contact()

	def validate_primary_contact(self):
		if self.doc.is_primary_contact == 1:
			if self.doc.customer:
				frappe.conn.sql("update tabContact set is_primary_contact=0 where customer = '%s'" % (self.doc.customer))
			elif self.doc.supplier:
				frappe.conn.sql("update tabContact set is_primary_contact=0 where supplier = '%s'" % (self.doc.supplier))	
			elif self.doc.sales_partner:
				frappe.conn.sql("update tabContact set is_primary_contact=0 where sales_partner = '%s'" % (self.doc.sales_partner))
		else:
			if self.doc.customer:
				if not frappe.conn.sql("select name from tabContact where is_primary_contact=1 and customer = '%s'" % (self.doc.customer)):
					self.doc.is_primary_contact = 1
			elif self.doc.supplier:
				if not frappe.conn.sql("select name from tabContact where is_primary_contact=1 and supplier = '%s'" % (self.doc.supplier)):
					self.doc.is_primary_contact = 1
			elif self.doc.sales_partner:
				if not frappe.conn.sql("select name from tabContact where is_primary_contact=1 and sales_partner = '%s'" % (self.doc.sales_partner)):
					self.doc.is_primary_contact = 1

	def on_trash(self):
		frappe.conn.sql("""update `tabSupport Ticket` set contact='' where contact=%s""",
			self.doc.name)

@frappe.whitelist()
def get_contact_details(contact):
	contact = frappe.doc("Contact", contact)
	out = {
		"contact_person": contact.get("name"),
		"contact_display": " ".join(filter(None, 
			[contact.get("first_name"), contact.get("last_name")])),
		"contact_email": contact.get("email_id"),
		"contact_mobile": contact.get("mobile_no"),
		"contact_phone": contact.get("phone"),
		"contact_designation": contact.get("designation"),
		"contact_department": contact.get("department")
	}
	
	return out