# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Creates or updates a Customer / Supplier from a single import row.

This is the runtime workhorse called once per row by the background job.
Responsibility is split two ways here, plus a sibling
:mod:`contact_linker` module:

* :class:`PartyCreator` — turns a raw CSV row into a saved party document.
* :class:`AddressCreator` — billing + shipping addresses, with titles
  disambiguated so users can tell them apart in the address list view.
"""

import frappe
from frappe.utils import flt

from erpnext.selling.doctype.customer.customer import make_address
from erpnext.selling.doctype.party_import_log.contact_linker import ContactLinker
from erpnext.selling.doctype.party_import_log.dependency_resolver import (
	DependencyResolver,
)
from erpnext.selling.doctype.party_import_log.schema import (
	CUSTOMER,
	VIRTUAL_FIELD_KEYS,
	dependency_fields_for,
	group_field_for,
	name_field_for,
)

CORE_FIELDS = (
	"customer_type",
	"supplier_type",
	"tax_id",
	"default_currency",
	"default_price_list",
	"payment_terms",
	"language",
	"website",
	"industry",
	"market_segment",
	"country",
)

UPDATABLE_FIELDS = (
	"tax_id",
	"default_currency",
	"default_price_list",
	"payment_terms",
	"language",
	"website",
	"industry",
	"market_segment",
	"country",
)

# Fields in CORE_FIELDS or with their own _apply_* method — not custom fields.
_STANDARD_PARTY_FIELDS = frozenset(CORE_FIELDS) | {"account_manager"}

DEFAULT_CUSTOMER_TYPE = "Company"


class PartyCreator:
	"""Creates or updates one party per call, including its contacts/addresses."""

	def __init__(
		self,
		party_type: str,
		mappings: dict[str, str],
		resolver: DependencyResolver,
	):
		self.party_type = party_type
		self.mappings = mappings
		self.resolver = resolver
		self.dependency_fields = dependency_fields_for(party_type)
		self.name_field = name_field_for(party_type)
		self.group_field = group_field_for(party_type)
		self.contact_linker = ContactLinker(party_type, self.name_field)
		self.address_creator = AddressCreator(party_type, self.name_field)

	def create(self, row: dict, overrides: dict | None = None) -> str:
		"""Insert a new party + addresses + contact. Returns the party name."""
		value_map = self.row_to_value_map(row, overrides=overrides)
		party_doc = self._build_party_doc(value_map)
		self._insert_party(party_doc)
		self.contact_linker.link(party_doc, value_map)
		self.address_creator.create_all(party_doc, value_map)
		self._save_notes(party_doc, value_map)
		return party_doc.name

	def update(self, party_name: str, row: dict, conflict_policy: str, overrides: dict | None = None) -> None:
		"""Apply a row's values to an existing party, honoring the conflict policy."""
		party_doc = frappe.get_doc(self.party_type, party_name)
		value_map = self.row_to_value_map(row, overrides=overrides)
		update_empty_only = conflict_policy == "Update Empty Fields Only"
		self._apply_updatable_fields(party_doc, value_map, update_empty_only)
		self._apply_group_field_update(party_doc, value_map, update_empty_only)
		self._apply_territory_update(party_doc, value_map, update_empty_only)
		self._apply_custom_field_updates(party_doc, value_map, update_empty_only)
		party_doc.flags.ignore_permissions = True
		party_doc.save()

	def row_to_value_map(self, row: dict, overrides: dict | None = None) -> dict:
		"""Translate one CSV row into ``{target_field: resolved_value}``.

		``overrides`` carry user-edited values keyed by target field — they
		bypass dependency resolution (the user has already picked the final
		value via the inline editor) and override anything from the source row.
		"""
		value_map: dict = {}
		for source, target in self.mappings.items():
			if not target:
				continue
			raw = self._raw_value(row, source)
			if raw in (None, ""):
				continue
			if target in self.dependency_fields:
				resolved = self.resolver.resolve(self.dependency_fields[target][0], str(raw).strip())
				if resolved:
					value_map[target] = resolved
			else:
				value_map[target] = raw
		if overrides:
			for target, value in overrides.items():
				if value in (None, ""):
					value_map.pop(target, None)
				else:
					value_map[target] = value
		return value_map

	def _build_party_doc(self, value_map: dict):
		party_doc = frappe.new_doc(self.party_type)
		party_doc.set(self.name_field, value_map.get(self.name_field))
		self._apply_core_fields(party_doc, value_map)
		self._apply_group_and_territory(party_doc, value_map)
		self._apply_account_manager(party_doc, value_map)
		self._apply_credit_limit(party_doc, value_map)
		self._apply_custom_fields(party_doc, value_map)
		self._apply_default_customer_type(party_doc)
		return party_doc

	def _apply_core_fields(self, party_doc, value_map: dict) -> None:
		for field in CORE_FIELDS:
			if value_map.get(field):
				party_doc.set(field, value_map[field])

	def _apply_group_and_territory(self, party_doc, value_map: dict) -> None:
		if value_map.get(self.group_field):
			party_doc.set(self.group_field, value_map[self.group_field])
		if self.party_type == CUSTOMER and value_map.get("territory"):
			party_doc.set("territory", value_map["territory"])

	def _apply_account_manager(self, party_doc, value_map: dict) -> None:
		if self.party_type != CUSTOMER or not value_map.get("account_manager"):
			return
		email = value_map["account_manager"].strip()
		if frappe.db.exists("User", email):
			party_doc.set("account_manager", email)

	def _apply_credit_limit(self, party_doc, value_map: dict) -> None:
		if self.party_type != CUSTOMER or not value_map.get("credit_limit"):
			return
		limit = flt(value_map["credit_limit"])
		company = value_map.get("credit_limit_company") or frappe.defaults.get_user_default("Company")
		if not (company and limit):
			return
		party_doc.append(
			"credit_limits",
			{"company": company, "credit_limit": limit, "bypass_credit_limit_check": 0},
		)

	def _apply_default_customer_type(self, party_doc) -> None:
		if self.party_type == CUSTOMER and not party_doc.customer_type:
			party_doc.customer_type = DEFAULT_CUSTOMER_TYPE

	def _apply_custom_fields(self, party_doc, value_map: dict) -> None:
		"""Set custom fields that are not handled by any other _apply_* method."""
		already_handled = (
			_STANDARD_PARTY_FIELDS | {self.name_field, self.group_field, "territory"} | VIRTUAL_FIELD_KEYS
		)
		for field, value in value_map.items():
			if field not in already_handled:
				party_doc.set(field, value)

	def _apply_custom_field_updates(self, party_doc, value_map: dict, update_empty_only: bool) -> None:
		"""Update custom fields on an existing party, honoring the conflict policy."""
		already_handled = (
			frozenset(UPDATABLE_FIELDS)
			| {self.name_field, self.group_field, "territory"}
			| VIRTUAL_FIELD_KEYS
		)
		for field, value in value_map.items():
			if field in already_handled:
				continue
			if update_empty_only and party_doc.get(field):
				continue
			party_doc.set(field, value)

	def _insert_party(self, party_doc) -> None:
		party_doc.flags.ignore_permissions = True
		party_doc.insert()

	def _apply_updatable_fields(self, party_doc, value_map: dict, update_empty_only: bool) -> None:
		for field in UPDATABLE_FIELDS:
			value = value_map.get(field)
			if not value or (update_empty_only and party_doc.get(field)):
				continue
			party_doc.set(field, value)

	def _apply_group_field_update(self, party_doc, value_map: dict, update_empty_only: bool) -> None:
		value = value_map.get(self.group_field)
		if not value or (update_empty_only and party_doc.get(self.group_field)):
			return
		party_doc.set(self.group_field, value)

	def _apply_territory_update(self, party_doc, value_map: dict, update_empty_only: bool) -> None:
		if self.party_type != CUSTOMER or not value_map.get("territory"):
			return
		if update_empty_only and party_doc.territory:
			return
		party_doc.territory = value_map["territory"]

	def _save_notes(self, party_doc, value_map: dict) -> None:
		notes = value_map.get("notes")
		if not notes:
			return
		field = "customer_details" if self.party_type == CUSTOMER else "supplier_details"
		party_doc.db_set(field, notes, update_modified=False)

	def _raw_value(self, row: dict, source: str):
		raw = row.get(source)
		return raw.strip() if isinstance(raw, str) else raw


