# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import frappe


def execute():
	doctypes = frappe.get_all("DocType", {"module": "education", "custom": 0}, pluck="name")
	items = frappe.get_all(
		"Portal Menu Item", filters={"reference_doctype": ("in", doctypes)}, pluck="name"
	)
	for item in items:
		frappe.delete_doc("Portal Menu Item", item, ignore_missing=True, force=True)
