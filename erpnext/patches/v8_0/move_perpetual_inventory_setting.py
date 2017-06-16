# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('Company')
	enabled = frappe.db.get_single_value("Accounts Settings", "auto_accounting_for_stock") or 0
	frappe.db.sql("""update tabCompany set enable_perpetual_inventory = {0}""".format(enabled))