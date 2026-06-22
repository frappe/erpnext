# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""
Company-wise master filtering for Supplier, Customer, and Item.

When a master record has rows in its `allowed_companies` child table it is
only visible/usable for transactions belonging to those companies.  An empty
`allowed_companies` table means the record is global — accessible from all
companies.

Enforcement happens at three layers:
  1. List view / link search  — permission_query_conditions hook
  2. Direct form / API access — has_permission hook
  3. Transaction save         — doc_events validate hook (validate_party_company)

The set of covered DocTypes is driven by the `company_wise_masters_config` hook
so any installed app can extend coverage without patching this file:

    # in another app's hooks.py
    company_wise_masters_config = [
        {"doctype": "MyDocType", "customer_field": "customer", "items_table": "items"},
    ]
"""

import frappe


def is_enabled() -> bool:
	"""Return True when company-wise master filtering is turned on in Accounts Settings."""
	return bool(frappe.db.get_single_value("Accounts Settings", "enable_company_wise_masters"))


def _get_user_companies(user: str) -> list[str]:
	"""Return companies the user is restricted to via User Permissions on Company."""
	return frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Company"},
		pluck="for_value",
	)


def _company_filter_sql(doctype: str, user: str) -> str:
	"""
	Return an SQL fragment that filters `tab{doctype}` rows by allowed_companies.

	Returns "" (no restriction) when:
	- the feature is disabled in Accounts Settings, or
	- the user is System Manager, or
	- the user has no User Permission rows for Company (not company-restricted).
	"""
	if not is_enabled():
		return ""

	if "System Manager" in frappe.get_roles(user):
		return ""

	user_companies = _get_user_companies(user)
	if not user_companies:
		return ""

	companies_sql = ", ".join(frappe.db.escape(c) for c in user_companies)
	return f"""(
        not exists (
            select 1 from `tabAllowed To Transact With` attw
            where attw.parent      = `tab{doctype}`.name
              and attw.parenttype  = '{doctype}'
              and attw.parentfield = 'allowed_companies'
        )
        or exists (
            select 1 from `tabAllowed To Transact With` attw
            where attw.parent      = `tab{doctype}`.name
              and attw.parenttype  = '{doctype}'
              and attw.parentfield = 'allowed_companies'
              and attw.company in ({companies_sql})
        )
    )"""


# ---------- permission_query_conditions hooks ----------


def supplier_query_conditions(user=None):
	return _company_filter_sql("Supplier", user or frappe.session.user)


def customer_query_conditions(user=None):
	return _company_filter_sql("Customer", user or frappe.session.user)


def item_query_conditions(user=None):
	return _company_filter_sql("Item", user or frappe.session.user)


# ---------- has_permission hook ----------


def party_has_permission(doc, user=None, permission_type=None):
	if not is_enabled():
		return True

	user = user or frappe.session.user
	if "System Manager" in frappe.get_roles(user):
		return True

	user_companies = _get_user_companies(user)
	if not user_companies:
		return True

	doc_companies = [row.company for row in (doc.get("allowed_companies") or [])]
	if not doc_companies:
		return True  # global master — visible to all

	return bool(set(doc_companies) & set(user_companies))


# ---------- validate doc_event hook ----------


def _allowed_for_company(master_dt: str, name: str, company: str) -> bool:
	"""Return True if the master has no company restriction or explicitly allows `company`."""
	rows = frappe.get_all(
		"Allowed To Transact With",
		filters={"parent": name, "parenttype": master_dt, "parentfield": "allowed_companies"},
		pluck="company",
	)
	return (not rows) or (company in rows)


def _get_masters_config() -> dict:
	"""
	Return a {doctype: config_dict} map built from the company_wise_masters_config hook.

	frappe.get_hooks() is already cached per-process, so this is effectively O(1) after
	the first call within a request.
	"""
	entries = frappe.get_hooks("company_wise_masters_config") or []
	return {entry["doctype"]: entry for entry in entries}


def validate_party_company(doc, method=None):
	"""
	Throw if any master referenced by the document is not configured for doc.company.

	Reads the company_wise_masters_config hook so coverage extends automatically to
	any DocType registered by an installed app.
	"""
	if not is_enabled():
		return

	config = _get_masters_config().get(doc.doctype)
	if not config:
		return

	company = doc.company

	# --- supplier at document level ---
	supplier_field = config.get("supplier_field")
	if supplier_field:
		supplier = doc.get(supplier_field)
		if supplier and not _allowed_for_company("Supplier", supplier, company):
			frappe.throw(
				frappe._(
					"Supplier {0} is not configured for company {1}. "
					"Add {1} to the Supplier's <b>Allowed Companies</b> table or leave it empty for global access."
				).format(frappe.bold(supplier), frappe.bold(company))
			)

	# --- customer at document level ---
	customer_field = config.get("customer_field")
	if customer_field:
		customer = doc.get(customer_field)
		if customer and not _allowed_for_company("Customer", customer, company):
			frappe.throw(
				frappe._(
					"Customer {0} is not configured for company {1}. "
					"Add {1} to the Customer's <b>Allowed Companies</b> table or leave it empty for global access."
				).format(frappe.bold(customer), frappe.bold(company))
			)

	# --- dynamic party at document level (Payment Entry, Quotation) ---
	party_field = config.get("party_field")
	party_type_field = config.get("party_type_field")
	party_rows_table = config.get("party_rows_table")

	if party_field and not party_rows_table:
		party_type = doc.get(party_type_field) if party_type_field else None
		party = doc.get(party_field)
		if party and party_type in ("Customer", "Supplier"):
			if not _allowed_for_company(party_type, party, company):
				frappe.throw(
					frappe._(
						"{0} {1} is not configured for company {2}. "
						"Add {2} to the {0}'s <b>Allowed Companies</b> table or leave it empty for global access."
					).format(frappe.bold(party_type), frappe.bold(party), frappe.bold(company))
				)

	# --- dynamic party inside child rows (Journal Entry accounts) ---
	if party_field and party_rows_table:
		for row in doc.get(party_rows_table) or []:
			party_type = row.get(party_type_field) if party_type_field else None
			party = row.get(party_field)
			if party and party_type in ("Customer", "Supplier"):
				if not _allowed_for_company(party_type, party, company):
					frappe.throw(
						frappe._(
							"{0} {1} (row {2}) is not configured for company {3}. "
							"Add {3} to the {0}'s <b>Allowed Companies</b> table or leave it empty for global access."
						).format(
							frappe.bold(party_type),
							frappe.bold(party),
							row.idx,
							frappe.bold(company),
						)
					)

	# --- item_code in items child table ---
	items_table = config.get("items_table")
	if items_table:
		item_field = config.get("item_field", "item_code")
		for row in doc.get(items_table) or []:
			item_code = row.get(item_field)
			if item_code and not _allowed_for_company("Item", item_code, company):
				frappe.throw(
					frappe._(
						"Item {0} (row {1}) is not configured for company {2}. "
						"Add {2} to the Item's <b>Allowed Companies</b> table or leave it empty for global access."
					).format(frappe.bold(item_code), row.idx, frappe.bold(company))
				)
