# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime


def lock_company(company: str) -> None:
	"""Serialize shareholding changes within the current database transaction."""
	if not frappe.db.get_value("Company", company, "name", for_update=True):
		frappe.throw(_("Company does not exist."))
	# A row write also rejects stale PostgreSQL snapshots after a competing post.
	frappe.db.set_value("Company", company, "modified", now_datetime(), update_modified=False)
