# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from pypika.terms import Bracket, ExistsCriterion


class CompanyRestriction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types


def get_allowed_companies(user, doctype):
	from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions

	if not frappe.get_single_value("Global Defaults", "enable_company_wise_masters"):
		return None

	user_permissions = get_user_permissions(user or frappe.session.user)
	if "Company" not in user_permissions:
		return None
	return get_allowed_docs_for_doctype(user_permissions["Company"], doctype) or None


def get_permission_query_conditions(user, doctype=None):
	if not doctype:
		return None

	allowed_companies = get_allowed_companies(user, doctype)
	if not allowed_companies:
		return None

	parent = frappe.qb.DocType(doctype)
	restriction = frappe.qb.DocType("Company Restriction")
	restriction_rows = (
		frappe.qb.from_(restriction)
		.select(restriction.name)
		.where(
			(restriction.parenttype == doctype)
			& (restriction.parentfield == "allowed_companies")
			& (restriction.parent == parent.name)
		)
	)
	allowed_rows = restriction_rows.where(restriction.company.isin(allowed_companies))
	return Bracket(ExistsCriterion(allowed_rows) | ExistsCriterion(restriction_rows).negate())


def has_permission(doc, ptype=None, user=None):
	allowed_companies = get_allowed_companies(user, doc.doctype)
	if not allowed_companies:
		return True

	companies = [row.company for row in doc.get("allowed_companies") or []]
	if not companies:
		return True
	return any(company in allowed_companies for company in companies)


def validate_allowed_companies(doc):
	if doc.flags.ignore_permissions:
		return

	allowed_companies = get_allowed_companies(frappe.session.user, doc.doctype)
	if not allowed_companies:
		return

	previous_companies = set()
	if previous_doc := doc.get_doc_before_save():
		previous_companies = {row.company for row in previous_doc.get("allowed_companies") or []}

	current_companies = {row.company for row in doc.get("allowed_companies") or []}
	for company in current_companies.symmetric_difference(previous_companies):
		if company not in allowed_companies:
			frappe.throw(
				_("You are not permitted to add or remove Company {0} in Allowed Companies").format(company),
				frappe.PermissionError,
			)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def company_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | str | None = None,
):
	filters = frappe.parse_json(filters) if filters else {}
	if isinstance(filters, list):
		filters.append(["Company", "name", "like", f"%{txt}%"])
	else:
		filters["name"] = ("like", f"%{txt}%")

	return frappe.get_list(
		"Company",
		filters=filters,
		limit_start=start,
		limit_page_length=page_len,
		order_by="name",
		as_list=True,
	)
