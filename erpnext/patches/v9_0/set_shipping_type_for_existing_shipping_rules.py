# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Shipping Rule")
	for record in frappe.get_all("Shipping Rule"):
		doc = frappe.get_doc("Shipping Rule", record)
		if not doc.shipping_rule_type:
			frappe.db.set_value("Shipping Rule", record, "shipping_rule_type", "Selling")