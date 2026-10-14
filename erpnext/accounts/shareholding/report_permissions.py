# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

from erpnext.accounts.shareholding.legacy import assert_legacy_history_backfilled
from erpnext.accounts.shareholding.permissions import get_allowed_companies


def apply_report_filters(query, entry, folio, filters, *, ignore_company_permissions=False):
	for field in ("company", "share_class", "share_folio", "shareholder"):
		if filters.get(field) and not isinstance(filters[field], str):
			frappe.throw(_("{0} must be a document name.").format(field))
	companies = get_allowed_companies(reference_doctype="Share Ledger Entry")
	if filters.get("company"):
		companies = (
			[filters.company]
			if ignore_company_permissions
			or frappe.session.user == "Administrator"
			or filters.company in companies
			else []
		)
	for company in companies:
		assert_legacy_history_backfilled(company)
	if not ignore_company_permissions and frappe.session.user != "Administrator":
		companies = get_allowed_companies(reference_doctype="Share Ledger Entry")
		if filters.get("company") and filters.company not in companies:
			frappe.throw(_("You do not have access to this company."), frappe.PermissionError)
		query = query.where(entry.company.isin(companies or [""]))
		permitted_entries = frappe.qb.get_query(
			"Share Ledger Entry", fields=["name"], ignore_permissions=False
		)
		query = query.where(entry.name.isin(permitted_entries))
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
