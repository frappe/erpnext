# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _

def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)
	if hasattr(context.doc, "set_indicator"):
		context.doc.set_indicator()

	for portal_menu_item in frappe.get_all("Portal Menu Item", filters={'reference_doctype': frappe.form_dict.doctype}, fields=['view_attachments\
']):
                if portal_menu_item.view_attachments == 1:
                        context.attachments = get_attachments(frappe.form_dict.doctype, frappe.form_dict.name)

	context.parents = frappe.form_dict.parents
	context.payment_ref = frappe.db.get_value("Payment Request",
		{"reference_name": frappe.form_dict.name}, "name")

	context.enabled_checkout = frappe.get_doc("Shopping Cart Settings").enable_checkout

	if not frappe.has_website_permission(context.doc):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

def get_attachments(dt, dn):
        return frappe.get_all("File", fields=["name", "file_name", "file_url", "is_private"],
                              filters = {"attached_to_name": dn, "attached_to_doctype": dt, "is_private":0})
