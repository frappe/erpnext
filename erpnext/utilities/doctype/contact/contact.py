# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, extract_email_id

from erpnext.controllers.status_updater import StatusUpdater

class Contact(StatusUpdater):

	def autoname(self):
		# concat first and last name
		self.name = " ".join(filter(None, 
			[cstr(self.get(f)).strip() for f in ["first_name", "last_name"]]))
		
		# concat party name if reqd
		for fieldname in ("customer", "supplier", "sales_partner"):
			if self.get(fieldname):
				self.name = self.name + "-" + cstr(self.get(fieldname)).strip()
				break
		
	def validate(self):
		self.set_status()
		self.validate_primary_contact()

	def validate_primary_contact(self):
		if self.is_primary_contact == 1:
			if self.customer:
				frappe.db.sql("update tabContact set is_primary_contact=0 where customer = %s", 
					(self.customer))
			elif self.supplier:
				frappe.db.sql("update tabContact set is_primary_contact=0 where supplier = %s", 
					 (self.supplier))	
			elif self.sales_partner:
				frappe.db.sql("""update tabContact set is_primary_contact=0 
					where sales_partner = %s""", (self.sales_partner))
		else:
			if self.customer:
				if not frappe.db.sql("select name from tabContact \
						where is_primary_contact=1 and customer = %s", (self.customer)):
					self.is_primary_contact = 1
			elif self.supplier:
				if not frappe.db.sql("select name from tabContact \
						where is_primary_contact=1 and supplier = %s", (self.supplier)):
					self.is_primary_contact = 1
			elif self.sales_partner:
				if not frappe.db.sql("select name from tabContact \
						where is_primary_contact=1 and sales_partner = %s", 
						self.sales_partner):
					self.is_primary_contact = 1

	def on_trash(self):
		frappe.db.sql("""update `tabSupport Ticket` set contact='' where contact=%s""",
			self.name)

@frappe.whitelist()
def get_contact_details(contact):
	contact = frappe.get_doc("Contact", contact)
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