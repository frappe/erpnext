# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import cstr, filter_strip_join
from frappe.website.website_generator import WebsiteGenerator


class SalesPartner(WebsiteGenerator):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.target_detail.target_detail import TargetDetail

		commission_rate: DF.Float
		description: DF.TextEditor | None
		introduction: DF.Text | None
		logo: DF.Attach | None
		partner_name: DF.Data
		partner_type: DF.Link | None
		partner_website: DF.Data | None
		referral_code: DF.Data | None
		route: DF.Data | None
		show_in_website: DF.Check
		targets: DF.Table[TargetDetail]
		territory: DF.Link
	# end: auto-generated types

	website = frappe._dict(
		page_title_field="partner_name",
		condition_field="show_in_website",
		template="templates/generators/sales_partner.html",
	)

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)

	def autoname(self):
		self.name = self.partner_name

	def validate(self):
		if not self.route:
			self.route = "partners/" + self.scrub(self.partner_name)
		super().validate()
		if self.partner_website and not self.partner_website.startswith("http"):
			self.partner_website = "http://" + self.partner_website

	def get_context(self, context):
		address = frappe.db.get_value(
			"Address", {"sales_partner": self.name, "is_primary_address": 1}, "*", as_dict=True
		)
		if address:
			city_state = ", ".join(filter(None, [address.city, address.state]))
			address_rows = [
				address.address_line1,
				address.address_line2,
				city_state,
				address.pincode,
				address.country,
			]

			context.update(
				{
					"email": address.email_id,
					"partner_address": filter_strip_join(address_rows, "\n<br>"),
					"phone": filter_strip_join(cstr(address.phone).split(","), "\n<br>"),
				}
			)

		return context
