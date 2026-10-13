# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def lock_company(company: str) -> None:
	"""Serialize shareholding changes within the current database transaction."""
	if not frappe.db.get_value("Company", company, "name", for_update=True):
		frappe.throw(_("Company does not exist."))
