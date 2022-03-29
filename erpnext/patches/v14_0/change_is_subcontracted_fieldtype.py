# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
    doctypes = ["Purchase Order", "Purchase Receipt", "Purchase Invoice", "Supplier Quotation"]

    for doctype in doctypes:
        docs = frappe.get_all(doctype, fields=["name", "is_subcontracted"])
        for doc in docs:
            value = "1" if doc.is_subcontracted == "Yes" else "0"
            frappe.db.set_value(doctype, doc.name, "is_subcontracted", value, update_modified=False)