# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	for doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
		tab = frappe.qb.DocType(doctype).as_("tab")
		frappe.qb.update(tab).set(tab.is_old_subcontracting_flow, 1).where(
			tab.is_subcontracted == 1
		).run()