class AddressCreator:
	"""Creates billing + shipping addresses with disambiguating titles."""

	def __init__(self, party_type: str, name_field: str):
		self.party_type = party_type
		self.name_field = name_field

	def create_all(self, party_doc, value_map: dict) -> None:
		party_name_value = party_doc.get(self.name_field)
		has_billing = self._has_billing(value_map)
		has_shipping = self.party_type == CUSTOMER and self._has_shipping(value_map)

		if has_billing and has_shipping and self._same_address_line1(value_map):
			self._create_combined(party_doc, value_map, party_name_value)
		else:
			if has_billing:
				self._create_billing(party_doc, value_map, party_name_value)
			if has_shipping:
				self._create_shipping(party_doc, value_map, party_name_value)

	def _create_combined(self, party_doc, value_map: dict, party_name_value: str) -> None:
		"""Single address that serves as both billing and shipping."""
		try:
			address = make_address(
				self._args(party_doc, party_name_value, value_map, prefix="billing"),
				is_primary_address=1,
				is_shipping_address=1,
			)
			address.db_set("address_title", party_name_value, update_modified=False)
			if self.party_type == CUSTOMER:
				party_doc.db_set("customer_primary_address", address.name, update_modified=False)
		except Exception as exc:
			frappe.log_error(f"Party Import: combined address failed for {party_doc.name}: {exc}")

	def _create_billing(self, party_doc, value_map: dict, party_name_value: str) -> None:
		try:
			address = make_address(
				self._args(party_doc, party_name_value, value_map, prefix="billing"),
				is_primary_address=1,
				is_shipping_address=0,
			)
			address.db_set("address_title", f"{party_name_value} - Billing", update_modified=False)
			if self.party_type == CUSTOMER:
				party_doc.db_set("customer_primary_address", address.name, update_modified=False)
		except Exception as exc:
			frappe.log_error(f"Party Import: billing address failed for {party_doc.name}: {exc}")

	def _create_shipping(self, party_doc, value_map: dict, party_name_value: str) -> None:
		try:
			address = make_address(
				self._args(party_doc, party_name_value, value_map, prefix="shipping"),
				is_primary_address=0,
				is_shipping_address=1,
			)
			address.db_set("address_title", f"{party_name_value} - Shipping", update_modified=False)
		except Exception as exc:
			frappe.log_error(f"Party Import: shipping address failed for {party_doc.name}: {exc}")

	def _args(self, party_doc, party_name_value: str, value_map: dict, prefix: str) -> dict:
		return frappe._dict(
			{
				"doctype": self.party_type,
				"name": party_doc.name,
				self.name_field: party_name_value,
				"address_line1": value_map.get(f"{prefix}_address_line1"),
				"address_line2": value_map.get(f"{prefix}_address_line2"),
				"city": value_map.get(f"{prefix}_city"),
				"state": value_map.get(f"{prefix}_state"),
				"country": value_map.get(f"{prefix}_country"),
				"pincode": value_map.get(f"{prefix}_pincode"),
				"flags": {"ignore_permissions": True},
			}
		)

	def _same_address_line1(self, value_map: dict) -> bool:
		billing = (value_map.get("billing_address_line1") or "").strip()
		shipping = (value_map.get("shipping_address_line1") or "").strip()
		return bool(billing) and billing == shipping

	def _has_billing(self, value_map: dict) -> bool:
		return bool(value_map.get("billing_address_line1") or value_map.get("billing_city"))

	def _has_shipping(self, value_map: dict) -> bool:
		return bool(value_map.get("shipping_address_line1") or value_map.get("shipping_city"))
