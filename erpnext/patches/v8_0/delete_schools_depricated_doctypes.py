# Copyright (c) 2017, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	""" delete doctypes """

	if frappe.db.exists("DocType", "Grading Structure"):
		frappe.delete_doc("DocType", "Grading Structure", force=1)

	if frappe.db.exists("DocType", "Grade Interval"):
		frappe.delete_doc("DocType", "Grade Interval", force=1)