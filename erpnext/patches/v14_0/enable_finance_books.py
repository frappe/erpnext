# Copyright (c) 2021, Frappe and Contributors


import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "accounts_settings")
	frappe.db.set_value("Accounts Settings", None, "enable_finance_books", 1)
