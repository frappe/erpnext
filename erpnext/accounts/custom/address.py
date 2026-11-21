import frappe
from frappe import _
from frappe.contacts.doctype.address.address import (
	Address,
	get_address_display,
	get_address_templates,
)
from frappe.desk.search import get_std_fields_list
from frappe.model import get_permitted_fields
from frappe.utils import cint


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
		"""A Company link marks the address as the company's own, so a user who cannot set the flag
		must keep the stored Company links unchanged."""
		company_links = self.get_company_links(self)
		if not company_links:
			return

		if (
			not self.flags.ignore_permissions
			and frappe.session.user != "Administrator"
			and not self.has_permlevel_access_to("is_your_company_address", permission_type="write")
		):
			stored_links = set() if self.is_new() else self.get_company_links(self.get_latest())
			if company_links != stored_links:
				frappe.throw(
					_("You are not permitted to link an address to a Company"),
					frappe.PermissionError,
					title=_("Not Permitted"),
				)

		self.is_your_company_address = 1

	@staticmethod
	def get_company_links(doc):
		return {link.link_name for link in doc.get("links") or [] if link.link_doctype == "Company"}

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
		customers = frappe.db.get_all(
			"Customer", filters={"customer_primary_address": self.name}, pluck="name"
		)
		for customer in customers:
			frappe.db.set_value(
				"Customer", customer, "primary_address", address_display, update_modified=False
			)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def address_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None = None
):
	if doctype != "Address":
		return []

	filters = frappe._dict(frappe.parse_json(filters) or {})
	company_address = filters.pop("is_your_company_address", None)
	if company_address not in (None, 0, 1, "0", "1"):
		frappe.throw(_("Invalid company address filter"))

	link_filters = {"parenttype": "Address"}
	for fieldname in ("link_doctype", "link_name"):
		if value := filters.pop(fieldname, None):
			link_filters[fieldname] = value

	permitted_fields = get_permitted_fields("Address")
	fields = [
		fieldname
		for fieldname in get_std_fields_list(frappe.get_meta("Address"), searchfield)
		if fieldname in permitted_fields
	]
	address = frappe.qb.DocType("Address")
	query = frappe.qb.get_query(
		"Address",
		fields=fields,
		filters=filters,
		or_filters=[[fieldname, "like", f"%{txt}%"] for fieldname in fields] if txt else None,
		order_by="idx desc, creation desc, name",
		limit=page_len,
		offset=start,
		ignore_permissions=False,
	).where(address.disabled == 0)
	if len(link_filters) > 1:
		linked_addresses = frappe.qb.get_query("Dynamic Link", fields=["parent"], filters=link_filters)
		query = query.where(address.name.isin(linked_addresses))
	if company_address is not None:
		# Users may select company addresses without being able to read or edit the protected flag.
		query = query.where(address.is_your_company_address == cint(company_address))
	return query.run()


@frappe.whitelist()
def get_shipping_address(company, address=None):
	# `select`, not `read`: Delivery, Maintenance, Purchase and Stock Manager fill in forms that ask
	# for this while holding no Company `read` row. doc= so User Permissions apply to the named company.
	frappe.has_permission("Company", ptype="select", doc=company, throw=True)
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
