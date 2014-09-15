# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("manufacturing", "doctype", "bom")
	frappe.db.sql("""update tabBOM set total_variable_cost = total_cost""")