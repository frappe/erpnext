# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, filter_strip_join
from frappe.website.website_generator import WebsiteGenerator
from frappe.geo.address_and_contact import load_address_and_contact

class SalesPartner(WebsiteGenerator):
	website = frappe._dict(
		page_title_field = "partner_name",
		condition_field = "show_in_website",
		template = "templates/generators/sales_partner.html"
	)

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self, "sales_partner")

	def autoname(self):
		self.name = self.partner_name

	def validate(self):
		if not self.route:
			self.route = "partners/" + self.scrub(self.partner_name)
		super(SalesPartner, self).validate()
		if self.partner_website and not self.partner_website.startswith("http"):
			self.partner_website = "http://" + self.partner_website

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
