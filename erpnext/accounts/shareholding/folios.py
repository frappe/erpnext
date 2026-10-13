# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.accounts.shareholding.locking import lock_company


def get_or_create_folio(company, shareholder=None, posting_date=None, is_treasury=False):
	lock_company(company)
	filters = {"company": company, "is_treasury": 1 if is_treasury else 0}
	if not is_treasury:
		if not shareholder:
			frappe.throw(_("Shareholder is required to resolve a non-treasury folio."))
		filters["shareholder"] = shareholder

	if folio := frappe.db.get_value("Share Folio", filters, "name"):
		return folio

	folio = frappe.get_doc(
		{
			"doctype": "Share Folio",
			"company": company,
			"is_treasury": 1 if is_treasury else 0,
			"shareholder": None if is_treasury else shareholder,
			"date_of_becoming_member": None if is_treasury else posting_date,
		}
	)
	previous_creation_flag = frappe.flags.get("creating_share_folio")
	frappe.flags.creating_share_folio = True
	try:
		folio.insert(ignore_permissions=True)
	finally:
		frappe.flags.creating_share_folio = previous_creation_flag
	return folio.name
