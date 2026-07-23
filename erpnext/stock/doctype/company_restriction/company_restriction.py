# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import comma_and
from pypika.terms import Bracket, ExistsCriterion

RESTRICTABLE_MASTER_DOCTYPES = ("Item", "Customer", "Supplier")

COMPANY_RESTRICTION_EXEMPT_DOCTYPES = frozenset(
	{
		"Asset",
		"Bank Transaction",
		"Exchange Rate Revaluation",
		"Landed Cost Voucher",
		"POS Closing Entry",
		"POS Invoice Merge Log",
		"Payment Reconciliation",
		"Process Payment Reconciliation",
		"Repost Accounting Ledger",
		"Repost Item Valuation",
		"Repost Payment Ledger",
		"Serial No",
		"Serial and Batch Bundle",
		"Unreconcile Payment",
	}
)


class CompanyRestrictionError(frappe.ValidationError):
	pass


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

	return get_restriction_criterion(doctype, allowed_companies)


def get_restriction_criterion(doctype, companies):
	parent = frappe.qb.DocType(doctype)
	restriction = frappe.qb.DocType("Company Restriction")
	allowed_rows = (
		frappe.qb.from_(restriction)
		.select(restriction.name)
		.where(
			(restriction.parenttype == doctype)
			& (restriction.parentfield == "allowed_companies")
			& (restriction.parent == parent.name)
			& (restriction.company.isin(companies))
		)
	)
	return Bracket((parent.restrict_to_companies == 0) | ExistsCriterion(allowed_rows))


def has_permission(doc, ptype=None, user=None):
	if not doc.get("restrict_to_companies"):
		return True

	allowed_companies = get_allowed_companies(user, doc.doctype)
	if not allowed_companies:
		return True

	return any(row.company in allowed_companies for row in doc.get("allowed_companies") or [])


def validate_allowed_companies(doc, method=None):
	if not doc.get("restrict_to_companies"):
		doc.set("allowed_companies", [])
	elif not doc.get("allowed_companies") and not doc.flags.ignore_mandatory:
		frappe.throw(
			_("Allowed Companies is required when Restrict to Companies is checked"),
			frappe.MandatoryError,
		)

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


def validate_transaction_company(doc, method=None):
	if doc.doctype in COMPANY_RESTRICTION_EXEMPT_DOCTYPES or doc.meta.in_create:
		return

	company_field = doc.meta.get_field("company")
	if not company_field or company_field.fieldtype != "Link" or company_field.options != "Company":
		return

	company = doc.get("company")
	if not company:
		return

	for doctype, names in get_master_references(doc).items():
		if blocked := get_blocked_masters(doctype, names, company):
			frappe.throw(
				_("{0} {1} cannot be used with Company {2} because of Company Restrictions").format(
					_(doctype),
					comma_and([frappe.bold(name) for name in blocked], add_quotes=False),
					frappe.bold(company),
				),
				CompanyRestrictionError,
				title=_("Restricted to Other Companies"),
			)


def get_master_references(doc):
	references = defaultdict(set)
	collect_master_references([doc], references)
	for table_field in doc.meta.get_table_fields():
		if rows := doc.get(table_field.fieldname):
			collect_master_references(rows, references)

	return references


def collect_master_references(rows, references):
	meta = frappe.get_meta(rows[0].doctype)
	link_fields = [field for field in meta.get_link_fields() if field.options in RESTRICTABLE_MASTER_DOCTYPES]
	dynamic_link_fields = meta.get_dynamic_link_fields()

	for row in rows:
		for field in link_fields:
			if value := row.get(field.fieldname):
				references[field.options].add(value)

		for field in dynamic_link_fields:
			doctype = row.get(field.options)
			if doctype in RESTRICTABLE_MASTER_DOCTYPES and (value := row.get(field.fieldname)):
				references[doctype].add(value)


def get_blocked_masters(doctype, names, company):
	restricted = frappe.get_all(
		doctype,
		filters={"name": ("in", sorted(names)), "restrict_to_companies": 1},
		pluck="name",
	)
	if not restricted:
		return []

	allowed = frappe.get_all(
		"Company Restriction",
		filters={
			"parenttype": doctype,
			"parentfield": "allowed_companies",
			"parent": ("in", restricted),
			"company": company,
		},
		pluck="parent",
	)
	return sorted(set(restricted) - set(allowed))


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
