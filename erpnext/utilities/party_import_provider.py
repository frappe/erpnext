# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
"""Imports a Customer or Supplier together with its Contacts and Addresses."""

from collections import Counter

import frappe
from frappe import _
from frappe.core.doctype.data_import.import_provider import ImportProvider
from frappe.core.doctype.data_import.importer import INSERT, UPDATE

from erpnext.selling.doctype.customer.customer import parse_full_name

# Contact details come from the Contact rows. Importing them on the party too would make
# the party create a second contact from them on insert.
CONTACT_FIELDS = ("mobile_no", "email_id", "first_name", "last_name")


class PartyImportProvider(ImportProvider):
	def get_import_fields(self) -> dict:
		"""The party's fields and child tables, plus Contact and Address as extra child tables."""
		schema = {
			"fields": [
				df for df in _doctype_docfields(self.doctype) if df["fieldname"] not in CONTACT_FIELDS
			],
			"child_tables": [
				*_doctype_child_tables(self.doctype),
				{
					"fieldname": "contacts",
					"label": _("Contact"),
					"fields": _contact_docfields(),
				},
				{
					"fieldname": "addresses",
					"label": _("Address"),
					"fields": _doctype_docfields("Address"),
				},
			],
		}
		_add_plain_headers(schema, ("contacts", "addresses"))
		return schema

	def import_row(self, importer, doc):
		"""Persist the party per Import Type, then create linked Contacts/Addresses."""
		contact_rows = doc.pop("contacts", None) or []
		address_rows = doc.pop("addresses", None) or []
		has_child_rows = bool(contact_rows or address_rows)
		party, import_action = self._persist_party(importer, doc, has_child_rows)

		# A new party has no linked records yet, so only look for existing ones on updates.
		find_existing = importer.import_type != INSERT
		self._create_contacts(party, contact_rows, find_existing)
		self._create_addresses(party, address_rows, find_existing)
		return party, import_action

	def _field(self, name):
		"""The party's own fieldname, e.g. ``customer_name`` or ``supplier_name``."""
		return f"{frappe.scrub(self.doctype)}_{name}"

	def _persist_party(self, importer, doc, has_child_rows):
		if importer.import_type == INSERT:
			return importer.insert_record(doc), None

		if importer.import_type == UPDATE:
			# A row may only add contacts or addresses, without changing the party.
			return importer.update_record(doc, raise_if_no_changes=not has_child_rows), None

		return importer.upsert_record(doc)

	def _create_contacts(self, party, rows, find_existing):
		primary = None
		for row in rows:
			row = dict(row)
			email = row.pop("email_id", None)
			mobile = row.pop("mobile_no", None)
			flagged = frappe.utils.cint(row.pop("is_primary_contact", 0))

			# Reuse a contact already linked to this party so re-imports don't duplicate it.
			match = {"email_id": email} if email else {"mobile_no": mobile} if mobile else None
			existing = find_existing and match and _find_linked("Contact", party.doctype, party.name, match)
			if existing:
				contact = frappe.get_doc("Contact", existing)
			else:
				names = self._resolve_contact_names(party, row)
				contact_values = {k: v for k, v in {**row, **names}.items() if v not in (None, "")}
				contact = frappe.get_doc(
					{
						"doctype": "Contact",
						**contact_values,
						"links": [{"link_doctype": party.doctype, "link_name": party.name}],
					}
				)
				if email:
					contact.add_email(email, is_primary=True)
				if mobile:
					contact.add_phone(mobile, is_primary_mobile_no=True)
				contact.insert()
			# First created contact is the default primary; an explicit flag overrides.
			if flagged or primary is None:
				primary = contact
		if primary:
			# Unlike addresses, saving a contact doesn't clear the party's other primary contact.
			_demote_other_primary_contacts(party.doctype, party.name, primary.name)
			frappe.db.set_value("Contact", primary.name, "is_primary_contact", 1)
			party.db_set(self._field("primary_contact"), primary.name)
			party.db_set("mobile_no", primary.mobile_no)
			party.db_set("email_id", primary.email_id)

	def _resolve_contact_names(self, party, row):
		"""Contact names from the row, falling back to the party's name."""
		names = {
			field: row.pop(field, None)
			for field in ("first_name", "middle_name", "last_name", "company_name")
		}
		party_name = party.get(self._field("name"))
		if party.get(self._field("type")) != "Individual":
			names["company_name"] = names["company_name"] or party_name
			return names

		names["first_name"] = names["first_name"] or party.get("first_name")
		names["last_name"] = names["last_name"] or party.get("last_name")
		if not names["first_name"]:
			first, middle, last = parse_full_name(party_name)
			names["first_name"] = first
			names["middle_name"] = names["middle_name"] or middle
			names["last_name"] = names["last_name"] or last
		return names

	def _create_addresses(self, party, rows, find_existing):
		from frappe.contacts.doctype.address.address import get_address_display

		primary = None
		for row in rows:
			row = dict(row)
			flagged = frappe.utils.cint(row.pop("is_primary_address", 0))
			existing = find_existing and _find_linked(
				"Address",
				party.doctype,
				party.name,
				{"address_line1": row.get("address_line1"), "city": row.get("city")},
			)
			if existing:
				address = frappe.get_doc("Address", existing)
			else:
				row["address_type"] = row.get("address_type") or "Billing"
				row["address_title"] = row.get("address_title") or party.get(self._field("name"))
				address = frappe.get_doc(
					{
						"doctype": "Address",
						**{k: v for k, v in row.items() if v not in (None, "")},
						"links": [{"link_doctype": party.doctype, "link_name": party.name}],
					}
				)
				address.insert()
			# First created address is the default primary; an explicit flag overrides.
			if flagged or primary is None:
				primary = address
		if primary:
			# save() clears the party's other primary address; set_value would leave two.
			primary.is_primary_address = 1
			primary.save()
			party.db_set(self._field("primary_address"), primary.name)
			party.db_set("primary_address", get_address_display(primary.name))


