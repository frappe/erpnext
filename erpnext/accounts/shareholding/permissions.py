# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""A global shareholder can contain balances from several companies."""

import frappe
from frappe import _


def get_allowed_companies(user=None, *, reference_doctype=None):
	return frappe.get_list(
		"Company",
		pluck="name",
		limit=0,
		user=user or frappe.session.user,
		reference_doctype=reference_doctype,
	)


def shareholder_has_permission(doc, user=None, ptype=None):
	if (user or frappe.session.user) == "Administrator" or doc.is_new():
		return True
	companies = get_allowed_companies(user)
	assert_no_legacy_shares(user, doc.name)
	if frappe.db.exists("Share Folio", {"shareholder": doc.name, "company": ["not in", companies or [""]]}):
		return False
	return True


def assert_no_legacy_shares(user=None, shareholder=None):
	"""Require removal of legacy shares before framework sharing can bypass company access."""
	user = user or frappe.session.user
	if user == "Administrator":
		return
	share = frappe.qb.DocType("DocShare")
	query = (
		frappe.qb.from_(share)
		.select(share.name)
		.where((share.share_doctype == "Shareholder") & ((share.user == user) | (share.everyone == 1)))
	)
	if shareholder:
		query = query.where(share.share_name == shareholder)
	if query.limit(1).run():
		frappe.throw(
			_("Legacy Shareholder shares must be removed. Run bench migrate before accessing Shareholders."),
			frappe.PermissionError,
		)


def shareholder_query_conditions(user=None):
	if (user or frappe.session.user) == "Administrator":
		return ""
	assert_no_legacy_shares(user)
	folio = frappe.qb.DocType("Share Folio")
	holder = frappe.qb.DocType("Shareholder")
	query = (
		frappe.qb.from_(folio)
		.select(folio.name)
		.where((folio.shareholder == holder.name) & folio.company.notin(get_allowed_companies(user) or [""]))
	)
	return f"not exists ({query.get_sql()})"
