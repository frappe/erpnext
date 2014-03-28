# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, cstr, filter_strip_join
from frappe.model.document import Document

class SalesPartner(Document):
	def validate(self):
		if self.partner_website and not self.partner_website.startswith("http"):
			self.partner_website = "http://" + self.partner_website

	def get_contacts(self, nm):
		if nm:
			return frappe.db.convert_to_lists(frappe.db.sql("""
				select name, CONCAT(IFNULL(first_name,''), 
					' ',IFNULL(last_name,'')),contact_no,email_id 
				from `tabContact` where sales_partner = %s""", nm))
		else:
			return ''

	def get_page_title(self):
		return self.partner_name
