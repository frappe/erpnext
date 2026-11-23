# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The report filters on adjustment rows: the same rules as the GL query of the reports."""

import frappe
import frappe.permissions
from frappe.utils import cstr

from erpnext.accounts.cash_basis import queries
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimension_filter_values


def apply_report_filters(rows: list[dict], company: str, filters: dict | None) -> list[dict]:
	"""Keep the rows that the GL query of a report keeps: user permissions, dimensions, project,
	finance book.

	The calculation reads whole vouchers, so that a hidden line cannot break the proof rule.
	The user permissions then apply to the adjustment rows, as they apply to GL rows.
	"""
	rows = apply_user_permissions(rows)
	if not filters:
		return rows
	checks = get_dimension_checks(filters)
	finance_books = get_finance_books(company, filters)
	return [
		row
		for row in rows
		if cstr(row.get("finance_book")) in finance_books
		and all(
			matches(row.get(fieldname), values, include_blank) for fieldname, values, include_blank in checks
		)
	]


def get_dimension_checks(filters) -> list[tuple]:
	checks = []
	for fieldname, doctype in queries.get_dimension_doctypes().items():
		if filters.get(fieldname):
			values, include_blank = get_dimension_filter_values(filters[fieldname], doctype)
			checks.append((fieldname, set(values), include_blank))
	return checks


def get_finance_books(company, filters) -> set[str]:
	"""As apply_additional_conditions: the selected book, the default book if included, and none."""
	books = {cstr(filters.get("finance_book")), ""}
	if filters.get("include_default_book_entries"):
		books.add(cstr(frappe.get_cached_value("Company", company, "default_finance_book")))
	return books


def matches(value, values, include_blank) -> bool:
	if not value:
		return include_blank
	return value in values


def apply_user_permissions(rows: list[dict]) -> list[dict]:
	"""The match conditions of GL Entry for the session user (frappe.model.db_query.add_user_permissions).

	Only the link fields that an adjustment row carries are checked, for example not the currency.
	"""
	user_permissions = frappe.permissions.get_user_permissions(frappe.session.user)
	if not user_permissions:
		return rows
	strict = frappe.get_system_settings("apply_strict_user_permissions")
	allowed = {}
	for df in frappe.get_meta("GL Entry").get_link_fields():
		if df.get("ignore_user_permissions"):
			continue
		docs = {
			permission.get("doc")
			for permission in user_permissions.get(df.options, [])
			if permission.get("applicable_for") in (None, "", "GL Entry")
		}
		if docs:
			allowed[df.fieldname] = docs
	if not allowed:
		return rows
	return [
		row
		for row in rows
		if all(
			(not row.get(fieldname) and not strict) or row.get(fieldname) in docs
			for fieldname, docs in allowed.items()
			if fieldname in row
		)
	]
