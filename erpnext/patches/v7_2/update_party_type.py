# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Account")
	make_party_type()

def make_party_type():
	for party_type in ["Customer", "Supplier", "Employee"]:
		doc = frappe.new_doc("Party Type")
		doc.party_type = party_type
		doc.save(ignore_permissions=True)