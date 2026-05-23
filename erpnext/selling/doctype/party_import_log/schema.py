# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Field and master-data schemas for the Party Import feature.

This module is the single source of truth for the importer's "what":
which target fields exist on Customer / Supplier, which of those resolve
against master DocTypes, how to create masters when they're missing, and
the upload / batching limits enforced by the rest of the pipeline.
"""

import frappe
from frappe import _

CUSTOMER = "Customer"
SUPPLIER = "Supplier"
PARTY_TYPES = (CUSTOMER, SUPPLIER)

# Fieldtypes that can be set directly on the party doc from a flat CSV value.
# Link and Table types are excluded: Links need dependency resolution, Tables
# need child-row construction — both are beyond flat-CSV import scope.
IMPORTABLE_CUSTOM_FIELDTYPES = frozenset(
	{
		"Data",
		"Small Text",
		"Text",
		"Long Text",
		"Int",
		"Float",
		"Currency",
		"Percent",
		"Select",
		"Check",
		"Date",
		"Datetime",
		"Time",
		"Duration",
	}
)

# Fieldnames in the target schema that do NOT map to actual Customer/Supplier
# meta fields — they are virtual aliases for Contact, Address, or child-table
# data handled by ContactLinker, AddressCreator, and PartyCreator._apply_*.
VIRTUAL_FIELD_KEYS = frozenset(
	{
		"primary_first_name",
		"primary_last_name",
		"primary_email",
		"primary_mobile",
		"primary_phone",
		"billing_address_line1",
		"billing_address_line2",
		"billing_city",
		"billing_state",
		"billing_country",
		"billing_pincode",
		"shipping_address_line1",
		"shipping_address_line2",
		"shipping_city",
		"shipping_state",
		"shipping_country",
		"shipping_pincode",
		"notes",
		"credit_limit",
		"credit_limit_company",
	}
)


CUSTOMER_TARGET_FIELDS = [
	("customer_name", "Customer Name", "Identity", True),
	("customer_type", "Customer Type", "Identity", False),
	("tax_id", "Tax ID", "Identity", False),
	("customer_group", "Customer Group", "Classification", False),
	("territory", "Territory", "Classification", False),
	("industry", "Industry", "Classification", False),
	("market_segment", "Market Segment", "Classification", False),
	("account_manager", "Account Manager (User email)", "Classification", False),
	("default_currency", "Default Currency", "Defaults", False),
	("default_price_list", "Default Price List", "Defaults", False),
	("payment_terms", "Payment Terms Template", "Defaults", False),
	("language", "Print Language", "Defaults", False),
	("website", "Website", "Defaults", False),
	("credit_limit", "Credit Limit", "Credit", False),
	("credit_limit_company", "Credit Limit Company", "Credit", False),
	("primary_first_name", "Primary Contact First Name", "Primary Contact", False),
	("primary_last_name", "Primary Contact Last Name", "Primary Contact", False),
	("primary_email", "Primary Email", "Primary Contact", False),
	("primary_mobile", "Primary Mobile", "Primary Contact", False),
	("primary_phone", "Primary Phone", "Primary Contact", False),
	("billing_address_line1", "Billing Address Line 1", "Billing Address", False),
	("billing_address_line2", "Billing Address Line 2", "Billing Address", False),
	("billing_city", "Billing City", "Billing Address", False),
	("billing_state", "Billing State", "Billing Address", False),
	("billing_country", "Billing Country", "Billing Address", False),
	("billing_pincode", "Billing Pincode", "Billing Address", False),
	("shipping_address_line1", "Shipping Address Line 1", "Shipping Address", False),
	("shipping_address_line2", "Shipping Address Line 2", "Shipping Address", False),
	("shipping_city", "Shipping City", "Shipping Address", False),
	("shipping_state", "Shipping State", "Shipping Address", False),
	("shipping_country", "Shipping Country", "Shipping Address", False),
	("shipping_pincode", "Shipping Pincode", "Shipping Address", False),
	("notes", "Notes", "Misc", False),
]


SUPPLIER_TARGET_FIELDS = [
	("supplier_name", "Supplier Name", "Identity", True),
	("supplier_type", "Supplier Type", "Identity", False),
	("tax_id", "Tax ID", "Identity", False),
	("supplier_group", "Supplier Group", "Classification", False),
	("country", "Country", "Classification", False),
	("default_currency", "Default Currency", "Defaults", False),
	("default_price_list", "Default Price List", "Defaults", False),
	("payment_terms", "Payment Terms Template", "Defaults", False),
	("language", "Print Language", "Defaults", False),
	("website", "Website", "Defaults", False),
	("primary_first_name", "Primary Contact First Name", "Primary Contact", False),
	("primary_last_name", "Primary Contact Last Name", "Primary Contact", False),
	("primary_email", "Primary Email", "Primary Contact", False),
	("primary_mobile", "Primary Mobile", "Primary Contact", False),
	("primary_phone", "Primary Phone", "Primary Contact", False),
	("billing_address_line1", "Billing Address Line 1", "Billing Address", False),
	("billing_address_line2", "Billing Address Line 2", "Billing Address", False),
	("billing_city", "Billing City", "Billing Address", False),
	("billing_state", "Billing State", "Billing Address", False),
	("billing_country", "Billing Country", "Billing Address", False),
	("billing_pincode", "Billing Pincode", "Billing Address", False),
	("notes", "Notes", "Misc", False),
]


DEPENDENCY_FIELDS_CUSTOMER = {
	"customer_group": ("Customer Group", True),
	"territory": ("Territory", True),
	"default_currency": ("Currency", False),
	"default_price_list": ("Price List", False),
	"billing_country": ("Country", False),
	"shipping_country": ("Country", False),
	"industry": ("Industry Type", False),
	"market_segment": ("Market Segment", False),
	"payment_terms": ("Payment Terms Template", False),
	"language": ("Language", False),
}


DEPENDENCY_FIELDS_SUPPLIER = {
	"supplier_group": ("Supplier Group", True),
	"default_currency": ("Currency", False),
	"default_price_list": ("Price List", False),
	"country": ("Country", False),
	"billing_country": ("Country", False),
	"payment_terms": ("Payment Terms Template", False),
	"language": ("Language", False),
}


NON_CREATABLE_MASTERS = {"Country", "Currency", "Language"}


MASTER_NAME_FIELDS = {
	"Customer Group": "customer_group_name",
	"Supplier Group": "supplier_group_name",
	"Territory": "territory_name",
	"Price List": "price_list_name",
	"Industry Type": "industry",
	"Market Segment": "market_segment",
	"Payment Terms Template": "template_name",
}


TREE_MASTER_FIELDS = {
	"Customer Group": ("parent_customer_group", "customer_group_name"),
	"Supplier Group": ("parent_supplier_group", "supplier_group_name"),
	"Territory": ("parent_territory", "territory_name"),
}


TREE_MASTER_ROOTS = {
	"Customer Group": "All Customer Groups",
	"Supplier Group": "All Supplier Groups",
	"Territory": "All Territories",
}


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 10_000
IMPORT_BATCH_SIZE = 50
SAMPLE_ROW_COUNT = 5
RECENT_ERRORS_LIMIT = 10
DRY_RUN_ERROR_LIMIT = 20
# Above this many errors, inline editing is disabled — the user should fix the
# source file rather than babysit one-by-one corrections. Tuned by intuition;
# raise once we have usage signal.
INLINE_EDIT_ERROR_LIMIT = 50


def target_fields_for(party_type: str) -> list[tuple]:
	"""Return the target-field schema for the given party type.

	Labels are resolved from the live meta (respecting Customize Form renames)
	and translated into the current user's language. Custom fields of importable
	types are appended under a "Custom Fields" group.
	"""
	meta = frappe.get_meta(party_type)
	base = CUSTOMER_TARGET_FIELDS if party_type == CUSTOMER else SUPPLIER_TARGET_FIELDS
	fields = [
		(fieldname, _live_label(meta, fieldname, label), group, required)
		for fieldname, label, group, required in base
	]
	fields += _custom_target_fields(meta)
	return fields


def _live_label(meta, fieldname: str, fallback: str) -> str:
	"""Return the translated label for a field, falling back to the hardcoded value.

	Virtual fields (contact/address aliases) have no meta entry and keep their
	hardcoded fallback, which is then translated like any other label.
	"""
	field = meta.get_field(fieldname)
	raw = field.label if field else fallback
	return _(raw)


def _custom_target_fields(meta) -> list[tuple]:
	"""Return importable custom fields from meta, grouped under 'Custom Fields'."""
	fields = []
	for field in meta.fields:
		if not field.get("is_custom_field"):
			continue
		if field.fieldtype not in IMPORTABLE_CUSTOM_FIELDTYPES:
			continue
		if field.fieldname in VIRTUAL_FIELD_KEYS:
			continue
		fields.append((field.fieldname, _(field.label), "Custom Fields", False))
	return fields


def dependency_fields_for(party_type: str) -> dict[str, tuple[str, bool]]:
	"""Return the master-dependent fields for the given party type."""
	return DEPENDENCY_FIELDS_CUSTOMER if party_type == CUSTOMER else DEPENDENCY_FIELDS_SUPPLIER


def name_field_for(party_type: str) -> str:
	"""Return the identity field for the given party type."""
	return "customer_name" if party_type == CUSTOMER else "supplier_name"


def group_field_for(party_type: str) -> str:
	"""Return the group field for the given party type."""
	return "customer_group" if party_type == CUSTOMER else "supplier_group"