def _find_linked(doctype: str, link_doctype: str, link_name: str, filters: dict) -> str | None:
	"""Name of a ``doctype`` record linked to the party that matches ``filters``."""
	return frappe.db.get_value(
		doctype,
		[
			["Dynamic Link", "link_doctype", "=", link_doctype],
			["Dynamic Link", "link_name", "=", link_name],
			*[[field, "=", value] for field, value in filters.items()],
		],
	)


def _demote_other_primary_contacts(link_doctype: str, link_name: str, keep: str) -> None:
	"""Clear ``is_primary_contact`` on the party's other Contacts (keeps ``keep``)."""
	linked = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": link_doctype, "link_name": link_name, "parenttype": "Contact"},
		pluck="parent",
	)
	for other in frappe.get_all(
		"Contact", filters={"name": ["in", linked or [""]], "is_primary_contact": 1}, pluck="name"
	):
		if other != keep:
			frappe.db.set_value("Contact", other, "is_primary_contact", 0)


def _doctype_docfields(doctype: str) -> list[dict]:
	"""Non-table importable fields of ``doctype`` as complete docfield dicts."""
	from frappe.model import display_fieldtypes, no_value_fields

	fields = []
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype in no_value_fields or df.fieldtype in display_fieldtypes:
			continue
		if df.fieldname in ("lft", "rgt") or df.get("is_virtual"):
			continue
		fields.append(df.as_dict())
	return fields


def _contact_docfields() -> list[dict]:
	"""Contact's fields, with email and mobile ticked in the template by default.

	A Contact keeps these in child tables and clears the fields on save, so the Contact DocType
	can't flag them; this import turns them into those rows, so here they are worth a column."""
	fields = _doctype_docfields("Contact")
	for df in fields:
		if df["fieldname"] in ("email_id", "mobile_no"):
			df["in_import_template"] = 1
	return fields


def _add_plain_headers(schema: dict, tables: tuple) -> None:
	"""Let a plain header like "Address Line 1" match a field in ``tables``, as long as no
	other field in the import uses the same header."""
	parent_headers = {header for df in schema["fields"] for header in _plain_headers(df)}
	counts = Counter(
		header for table in schema["child_tables"] for df in table["fields"] for header in _plain_headers(df)
	)
	for table in schema["child_tables"]:
		if table["fieldname"] in tables:
			for df in table["fields"]:
				df["import_labels"] = [
					header
					for header in _plain_headers(df)
					if counts[header] == 1 and header not in parent_headers
				]


def _plain_headers(df: dict) -> set[str]:
	return {header for header in (df.get("label"), _(df.get("label") or ""), df["fieldname"]) if header}


def _doctype_child_tables(doctype: str) -> list[dict]:
	"""``doctype``'s own child tables as schema groups (fieldname, label, fields)."""
	return [
		{
			"fieldname": tf.fieldname,
			"label": _(tf.label or tf.fieldname),
			"fields": _doctype_docfields(tf.options),
		}
		for tf in frappe.get_meta(doctype).get_table_fields()
	]
