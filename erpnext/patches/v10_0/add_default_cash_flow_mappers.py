# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe

from erpnext.setup.install import create_default_cash_flow_mapper_templates


def execute():
	frappe.reload_doc("accounts", "doctype", frappe.scrub("Cash Flow Mapping"))
	frappe.reload_doc("accounts", "doctype", frappe.scrub("Cash Flow Mapper"))
	frappe.reload_doc("accounts", "doctype", frappe.scrub("Cash Flow Mapping Template Details"))

	create_default_cash_flow_mapper_templates()
