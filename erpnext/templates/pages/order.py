# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings import get_shopping_cart_settings, show_attachments
from frappe import _


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True

	# setup cart context
	shopping_cart_settings = get_shopping_cart_settings()
	context.payment_gateway_list = shopping_cart_settings.gateways
	context.enabled_checkout = shopping_cart_settings.enable_checkout

	# setup document context
	context.doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)

	if not frappe.has_website_permission(context.doc):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	context.parents = frappe.form_dict.parents
	context.title = frappe.form_dict.name
	context.payment_ref = frappe.db.get_value("Payment Request", {"reference_name": frappe.form_dict.name}, "name")

	default_print_format = frappe.db.get_value('Property Setter',
		dict(property='default_print_format', doc_type=frappe.form_dict.doctype), "value")

	context.print_format = default_print_format or "Standard"

	if hasattr(context.doc, "set_indicator"):
		context.doc.set_indicator()

	if show_attachments():
		context.attachments = get_attachments(frappe.form_dict.doctype, frappe.form_dict.name)

	# setup loyalty program for the customer, if available
	customer_loyalty_program = frappe.db.get_value("Customer", context.doc.customer, "loyalty_program")
	if customer_loyalty_program:
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_program_details_with_points

		loyalty_program_details = get_loyalty_program_details_with_points(context.doc.customer, customer_loyalty_program)
		context.available_loyalty_points = int(loyalty_program_details.get("loyalty_points"))


def get_attachments(dt, dn):
	return frappe.get_all("File",
		filters={"attached_to_name": dn, "attached_to_doctype": dt, "is_private": 0},
		fields=["name", "file_name", "file_url", "is_private"])
