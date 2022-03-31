# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("payroll", "doctype", "gratuity_rule")
	frappe.reload_doc("payroll", "doctype", "gratuity_rule_slab")
	frappe.reload_doc("payroll", "doctype", "gratuity_applicable_component")
	if frappe.db.exists("Company", {"country": "India"}):
		from erpnext.regional.india.setup import create_gratuity_rule

		create_gratuity_rule()
	if frappe.db.exists("Company", {"country": "United Arab Emirates"}):
		from erpnext.regional.united_arab_emirates.setup import create_gratuity_rule

		create_gratuity_rule()
