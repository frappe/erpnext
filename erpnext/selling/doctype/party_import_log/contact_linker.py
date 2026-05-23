# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Creates or reuses a primary Contact for a party row.

Dedup policy: if any existing Contact has a matching email, reuse it and
add a Dynamic Link to the new party instead of creating a parallel
duplicate. Phones missing on the existing contact are filled in.
"""

import frappe

from erpnext.selling.doctype.customer.customer import make_contact
from erpnext.selling.doctype.party_import_log.schema import CUSTOMER

CONTACT_FIELDS = (
	"primary_first_name",
	"primary_last_name",
	"primary_email",
	"primary_mobile",
	"primary_phone",
)


class ContactLinker:
	"""Creates a fresh Contact or links an existing one matched by email."""

	def __init__(self, party_type: str, name_field: str):
		self.party_type = party_type
		self.name_field = name_field

	def link(self, party_doc, value_map: dict) -> None:
		"""Attach a primary contact to the party, deduplicating by email."""
		if not self._has_contact_data(value_map):
			return
		try:
			contact = self._create_or_link(party_doc, value_map)
			if self.party_type == CUSTOMER and contact:
				party_doc.db_set("customer_primary_contact", contact.name, update_modified=False)
		except Exception as exc:
			frappe.log_error(f"Party Import: contact handling failed for {party_doc.name}: {exc}")

	def _create_or_link(self, party_doc, value_map: dict):
		party_name_value = party_doc.get(self.name_field)
		existing_name = find_contact_by_email(value_map.get("primary_email"))
		if existing_name:
			return self._extend_existing(existing_name, party_doc, value_map)
		return self._create_new(party_doc, party_name_value, value_map)

	def _extend_existing(self, contact_name: str, party_doc, value_map: dict):
		contact = frappe.get_doc("Contact", contact_name)
		self._append_party_link(contact, party_doc)
		self._fill_missing_phones(contact, value_map)
		contact.flags.ignore_permissions = True
		contact.save()
		return contact

	def _append_party_link(self, contact, party_doc) -> None:
		already_linked = any(
			link.link_doctype == self.party_type and link.link_name == party_doc.name
			for link in (contact.links or [])
		)
		if not already_linked:
			contact.append("links", {"link_doctype": self.party_type, "link_name": party_doc.name})

	def _fill_missing_phones(self, contact, value_map: dict) -> None:
		mobile = value_map.get("primary_mobile")
		if mobile and not contact_has_phone(contact, mobile):
			contact.add_phone(mobile, is_primary_mobile_no=True)
		phone = value_map.get("primary_phone")
		if phone and phone != mobile and not contact_has_phone(contact, phone):
			contact.add_phone(phone)

	def _create_new(self, party_doc, party_name_value: str, value_map: dict):
		args = frappe._dict(
			{
				"doctype": self.party_type,
				"name": party_doc.name,
				self.name_field: party_name_value,
				"customer_type": party_doc.get("customer_type"),
				"supplier_type": party_doc.get("supplier_type"),
				"first_name": value_map.get("primary_first_name"),
				"last_name": value_map.get("primary_last_name"),
				"email_id": value_map.get("primary_email"),
				"mobile_no": value_map.get("primary_mobile"),
				"flags": {"ignore_permissions": True},
			}
		)
		contact = make_contact(args, is_primary_contact=1)
		phone = value_map.get("primary_phone")
		if phone and phone != value_map.get("primary_mobile"):
			contact.add_phone(phone)
			contact.save(ignore_permissions=True)
		return contact

	def _has_contact_data(self, value_map: dict) -> bool:
		return any(value_map.get(field) for field in CONTACT_FIELDS)


def find_contact_by_email(email: str | None) -> str | None:
	"""Return the name of an existing Contact whose emails include `email`, or None."""
	if not email:
		return None
	cleaned = email.strip()
	if not cleaned:
		return None
	contact_email = frappe.qb.DocType("Contact Email")
	rows = (
		frappe.qb.from_(contact_email)
		.select(contact_email.parent)
		.where(contact_email.email_id.like(cleaned))
		.orderby(contact_email.creation)
		.limit(1)
	).run()
	return rows[0][0] if rows else None


def contact_has_phone(contact, phone: str) -> bool:
	"""True if the contact already has a phone number matching `phone`."""
	if not phone:
		return False
	target = phone.strip()
	return any((p.phone or "").strip() == target for p in (contact.phone_nos or []))
