# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import cstr, filter_strip_join, flt
from frappe.website.website_generator import WebsiteGenerator

from erpnext.setup.doctype.target_detail.target_detail import validate_targets


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
		pass

	def validate(self):
		validate_targets(self.get("targets"))
		if not self.route:
			self.route = "partners/" + self.scrub(self.partner_name)
		super().validate()
		self.validate_route()
		self.validate_targets()
		if self.partner_website:
			from urllib.parse import urlsplit, urlunsplit

			# scrub http
			parts = urlsplit(self.partner_website)
			if not parts.netloc and parts.path:
				parts = parts._replace(netloc=parts.path, path="")
			if not parts.scheme or parts.scheme == "http":
				parts = parts._replace(scheme="https")

			self.partner_website = urlunsplit(parts)

	def validate_route(self):
		if frappe.db.exists("Sales Partner", {"route": self.route, "name": ["!=", self.name]}):
			frappe.throw(
				_("Route {0} is already used by another Sales Partner. Please choose another route.").format(
					frappe.bold(self.route)
				)
			)

	def validate_targets(self):
		for target in self.get("targets") or []:
			if not flt(target.target_qty) and not flt(target.target_amount):
				frappe.throw(
					_("Row #{0}: Either Target Qty or Target Amount is mandatory").format(target.idx)
				)
			if flt(target.target_qty) < 0 or flt(target.target_amount) < 0:
				frappe.throw(
					_("Row #{0}: Target Qty and Target Amount cannot be negative").format(target.idx)
				)

	def get_context(self, context):
		address_names = frappe.db.get_all(
			"Dynamic Link",
			filters={"link_doctype": "Sales Partner", "link_name": self.name, "parenttype": "Address"},
			pluck="parent",
		)

		addresses = []
		for address_name in address_names:
			address_doc = frappe.get_doc("Address", address_name)
			city_state = ", ".join([item for item in [address_doc.city, address_doc.state] if item])
			address_rows = [
				address_doc.address_line1,
				address_doc.address_line2,
				city_state,
				address_doc.pincode,
				address_doc.country,
			]
			addresses.append(
				{
					"email": address_doc.email_id,
					"partner_address": filter_strip_join(address_rows, "\n"),
					"phone": filter_strip_join(cstr(address_doc.phone).split(","), "\n"),
				}
			)

		context["addresses"] = addresses
		return context


@frappe.whitelist()
def get_commission_rate(sales_partner: str) -> float:
	partner = frappe.get_doc("Sales Partner", sales_partner)
	partner.check_permission("select")
	return flt(partner.commission_rate)
