# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "stock_settings")

	ss = frappe.get_doc("Stock Settings")
	ss.set_qty_in_transactions_based_on_serial_no_input = 1
	ss.save()