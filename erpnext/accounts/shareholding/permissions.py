# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""A global shareholder can contain balances from several companies."""

import frappe


def get_allowed_companies(user=None):
	return frappe.get_list("Company", pluck="name", limit=0, user=user or frappe.session.user)


def shareholder_has_permission(doc, user=None, ptype=None):
	if (user or frappe.session.user) == "Administrator" or doc.is_new():
		return None
	companies = get_allowed_companies(user)
	if frappe.db.exists("Share Folio", {"shareholder": doc.name, "company": ["not in", companies or [""]]}):
		return False
	return None


def shareholder_query_conditions(user=None):
	if (user or frappe.session.user) == "Administrator":
		return ""
	folio = frappe.qb.DocType("Share Folio")
	holder = frappe.qb.DocType("Shareholder")
	query = (
		frappe.qb.from_(folio)
		.select(folio.name)
		.where((folio.shareholder == holder.name) & folio.company.notin(get_allowed_companies(user) or [""]))
	)
	return f"not exists ({query.get_sql()})"
