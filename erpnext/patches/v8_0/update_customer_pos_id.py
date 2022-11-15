# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doctype("Customer")
	frappe.db.sql(""" update `tabCustomer` set customer_pos_id = name """)