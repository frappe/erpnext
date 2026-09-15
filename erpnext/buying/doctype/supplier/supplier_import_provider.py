# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
"""Data Import provider for Supplier.

Imports a Supplier together with Contact and Address records. Contact and Address are
separate doctypes linked through Dynamic Link rows; the provider exposes them as child
sections in import schema and creates linked records during row import.
"""

import frappe
from frappe import _
from frappe.core.doctype.data_import.import_provider import ImportProvider
from frappe.core.doctype.data_import.importer import INSERT, UPDATE

from erpnext.selling.doctype.customer.mapper import parse_full_name


class SupplierImportProvider(ImportProvider):
	def get_import_fields(self) -> dict:
		return {
			"fields": _doctype_docfields("Supplier"),
			"child_tables": [
				*_doctype_child_tables("Supplier"),
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
		warnings = []
		for payload in import_file.get_payloads_for_import():
			doc = payload.doc
			row = payload.rows[0].row_number if payload.rows else None

			for contact in doc.get("contacts") or []:
				# Keep parity with current Customer provider behavior: require at least one contact method.
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
		contact_rows = doc.pop("contacts", None) or []
		address_rows = doc.pop("addresses", None) or []
		has_child_rows = bool(contact_rows or address_rows)
		supplier, import_action = self._persist_supplier(importer, doc, has_child_rows)

		self._create_contacts(supplier, contact_rows)
		self._create_addresses(supplier, address_rows)
		return supplier, import_action

	def _persist_supplier(self, importer, doc, has_child_rows):
		if importer.import_type == INSERT:
			return importer.insert_record(doc), None

		if importer.import_type == UPDATE:
			return importer.update_record(doc, raise_if_no_changes=not has_child_rows), None

		return importer.upsert_record(doc)

	def _create_contacts(self, supplier, rows):
		primary = None
		for row in rows:
			row = dict(row)
			email = row.pop("email_id", None)
			mobile = row.pop("mobile_no", None)
			flagged = frappe.utils.cint(row.pop("is_primary_contact", 0))

			first_name, last_name, company_name = self._resolve_contact_names(supplier, row)

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
					"links": [{"link_doctype": "Supplier", "link_name": supplier.name}],
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
			# than supplier_primary_contact.
			_demote_other_primary_contacts("Supplier", supplier.name, primary.name)
			frappe.db.set_value("Contact", primary.name, "is_primary_contact", 1)
			supplier.db_set("supplier_primary_contact", primary.name)
			supplier.db_set("mobile_no", primary.mobile_no)
			supplier.db_set("email_id", primary.email_id)

	def _resolve_contact_names(self, supplier, row):
		first_name = row.pop("first_name", None)
		last_name = row.pop("last_name", None)
		company_name = row.pop("company_name", None)
		supplier_get = getattr(supplier, "get", None)

		def get_supplier_value(fieldname):
			if callable(supplier_get):
				return supplier_get(fieldname)
			return getattr(supplier, fieldname, None)

		if supplier.supplier_type == "Individual":
			first_name = first_name or get_supplier_value("first_name")
			last_name = last_name or get_supplier_value("last_name")
			if not first_name and supplier.supplier_name:
				parsed_first, _, parsed_last = parse_full_name(supplier.supplier_name)
				first_name = parsed_first
				last_name = last_name or parsed_last

		return first_name, last_name, company_name

	def _create_addresses(self, supplier, rows):
		from frappe.contacts.doctype.address.address import get_address_display

		primary = None
		for row in rows:
			row = dict(row)
			flagged = frappe.utils.cint(row.pop("is_primary_address", 0))
			if not row.get("address_line1"):
				continue
			row["address_type"] = row.get("address_type") or "Billing"
			row["address_title"] = row.get("address_title") or supplier.supplier_name
			address = frappe.get_doc(
				{
					"doctype": "Address",
					**{k: v for k, v in row.items() if v not in (None, "")},
					"links": [{"link_doctype": "Supplier", "link_name": supplier.name}],
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
			supplier.db_set("supplier_primary_address", primary.name)
			supplier.db_set("primary_address", get_address_display(primary.name))


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
	fields = _doctype_docfields("Contact", prefer_plain_label=True)
	for field in fields:
		if field.get("fieldname") == "email_id":
			field["import_labels"] = ["Email ID"]
	return fields


def _doctype_child_tables(doctype: str) -> list[dict]:
	return [
		{
			"fieldname": tf.fieldname,
			"label": _(tf.label or tf.fieldname),
			"fields": _doctype_docfields(tf.options),
		}
		for tf in frappe.get_meta(doctype).get_table_fields()
	]
