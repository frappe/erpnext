# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
"""Data Import provider for Customer.

Imports a Customer together with its Contact and Address records. In the schema Contact and
Address are separate doctypes linked to the Customer via a Dynamic Link; the provider exposes
them as child tables in the import and wires up the links + primary flags in ``import_row``.
"""

import frappe
from frappe import _
from frappe.core.doctype.data_import.import_provider import ImportProvider
from frappe.core.doctype.data_import.importer import INSERT, UPDATE

from .mapper import parse_full_name


class CustomerImportProvider(ImportProvider):
	def get_import_fields(self) -> dict:
		"""Field schema for the picker: a Customer with its own child tables, plus Contact and
		Address (linked doctypes exposed as extra child tables).

		For Customer the columns ARE those doctypes' fields, so we read complete docfields from
		meta. (This is the provider's choice — Data Import itself never reads meta here.)
		"""
		return {
			"fields": _doctype_docfields("Customer"),
			"child_tables": [
				*_doctype_child_tables("Customer"),
				{
					"fieldname": "contacts",
					"label": _("Contact"),
					"fields": _contact_docfields(),
				},
				{
					"fieldname": "addresses",
					"label": _("Address"),
					"fields": _doctype_docfields("Address", prefer_plain_label=True),
				},
			],
		}

	def validate(self, import_file) -> list[dict]:
		"""Business checks on top of the framework's basic Select/Link/Date validation."""
		warnings = []
		for payload in import_file.get_payloads_for_import():
			doc = payload.doc
			row = payload.rows[0].row_number if payload.rows else None
			for contact in doc.get("contacts") or []:
				# A Contact is only useful with a way to reach it — warn when both are missing.
				if not (contact.get("email_id") or contact.get("mobile_no")):
					missing = [
						label
						for field, label in (("email_id", _("Email")), ("mobile_no", _("Mobile No")))
						if not contact.get(field)
					]
					warnings.append(
						{
							"row": row,
							"message": _("Contact in row {0} is missing {1}").format(row, ", ".join(missing)),
						}
					)
			for address in doc.get("addresses") or []:
				if not address.get("address_line1"):
					continue
				missing = [
					label
					for field, label in (("city", _("City")), ("country", _("Country")))
					if not address.get(field)
				]
				if missing:
					warnings.append(
						{
							"row": row,
							"message": _("Address in row {0} is missing {1}").format(row, ", ".join(missing)),
						}
					)
		return warnings

	def import_row(self, importer, doc):
		"""Persist Customer per Import Type, then create linked Contacts/Addresses."""
		contact_rows = doc.pop("contacts", None) or []
		address_rows = doc.pop("addresses", None) or []
		has_child_rows = bool(contact_rows or address_rows)
		customer, import_action = self._persist_customer(importer, doc, has_child_rows)

		self._create_contacts(customer, contact_rows)
		self._create_addresses(customer, address_rows)
		return customer, import_action

	def _persist_customer(self, importer, doc, has_child_rows):
		"""Use the core Importer paths so provider imports honor Insert/Update/Upsert semantics."""
		if importer.import_type == INSERT:
			return importer.insert_record(doc), None

		if importer.import_type == UPDATE:
			# Allow child-only updates (e.g. add Contact/Address) without failing on unchanged Customer fields.
			return importer.update_record(doc, raise_if_no_changes=not has_child_rows), None

		return importer.upsert_record(doc)

	def _create_contacts(self, customer, rows):
		primary = None
		for row in rows:
			row = dict(row)
			email = row.pop("email_id", None)
			mobile = row.pop("mobile_no", None)
			flagged = frappe.utils.cint(row.pop("is_primary_contact", 0))

			first_name, last_name, company_name = self._resolve_contact_names(customer, row)

			contact_values = {k: v for k, v in row.items() if v not in (None, "")}
			if first_name:
				contact_values["first_name"] = first_name
			if last_name:
				contact_values["last_name"] = last_name
			if company_name:
				contact_values["company_name"] = company_name

			contact = frappe.get_doc(
				{
					"doctype": "Contact",
					**contact_values,
					"links": [{"link_doctype": "Customer", "link_name": customer.name}],
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
			# Contact has no cross-contact auto-demotion (unlike Address's
			# validate_preferred_address), so explicitly demote any other primary Contact on
			# this party first — otherwise get_default_contact may return a Contact other
			# than customer_primary_contact.
			_demote_other_primary_contacts("Customer", customer.name, primary.name)
			frappe.db.set_value("Contact", primary.name, "is_primary_contact", 1)
			customer.db_set("customer_primary_contact", primary.name)
			customer.db_set("mobile_no", primary.mobile_no)
			customer.db_set("email_id", primary.email_id)

	def _resolve_contact_names(self, customer, row):
		"""Resolve Contact names from row data and fall back to Customer data when needed."""
		first_name = row.pop("first_name", None)
		last_name = row.pop("last_name", None)
		company_name = row.pop("company_name", None)
		customer_get = getattr(customer, "get", None)

		def get_customer_value(fieldname):
			if callable(customer_get):
				return customer_get(fieldname)
			return getattr(customer, fieldname, None)

		if customer.customer_type == "Individual":
			first_name = first_name or get_customer_value("first_name")
			last_name = last_name or get_customer_value("last_name")
			if not first_name and customer.customer_name:
				parsed_first, _, parsed_last = parse_full_name(customer.customer_name)
				first_name = parsed_first
				last_name = last_name or parsed_last

		return first_name, last_name, company_name

	def _create_addresses(self, customer, rows):
		from frappe.contacts.doctype.address.address import get_address_display

		primary = None
		for row in rows:
			row = dict(row)
			flagged = frappe.utils.cint(row.pop("is_primary_address", 0))
			if not row.get("address_line1"):
				continue
			row["address_type"] = row.get("address_type") or "Billing"
			row["address_title"] = row.get("address_title") or customer.customer_name
			address = frappe.get_doc(
				{
					"doctype": "Address",
					**{k: v for k, v in row.items() if v not in (None, "")},
					"links": [{"link_doctype": "Customer", "link_name": customer.name}],
				}
			)
			address.insert()
			# First created address is the default primary; an explicit flag overrides.
			# (Must not key off the loop index — skipped rows would leave no primary.)
			if flagged or primary is None:
				primary = address
		if primary:
			# Save (not db.set_value) so Address.validate_preferred_address() clears any
			# existing primary address on the party — a raw write would leave two flagged.
			primary.is_primary_address = 1
			primary.save()
			customer.db_set("customer_primary_address", primary.name)
			customer.db_set("primary_address", get_address_display(primary.name))


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


def _doctype_docfields(doctype: str, prefer_plain_label: bool = False) -> list[dict]:
	"""Non-table importable fields of ``doctype`` as complete docfield dicts."""
	from frappe.model import display_fieldtypes, no_value_fields

	fields = []
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype in no_value_fields or df.fieldtype in display_fieldtypes:
			continue
		if df.fieldname in ("lft", "rgt") or df.get("is_virtual"):
			continue
		field_dict = df.as_dict()
		if prefer_plain_label:
			field_dict["prefer_plain_label"] = 1
		fields.append(field_dict)
	return fields


def _contact_docfields() -> list[dict]:
	"""Contact fields with plain-label and import-header aliases for common CSV headers."""
	fields = _doctype_docfields("Contact", prefer_plain_label=True)
	for field in fields:
		if field.get("fieldname") == "email_id":
			field["import_labels"] = ["Email ID"]
	return fields


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
