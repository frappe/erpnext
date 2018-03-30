# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.exists("DocType", "Examination"):
		frappe.rename_doc("DocType", "Examination", "Assessment")
		frappe.rename_doc("DocType", "Examination Result", "Assessment Result")

		# 'Schools' module changed to the 'Education'
		# frappe.reload_doc("schools", "doctype", "assessment")
		# frappe.reload_doc("schools", "doctype", "assessment_result")

		frappe.reload_doc("education", "doctype", "assessment")
		frappe.reload_doc("education", "doctype", "assessment_result")

		rename_field("Assessment", "exam_name", "assessment_name")
		rename_field("Assessment", "exam_code", "assessment_code")
	
		frappe.db.sql("delete from `tabPortal Menu Item` where route = '/examination'")