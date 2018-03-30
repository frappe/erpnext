# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Opportunity")
	frappe.db.sql("update tabDocPerm set submit=0, cancel=0, amend=0 where parent='Opportunity'")
	frappe.db.sql("update tabOpportunity set docstatus=0 where docstatus=1")
