# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Pre-mapped column synonyms for known source systems.

Each template is a ``{normalized_source_header: target_field}`` map. Headers
are pre-normalized the same way ``column_mapper.normalize`` would normalize a
spreadsheet header — lowercased, alphanumerics only — so Tally's ``GSTIN/UIN``
matches as ``gstinuin``.

Generic synonyms in :mod:`column_mapper` handle the wide-net cases (``Email``,
``Mobile``, ``Address``…). Templates here add the source-specific labels that
those synonyms don't anticipate (``Ledger Name``, ``Display Name``,
``Customer Type``…) and resolve party-type-dependent targets — Tally's
``Ledger Name`` is ``customer_name`` for debtors and ``supplier_name`` for
creditors, and the same dance applies to QuickBooks ``Customer`` / ``Vendor``
and Zoho ``Customer Sub Type`` / ``Vendor Sub Type``.

To add a new source system, drop a ``SourceTemplate`` into :data:`_TEMPLATES`.
No other code needs to change.
"""

from dataclasses import dataclass

from erpnext.selling.doctype.party_import_log.schema import (
	group_field_for,
	name_field_for,
)

GENERIC = "Generic"
TALLY = "Tally"
QUICKBOOKS = "QuickBooks"
ZOHO = "Zoho"
HUBSPOT = "HubSpot"
SALESFORCE = "Salesforce"


@dataclass(frozen=True)
class SourceTemplate:
	"""Config for one source system's import shape.

	* ``base_synonyms`` — party-type-independent mappings of normalized source
	  headers to target fields (e.g. ``"gstinuin" -> "tax_id"``).
	* ``name_synonyms`` / ``group_synonyms`` — normalized headers that resolve
	  to the party-type-specific name and group fields.
	* ``columns`` — ordered ``(display_header, target_field)`` pairs that drive
	  the downloadable CSV template. Use ``"__name__"`` / ``"__group__"`` as
	  the target sentinel to substitute the party-type-specific field.
	* ``filename_suffix`` — appended to the downloaded filename so users can
	  tell exports apart.
	"""

	base_synonyms: dict[str, str]
	name_synonyms: tuple[str, ...]
	group_synonyms: tuple[str, ...]
	columns: tuple[tuple[str, str], ...]
	filename_suffix: str
	name_sentinel: str = "__name__"
	group_sentinel: str = "__group__"


def get_template_mappings(source_format: str, party_type: str) -> dict[str, str]:
	"""Return the ``{normalized_source_header: target_field}`` map for a source system.

	Returns an empty dict for ``Generic`` (or any unknown format) so callers can
	always pass the result through to :class:`ColumnMapper` without branching.
	"""
	template = _TEMPLATES.get(source_format)
	if not template:
		return {}
	name_field = name_field_for(party_type)
	group_field = group_field_for(party_type)
	return {
		**template.base_synonyms,
		**{alias: name_field for alias in template.name_synonyms},
		**{alias: group_field for alias in template.group_synonyms},
	}


def get_template_columns(source_format: str, party_type: str) -> list[tuple[str, str]] | None:
	"""Return ``[(display_header, target_field), ...]`` for a downloadable template.

	The order is the order columns should appear in the generated CSV. Returns
	``None`` for ``Generic`` so the caller can fall back to the live target schema.
	"""
	template = _TEMPLATES.get(source_format)
	if not template:
		return None
	name_field = name_field_for(party_type)
	group_field = group_field_for(party_type)
	return [
		(header, _resolve_target(target, template, name_field, group_field))
		for header, target in template.columns
	]


def filename_suffix_for(source_format: str) -> str:
	"""Return the filename suffix for a given source format (empty for Generic/unknown)."""
	template = _TEMPLATES.get(source_format)
	return template.filename_suffix if template else ""


def _resolve_target(target: str, template: SourceTemplate, name_field: str, group_field: str) -> str:
	if target == template.name_sentinel:
		return name_field
	if target == template.group_sentinel:
		return group_field
	return target


# ---------------------------------------------------------------------------
# Tally Prime / Tally ERP 9 ledger export.
# Address1..4 reflect Tally's split-address export — lines 3 and 4 fold into
# line2 since our target schema only has two address-line fields.
_TALLY = SourceTemplate(
	base_synonyms={
		"address1": "billing_address_line1",
		"address2": "billing_address_line2",
		"address3": "billing_address_line2",
		"address4": "billing_address_line2",
		"addressline3": "billing_address_line2",
		"addressline4": "billing_address_line2",
		"gstinuin": "tax_id",
		"gstregistrationno": "tax_id",
		"panitno": "tax_id",
		"panno": "tax_id",
		"telephone": "primary_phone",
		"contactperson": "primary_first_name",
		"narration": "notes",
		"remarks": "notes",
	},
	name_synonyms=("ledgername", "mailingname", "alias"),
	group_synonyms=("under", "groupname"),
	columns=(
		("Ledger Name", "__name__"),
		("Under", "__group__"),
		("GSTIN/UIN", "tax_id"),
		("Address Line 1", "billing_address_line1"),
		("Address Line 2", "billing_address_line2"),
		("State", "billing_state"),
		("Country", "billing_country"),
		("Pincode", "billing_pincode"),
		("Email-ID", "primary_email"),
		("Mobile", "primary_mobile"),
		("Telephone", "primary_phone"),
		("Contact Person", "primary_first_name"),
		("Website", "website"),
		("Currency", "default_currency"),
		("Narration", "notes"),
	),
	filename_suffix="_tally",
)


# ---------------------------------------------------------------------------
# QuickBooks Online customer/vendor export.
# QBO writes "Customer"/"Vendor" as the display-name column and uses
# "Customer Type" / "Vendor Type" as the group classifier. "Tax Resale No"
# carries the tax id on the customer export; vendor uses "Tax ID" which the
# generic synonyms already cover.
_QUICKBOOKS = SourceTemplate(
	base_synonyms={
		"taxresaleno": "tax_id",
		"terms": "payment_terms",
		# In QB exports "Phone" is the landline and "Mobile" is the cell —
		# override the generic synonym that maps "phone" to primary_mobile.
		"phone": "primary_phone",
		"mobile": "primary_mobile",
		"billingaddressline1": "billing_address_line1",
		"billingaddressline2": "billing_address_line2",
		"billingcity": "billing_city",
		"billingstate": "billing_state",
		"billingprovincestate": "billing_state",
		"billingpostalcode": "billing_pincode",
		"billingcountry": "billing_country",
		"shippingaddressline1": "shipping_address_line1",
		"shippingaddressline2": "shipping_address_line2",
		"shippingcity": "shipping_city",
		"shippingstate": "shipping_state",
		"shippingprovincestate": "shipping_state",
		"shippingpostalcode": "shipping_pincode",
		"shippingcountry": "shipping_country",
	},
	name_synonyms=("customer", "vendor", "displayname", "printoncheckas"),
	group_synonyms=("customertype", "vendortype"),
	columns=(
		("Customer", "__name__"),
		("Customer Type", "__group__"),
		("First Name", "primary_first_name"),
		("Last Name", "primary_last_name"),
		("Email", "primary_email"),
		("Phone", "primary_phone"),
		("Mobile", "primary_mobile"),
		("Website", "website"),
		("Tax Resale No", "tax_id"),
		("Terms", "payment_terms"),
		("Currency", "default_currency"),
		("Notes", "notes"),
		("Billing Address Line 1", "billing_address_line1"),
		("Billing Address Line 2", "billing_address_line2"),
		("Billing City", "billing_city"),
		("Billing State", "billing_state"),
		("Billing Postal Code", "billing_pincode"),
		("Billing Country", "billing_country"),
		("Shipping Address Line 1", "shipping_address_line1"),
		("Shipping Address Line 2", "shipping_address_line2"),
		("Shipping City", "shipping_city"),
		("Shipping State", "shipping_state"),
		("Shipping Postal Code", "shipping_pincode"),
		("Shipping Country", "shipping_country"),
	),
	filename_suffix="_quickbooks",
)


# ---------------------------------------------------------------------------
# Zoho Books / Zoho CRM contact export.
# Zoho splits address as ``Billing Address`` (line 1) + ``Billing Street2``
# (line 2) and uses ``Billing Code`` for pincode. The verbose
# ``GST Identification Number (GSTIN)`` / ``PAN Identification Number (PAN)``
# headers normalize to long alphanumeric strings — we map those explicitly so
# the fuzzy matcher doesn't have to guess.
_ZOHO = SourceTemplate(
	base_synonyms={
		"currencycode": "default_currency",
		"billingaddress": "billing_address_line1",
		"billingstreet2": "billing_address_line2",
		"billingcode": "billing_pincode",
		"shippingaddress": "shipping_address_line1",
		"shippingstreet2": "shipping_address_line2",
		"shippingcode": "shipping_pincode",
		"gstidentificationnumbergstin": "tax_id",
		"panidentificationnumberpan": "tax_id",
		"gstin": "tax_id",
		# Zoho has both ``Phone`` (landline) and ``MobilePhone`` columns; the
		# generic dict would route both to primary_mobile and drop one.
		"phone": "primary_phone",
		"mobilephone": "primary_mobile",
		"paymenttermslabel": "payment_terms",
	},
	name_synonyms=("displayname", "contactname"),
	group_synonyms=("customersubtype", "vendorsubtype"),
	columns=(
		("Display Name", "__name__"),
		("Customer Sub Type", "__group__"),
		("First Name", "primary_first_name"),
		("Last Name", "primary_last_name"),
		("EmailID", "primary_email"),
		("MobilePhone", "primary_mobile"),
		("Phone", "primary_phone"),
		("Currency Code", "default_currency"),
		("Website", "website"),
		("GST Identification Number (GSTIN)", "tax_id"),
		("Price List", "default_price_list"),
		("Payment Terms", "payment_terms"),
		("Notes", "notes"),
		("Billing Address", "billing_address_line1"),
		("Billing Street2", "billing_address_line2"),
		("Billing City", "billing_city"),
		("Billing State", "billing_state"),
		("Billing Country", "billing_country"),
		("Billing Code", "billing_pincode"),
		("Shipping Address", "shipping_address_line1"),
		("Shipping Street2", "shipping_address_line2"),
		("Shipping City", "shipping_city"),
		("Shipping State", "shipping_state"),
		("Shipping Country", "shipping_country"),
		("Shipping Code", "shipping_pincode"),
	),
	filename_suffix="_zoho",
)


# ---------------------------------------------------------------------------
# HubSpot Companies / Contacts export.
# HubSpot uses "Phone Number" for the main business phone and
# "Mobile Phone Number" for the cell — override the generic synonym that
# routes both "phonenumber" and "mobilephonenumber" to primary_mobile.
# "State/Region" and "Country/Region" contain a slash that normalizes away to
# "stateregion" / "countryregion"; "Website URL" → "websiteurl" similarly.
_HUBSPOT = SourceTemplate(
	base_synonyms={
		"phonenumber": "primary_phone",
		"mobilephonenumber": "primary_mobile",
		"streetaddress": "billing_address_line1",
		"streetaddress2": "billing_address_line2",
		"stateregion": "billing_state",
		"countryregion": "billing_country",
		"companydomainname": "website",
		"websiteurl": "website",
	},
	name_synonyms=("companyname", "company", "contactname"),
	group_synonyms=("lifecyclestage",),
	columns=(
		("Company Name", "__name__"),
		("Lifecycle Stage", "__group__"),
		("First Name", "primary_first_name"),
		("Last Name", "primary_last_name"),
		("Email Address", "primary_email"),
		("Phone Number", "primary_phone"),
		("Mobile Phone Number", "primary_mobile"),
		("Company Domain Name", "website"),
		("Industry", "industry"),
		("Default Currency", "default_currency"),
		("Payment Terms", "payment_terms"),
		("Notes", "notes"),
		("Street Address", "billing_address_line1"),
		("Street Address 2", "billing_address_line2"),
		("City", "billing_city"),
		("State/Region", "billing_state"),
		("Postal Code", "billing_pincode"),
		("Country/Region", "billing_country"),
	),
	filename_suffix="_hubspot",
)


# ---------------------------------------------------------------------------
# Salesforce Account / Contact export.
# Salesforce "Phone" is the business landline — override the generic synonym
# that routes "phone" → primary_mobile.
# Account export uses "Billing Street" / "Shipping Street" (single-field
# street). Contact export uses "Mailing Street" for the primary address —
# both are mapped so either export shape imports cleanly.
# "Billing State/Province" normalizes to "billingstateprovince";
# "Billing Zip/Postal Code" normalizes to "billingzippostalcode".
# "Currency ISO Code" (multi-currency orgs) → default_currency.
_SALESFORCE = SourceTemplate(
	base_synonyms={
		"phone": "primary_phone",
		"mobile": "primary_mobile",
		"billingstreet": "billing_address_line1",
		"billingcity": "billing_city",
		"billingstateprovince": "billing_state",
		"billingzippostalcode": "billing_pincode",
		"billingcountry": "billing_country",
		"shippingstreet": "shipping_address_line1",
		"shippingcity": "shipping_city",
		"shippingstateprovince": "shipping_state",
		"shippingzippostalcode": "shipping_pincode",
		"shippingcountry": "shipping_country",
		"currencyisocode": "default_currency",
		# Contact export uses "Mailing" prefix for the primary address
		"mailingstreet": "billing_address_line1",
		"mailingcity": "billing_city",
		"mailingstateprovince": "billing_state",
		"mailingzippostalcode": "billing_pincode",
		"mailingcountry": "billing_country",
	},
	name_synonyms=("accountname",),
	group_synonyms=("type", "accounttype"),
	columns=(
		("Account Name", "__name__"),
		("Type", "__group__"),
		("First Name", "primary_first_name"),
		("Last Name", "primary_last_name"),
		("Email", "primary_email"),
		("Phone", "primary_phone"),
		("Mobile", "primary_mobile"),
		("Website", "website"),
		("Tax ID", "tax_id"),
		("Industry", "industry"),
		("Payment Terms", "payment_terms"),
		("Currency ISO Code", "default_currency"),
		("Description", "notes"),
		("Billing Street", "billing_address_line1"),
		("Billing City", "billing_city"),
		("Billing State/Province", "billing_state"),
		("Billing Zip/Postal Code", "billing_pincode"),
		("Billing Country", "billing_country"),
		("Shipping Street", "shipping_address_line1"),
		("Shipping City", "shipping_city"),
		("Shipping State/Province", "shipping_state"),
		("Shipping Zip/Postal Code", "shipping_pincode"),
		("Shipping Country", "shipping_country"),
	),
	filename_suffix="_salesforce",
)


_TEMPLATES: dict[str, SourceTemplate] = {
	TALLY: _TALLY,
	QUICKBOOKS: _QUICKBOOKS,
	ZOHO: _ZOHO,
	HUBSPOT: _HUBSPOT,
	SALESFORCE: _SALESFORCE,
}


SOURCE_FORMATS = (GENERIC, *_TEMPLATES.keys())
