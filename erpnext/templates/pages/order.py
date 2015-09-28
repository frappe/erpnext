# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _

def get_context(context):
	context.no_cache = 1
	context.doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)
	if hasattr(context.doc, "set_indicator"):
		context.doc.set_indicator()

	context.parents = frappe.form_dict.parents

	if not context.doc.has_website_permission("read"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)
