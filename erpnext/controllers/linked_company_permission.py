# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Company User Permissions for doctypes that belong to a company only through a link.

Frappe applies a User Permission only on Link fields to the restricted doctype. A doctype
without a Link to Company is therefore open to users restricted to another company. These
hooks give such a doctype the company of the documents that it links to.
"""

from typing import NamedTuple

import frappe
from frappe.query_builder.functions import IfNull
from pypika.terms import Criterion

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies


class CompanyLink(NamedTuple):
	fieldname: str
	doctype: str
	# the field that holds the doctype, when `fieldname` is a Dynamic Link
	doctype_fieldname: str | None = None


COMPANY_LINKS = {
	"Activity Cost": (CompanyLink("employee", "Employee"),),
	"Asset Maintenance Log": (CompanyLink("asset_maintenance", "Asset Maintenance"),),
	"Asset Shift Allocation": (CompanyLink("asset", "Asset"),),
	"Bank Guarantee": (
		CompanyLink("bank_account", "Bank Account"),
		CompanyLink("account", "Account"),
		CompanyLink("project", "Project"),
		CompanyLink("reference_docname", "Sales Order", "reference_doctype"),
		CompanyLink("reference_docname", "Purchase Order", "reference_doctype"),
	),
	"Delivery Schedule Item": (CompanyLink("sales_order", "Sales Order"),),
	"Packing Slip": (CompanyLink("delivery_note", "Delivery Note"),),
	"Process Payment Reconciliation Log": (CompanyLink("process_pr", "Process Payment Reconciliation"),),
	"Process Period Closing Voucher": (CompanyLink("parent_pcv", "Period Closing Voucher"),),
	"Process Subscription": (CompanyLink("subscription", "Subscription"),),
	"Project Update": (CompanyLink("project", "Project"),),
}

# Permission types that can save new link values over the stored ones
WRITE_PTYPES = frozenset({"write", "submit", "cancel"})


def get_permission_query_conditions(user=None, doctype=None):
	links = COMPANY_LINKS.get(doctype)
	if not links:
		return None

	allowed_companies = get_allowed_companies(user, doctype)
	if not allowed_companies:
		return None

	table = frappe.qb.DocType(doctype)
	return Criterion.all(get_link_criterion(table, link, allowed_companies) for link in links)


def has_permission(doc, ptype=None, user=None):
	links = COMPANY_LINKS.get(doc.doctype)
	if not links:
		return True

	allowed_companies = get_allowed_companies(user, doc.doctype)
	if not allowed_companies:
		return True

	return not any(
		is_other_company(doctype, name, allowed_companies)
		for doctype, name in get_linked_documents(doc, links, ptype)
	)


def get_linked_documents(doc, links, ptype):
	rows = [doc]
	# Also check the stored links, or a user could take over another company's record
	# by pointing it to a document of their own company.
	if ptype in WRITE_PTYPES and doc.name and not doc.is_new():
		fieldnames = {name for link in links for name in (link.fieldname, link.doctype_fieldname) if name}
		if stored := frappe.db.get_value(doc.doctype, doc.name, list(fieldnames), as_dict=True):
			rows.append(stored)

	for row in rows:
		for link in links:
			if link.doctype_fieldname and row.get(link.doctype_fieldname) != link.doctype:
				continue
			if name := row.get(link.fieldname):
				yield link.doctype, name


def is_other_company(doctype, name, allowed_companies):
	company = frappe.db.get_value(doctype, name, "company")
	return bool(company) and company not in allowed_companies


def get_link_criterion(table, link, companies):
	linked = frappe.qb.DocType(link.doctype)
	other_company_documents = (
		frappe.qb.from_(linked).select(linked.name).where(IfNull(linked.company, "").notin([*companies, ""]))
	)
	field = table[link.fieldname]
	criterion = (IfNull(field, "") == "") | field.notin(other_company_documents)
	if link.doctype_fieldname:
		criterion = (IfNull(table[link.doctype_fieldname], "") != link.doctype) | criterion

	return criterion
