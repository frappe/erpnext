import frappe
from frappe import _
from frappe.contacts.doctype.address.address import (
	Address,
	get_address_display,
	get_address_templates,
)


class ERPNextAddress(Address):
	def validate(self):
		self.validate_reference()
		self.update_company_address()

		if hasattr(super(), "validate"):
			super().validate()

	def link_address(self):
		"""Link address based on owner"""
		if self.get("is_your_company_address"):
			return

		return super().link_address()

	def update_company_address(self):
		for link in self.get("links"):
			if link.link_doctype == "Company":
				self.is_your_company_address = 1

	def validate_reference(self):
		if self.get("is_your_company_address") and not [
			row for row in self.links if row.link_doctype == "Company"
		]:
			frappe.throw(
				_(
					"Address needs to be linked to a Company. Please add a row for Company in the Links table."
				),
				title=_("Company Not Linked"),
			)

	def on_update(self):
		"""
		After Address is updated, update the related 'Primary Address' on Customer.
		"""

		if hasattr(super(), "on_update"):
			super().on_update()

		address_display = get_address_display(self.as_dict())
		filters = {"customer_primary_address": self.name}
		customers = frappe.db.get_all("Customer", filters=filters, as_list=True)
		for customer_name in customers:
			frappe.db.set_value("Customer", customer_name[0], "primary_address", address_display)


@frappe.whitelist()
def get_shipping_address(company: str, address: str | None = None):
	# `company` is caller supplied and this returns that company's own registered address with every
	# field. `select` rather than `read` on Company: Delivery, Maintenance, Purchase Manager and
	# Stock Manager all fill in transactions that ask for this while holding no Company `read` row.
	frappe.has_permission("Company", ptype="select", throw=True)

	# and scope it to the caller's own Company restrictions, which costs nobody who has none
	from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies

	allowed_companies = get_allowed_companies(frappe.session.user, "Address")
	if allowed_companies and company not in allowed_companies:
		frappe.throw(_("Not permitted for {0}").format(company), frappe.PermissionError)

	filters = [
		["Dynamic Link", "link_doctype", "=", "Company"],
		["Dynamic Link", "link_name", "=", company],
		["Address", "is_your_company_address", "=", 1],
	]
	fields = ["*"]
	if address and frappe.db.get_value("Dynamic Link", {"parent": address, "link_name": company}):
		filters.append(["Address", "name", "=", address])
	if not address:
		filters.append(["Address", "is_shipping_address", "=", 1])

	address = frappe.get_all("Address", filters=filters, fields=fields) or {}

	if address:
		address_as_dict = address[0]
		name, address_template = get_address_templates(address_as_dict)
		return address_as_dict.get("name"), frappe.render_template(
			address_template, address_as_dict, restrict_globals=True
		)
