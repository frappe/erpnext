# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doctype("Appraisal")
	frappe.db.sql("update `tabAppraisal` set remarks = comments")