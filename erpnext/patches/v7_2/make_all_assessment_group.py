# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if not frappe.db.exists({"doctype": "Assessment Group","assessment_group_name": "All Assessment Groups"}):
		frappe.reload_doc("education", "doctype", "assessment_group")
		doc = frappe.new_doc("Assessment Group")
		doc.assessment_group_name = "All Assessment Groups"
		doc.is_group = 1
		doc.flags.ignore_mandatory = True
		doc.save()