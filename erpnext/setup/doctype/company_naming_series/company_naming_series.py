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


def get_allowed_naming_series(company: str, doctype: str) -> list[str] | None:
	"""Naming series this company may use for a doctype, or None when it restricts none.

	The stored options are intersected with the ones the document type currently offers, so a
	series dropped from Document Naming Settings stops being offered without a Company edit. A
	restriction whose every series has been dropped returns an empty list, not None: the company
	was never approved for the rest, so it may not fall back to them.
	"""
	if not company or not frappe.db.exists("Company", company):
		return None

	for row in frappe.get_cached_doc("Company", company).get("document_naming_series") or []:
		if row.document_type == doctype:
			available = frappe.get_meta(doctype).get_naming_series_options()
			return [series for series in row.get_options() if series in available]

	return None


def validate_naming_series(doc, method=None):
	"""Keep a company from using another company's naming series."""
	if not doc.is_new() or not doc.get("company") or not doc.get("naming_series"):
		return

	allowed = get_allowed_naming_series(doc.company, doc.doctype)
	if allowed is None or doc.naming_series in allowed:
		return

	if allowed:
		frappe.throw(
			_("Naming Series {0} is not available for Company {1}. Available: {2}").format(
				frappe.bold(doc.naming_series), frappe.bold(doc.company), frappe.bold(", ".join(allowed))
			),
			title=_("Invalid Naming Series"),
		)

	frappe.throw(
		_(
			"Company {0} has no Naming Series left for {1}. Every series listed on the Company has been removed from the document type."
		).format(frappe.bold(doc.company), frappe.bold(_(doc.doctype))),
		title=_("Invalid Naming Series"),
	)


@frappe.whitelist()
def get_naming_series_options(company: str, doctype: str) -> list[str] | None:
	frappe.has_permission(doctype, throw=True)
	return get_allowed_naming_series(company, doctype)
