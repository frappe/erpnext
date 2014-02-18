# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, cstr, filter_strip_join

class DocType():
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		if self.doc.partner_website and not self.doc.partner_website.startswith("http"):
			self.doc.partner_website = "http://" + self.doc.partner_website

	def get_contacts(self,nm):
		if nm:
			contact_details =frappe.conn.convert_to_lists(frappe.conn.sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where sales_partner = '%s'"%nm))
			return contact_details
		else:
			return ''

	def get_page_title(self):
		return self.doc.partner_name
