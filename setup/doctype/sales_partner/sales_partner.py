# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, cstr, filter_strip_join

sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist

	def on_update(self):
		if cint(self.doc.show_in_website):
			from webnotes.webutils import update_page_name
			update_page_name(self.doc, self.doc.partner_name)
		
		if self.doc.page_name:
			from webnotes.webutils import clear_cache
			clear_cache(self.doc.page_name)
			clear_cache("partners")
		
	def get_contacts(self,nm):
		if nm:
			contact_details =webnotes.conn.convert_to_lists(sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where sales_partner = '%s'"%nm))
			return contact_details
		else:
			return ''
			
	def get_context(self):
		address = webnotes.conn.get_value("Address", 
			{"sales_partner": self.doc.name, "is_primary_address": 1}, 
			"*", as_dict=True)
		if address:
			city_state = ", ".join(filter(None, [address.city, address.state]))
			address_rows = [address.address_line1, address.address_line2,
				city_state, address.pincode, address.country]
				
			self.doc.fields.update({
				"email": address.email_id,
				"partner_address": filter_strip_join(address_rows, "\n<br>"),
				"phone": filter_strip_join(cstr(address.phone).split(","), "\n<br>")
			})