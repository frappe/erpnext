# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

DOCTYPE = "Material Request"


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.doc = get_permitted_doc(frappe.form_dict.name)
	if hasattr(context.doc, "set_indicator"):
		context.doc.set_indicator()

	context.parents = frappe.form_dict.parents
	context.title = frappe.form_dict.name

	default_print_format = frappe.db.get_value(
		"Property Setter",
		dict(property="default_print_format", doc_type=DOCTYPE),
		"value",
	)
	if default_print_format:
		context.print_format = default_print_format
	else:
		context.print_format = "Standard"
	context.doc.items = get_more_items_info(context.doc.items, context.doc.name)


def get_permitted_doc(name):
	# same refusal for a missing and an unreadable record, so the page does not reveal which names exist
	# a JSON body can send a dict, which db.exists and get_doc would read as filters
	if not (name and isinstance(name, str) and frappe.db.exists(DOCTYPE, name)):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	doc = frappe.get_doc(DOCTYPE, name)
	if not (doc.has_permission("read") or frappe.has_website_permission(doc)):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	return doc


def get_more_items_info(items, material_request):
	for item in items:
		item.customer_provided = frappe.get_value("Item", item.item_code, "is_customer_provided_item")
		item.work_orders = frappe.db.sql(
			"""
			select
				wo.name, wo.status, wo_item.consumed_qty
			from
				`tabWork Order Item` wo_item, `tabWork Order` wo
			where
				wo_item.item_code=%s
				and wo_item.consumed_qty=0
				and wo_item.parent=wo.name
				and wo.status not in ('Completed', 'Cancelled', 'Stopped')
			order by
				wo.name asc""",
			item.item_code,
			as_dict=1,
		)
		item.delivered_qty = flt(
			frappe.db.sql(
				"""select sum(transfer_qty)
						from `tabStock Entry Detail` where material_request = %s
						and item_code = %s and docstatus = 1""",
				(material_request, item.item_code),
			)[0][0]
		)
	return items
