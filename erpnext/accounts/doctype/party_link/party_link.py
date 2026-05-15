# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document


class PartyLink(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		primary_party: DF.DynamicLink | None
		primary_role: DF.Link
		secondary_party: DF.DynamicLink | None
		secondary_role: DF.Link | None
	# end: auto-generated types

	def on_trash(self):
		if self.primary_role == "Customer":
			customer, supplier = self.primary_party, self.secondary_party
		else:
			customer, supplier = self.secondary_party, self.primary_party

		if customer and frappe.db.exists("Customer", customer):
			frappe.db.set_value("Customer", customer, "linked_supplier", None)

		if supplier and frappe.db.exists("Supplier", supplier):
			frappe.db.set_value("Supplier", supplier, "linked_customer", None)

	def validate(self):
		if self.primary_role not in ["Customer", "Supplier"]:
			frappe.throw(
				_(
					"Allowed primary roles are 'Customer' and 'Supplier'. Please select one of these roles only."
				),
				title=_("Invalid Primary Role"),
			)

		existing_party_link = frappe.get_all(
			"Party Link",
			{"primary_party": self.primary_party, "secondary_party": self.secondary_party},
			pluck="primary_role",
		)
		if existing_party_link:
			frappe.throw(
				_("{} {} is already linked with {} {}").format(
					self.primary_role,
					bold(self.primary_party),
					self.secondary_role,
					bold(self.secondary_party),
				)
			)

		existing_party_link = frappe.get_all(
			"Party Link", {"primary_party": self.secondary_party}, pluck="primary_role"
		)
		if existing_party_link:
			frappe.throw(
				_("{} {} is already linked with another {}").format(
					self.secondary_role, self.secondary_party, existing_party_link[0]
				)
			)

		existing_party_link = frappe.get_all(
			"Party Link", {"secondary_party": self.primary_party}, pluck="primary_role"
		)
		if existing_party_link:
			frappe.throw(
				_("{} {} is already linked with another {}").format(
					self.primary_role, self.primary_party, existing_party_link[0]
				)
			)


@frappe.whitelist()
def create_party_link(
	primary_role: str,
	primary_party: str,
	secondary_party: str,
	copy_address_and_contacts: bool = False,
):
	party_link = frappe.new_doc("Party Link")
	party_link.primary_role = primary_role
	party_link.primary_party = primary_party
	party_link.secondary_role = "Customer" if primary_role == "Supplier" else "Supplier"
	party_link.secondary_party = secondary_party

	party_link.save()

	if copy_address_and_contacts:
		_copy_address_and_contacts(party_link)

	return party_link


def _copy_address_and_contacts(party_link: "PartyLink"):
	"""Copy Dynamic Link rows from primary party's Addresses and Contacts to the secondary party."""
	source_party = party_link.primary_party
	source_role = party_link.primary_role
	target_party = party_link.secondary_party
	target_role = party_link.secondary_role

	for doctype in ("Address", "Contact"):
		dl = frappe.qb.DocType("Dynamic Link")
		linked_docs = (
			frappe.qb.from_(dl)
			.select(dl.parent)
			.where(
				(dl.link_doctype == source_role) & (dl.link_name == source_party) & (dl.parenttype == doctype)
			)
			.run(pluck="parent")
		)

		for doc_name in linked_docs:
			already_linked = frappe.db.exists(
				"Dynamic Link",
				{
					"parenttype": doctype,
					"parent": doc_name,
					"link_doctype": target_role,
					"link_name": target_party,
				},
			)
			if already_linked:
				continue

			if not frappe.has_permission(doctype, "write", doc=doc_name):
				continue

			doc = frappe.get_doc(doctype, doc_name)
			doc.append(
				"links",
				{
					"link_doctype": target_role,
					"link_name": target_party,
				},
			)
			doc.save()


def _find_party_link(party_type: str, party: str) -> "dict | None":
	PL = frappe.qb.DocType("Party Link")
	result = (
		frappe.qb.from_(PL)
		.select(PL.name, PL.primary_role, PL.primary_party, PL.secondary_role, PL.secondary_party)
		.where(
			((PL.primary_role == party_type) & (PL.primary_party == party))
			| ((PL.secondary_role == party_type) & (PL.secondary_party == party))
		)
		.run(as_dict=True)
	)
	return result[0] if result else None


@frappe.whitelist()
def create_and_link_party(
	primary_role: str,
	primary_party: str,
	new_party_name: str,
	new_party_type: str,
	new_party_group: str | None = None,
):
	if primary_role not in ("Customer", "Supplier"):
		frappe.throw(_("primary_role must be 'Customer' or 'Supplier'"))

	if not frappe.db.exists(primary_role, primary_party):
		frappe.throw(_("{} {} does not exist").format(primary_role, frappe.bold(primary_party)))

	frappe.has_permission(primary_role, "write", doc=primary_party, throw=True)

	secondary_role = "Customer" if primary_role == "Supplier" else "Supplier"
	role_lower = secondary_role.lower()

	sp = "create_and_link_party"
	frappe.db.savepoint(sp)
	try:
		new_doc = frappe.new_doc(secondary_role)
		new_doc.set(f"{role_lower}_name", new_party_name)
		new_doc.set(f"{role_lower}_type", new_party_type)
		if new_party_group:
			new_doc.set(f"{role_lower}_group", new_party_group)
		new_doc.insert()

		return create_party_link(
			primary_role=primary_role,
			primary_party=primary_party,
			secondary_party=new_doc.name,
			copy_address_and_contacts=True,
		)
	except Exception:
		frappe.db.rollback(save_point=sp)
		raise


@frappe.whitelist()
def remove_party_link(party_type: str, party: str):
	frappe.has_permission("Party Link", "delete", throw=True)

	link = _find_party_link(party_type, party)
	if not link:
		frappe.throw(_("No Party Link found for {} {}").format(party_type, frappe.bold(party)))

	frappe.delete_doc("Party Link", link.name)
