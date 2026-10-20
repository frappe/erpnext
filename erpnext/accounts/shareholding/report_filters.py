# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

from erpnext.accounts.shareholding.legacy_migration import assert_legacy_history_backfilled
from erpnext.accounts.shareholding.shareholder_permissions import get_allowed_companies


def require_company(filters):
	if not filters.get("company"):
		frappe.throw(_("Please select a Company."))


def apply_report_filters(query, entry, folio, filters, *, ignore_company_permissions=False):
	validate_filter_types(filters)
	allowed_companies = get_allowed_companies(reference_doctype="Share Ledger Entry")
	restricted = not ignore_company_permissions and frappe.session.user != "Administrator"
	for company in get_companies_to_check(filters, allowed_companies, restricted):
		assert_legacy_history_backfilled(company)
	if restricted:
		query = restrict_to_allowed_entries(query, entry, filters, allowed_companies)
	return apply_value_filters(query, entry, folio, filters)


def validate_filter_types(filters):
	for field in ("company", "share_class", "share_folio", "shareholder"):
		if filters.get(field) and not isinstance(filters[field], str):
			frappe.throw(_("{0} must be a document name.").format(field))


def get_companies_to_check(filters, allowed_companies, restricted):
	company = filters.get("company")
	if not company:
		return allowed_companies
	return [company] if not restricted or company in allowed_companies else []


def restrict_to_allowed_entries(query, entry, filters, allowed_companies):
	if filters.get("company") and filters.company not in allowed_companies:
		frappe.throw(_("You do not have access to this company."), frappe.PermissionError)
	permitted_entries = frappe.qb.get_query("Share Ledger Entry", fields=["name"], ignore_permissions=False)
	return query.where(entry.company.isin(allowed_companies or [""])).where(
		entry.name.isin(permitted_entries)
	)


def apply_value_filters(query, entry, folio, filters):
	for field in ("company", "share_class", "share_folio"):
		if filters.get(field):
			query = query.where(entry[field] == filters[field])
	if filters.get("shareholder"):
		query = query.where(folio.shareholder == filters.shareholder)
	if filters.get("from_date"):
		query = query.where(entry.posting_date >= getdate(filters.from_date))
	for field in ("to_date", "as_of_date"):
		if filters.get(field):
			query = query.where(entry.posting_date <= getdate(filters[field]))
	return query
