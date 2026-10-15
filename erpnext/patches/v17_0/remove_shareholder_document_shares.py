# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Remove document shares that can bypass a global Shareholder's company restrictions."""
	frappe.db.delete("DocShare", {"share_doctype": "Shareholder"})
