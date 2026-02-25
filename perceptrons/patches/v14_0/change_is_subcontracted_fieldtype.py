# Copyright (c) 2022, Hash Include Solutions FZC and contributors
# For license information, please see license.txt

import frappe


def execute():
	for doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice", "Supplier Quotation"]:
		frappe.db.sql(
			f"""
				UPDATE `tab{doctype}`
				SET is_subcontracted = 0
				where is_subcontracted in ('', 'No') or is_subcontracted is null"""
		)
		frappe.db.sql(
			f"""
				UPDATE `tab{doctype}`
				SET is_subcontracted = 1
				where is_subcontracted = 'Yes'"""
		)

		frappe.reload_doc(frappe.get_meta(doctype).module, "doctype", frappe.scrub(doctype))
