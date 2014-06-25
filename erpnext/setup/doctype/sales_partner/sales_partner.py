# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, filter_strip_join
from frappe.website.website_generator import WebsiteGenerator

condition_field = "show_in_website"
template = "templates/generators/sales_partner.html"

class SalesPartner(WebsiteGenerator):
	def autoname(self):
		self.name = self.partner_name

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

	def get_context(self, context):
		address = frappe.db.get_value("Address",
			{"sales_partner": self.name, "is_primary_address": 1},
			"*", as_dict=True)
		if address:
			city_state = ", ".join(filter(None, [address.city, address.state]))
			address_rows = [address.address_line1, address.address_line2,
				city_state, address.pincode, address.country]

			context.update({
				"email": address.email_id,
				"partner_address": filter_strip_join(address_rows, "\n<br>"),
				"phone": filter_strip_join(cstr(address.phone).split(","), "\n<br>")
			})

		return context

