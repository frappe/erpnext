# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CompanyNamingSeries(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_type: DF.Link
		naming_series_options: DF.SmallText
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	def get_options(self) -> list[str]:
		return [option.strip() for option in (self.naming_series_options or "").split("\n") if option.strip()]


def get_allowed_naming_series(company: str, doctype: str) -> list[str]:
	"""Naming series this company may use for a doctype. An empty list means no restriction."""
	if not company or not frappe.db.exists("Company", company):
		return []

	for row in frappe.get_cached_doc("Company", company).get("document_naming_series") or []:
		if row.document_type == doctype:
			return row.get_options()

	return []


def validate_naming_series(doc, method=None):
	"""Keep a company from using another company's naming series."""
	if not doc.is_new() or not doc.get("company") or not doc.get("naming_series"):
		return

	allowed = get_allowed_naming_series(doc.company, doc.doctype)
	if not allowed or doc.naming_series in allowed:
		return

	frappe.throw(
		_("Naming Series {0} is not available for Company {1}. Available: {2}").format(
			frappe.bold(doc.naming_series), frappe.bold(doc.company), frappe.bold(", ".join(allowed))
		),
		title=_("Invalid Naming Series"),
	)


@frappe.whitelist()
def get_naming_series_options(company: str, doctype: str) -> list[str]:
	frappe.has_permission(doctype, throw=True)
	return get_allowed_naming_series(company, doctype)
